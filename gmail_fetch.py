from typing import List
from datetime import datetime
from pydantic import BaseModel, validate_call
from gmail_service import get_gmail_service
import sqlite3
from dateutil import parser
import logging
import argparse

logging.basicConfig(format="%(levelname)s %(asctime)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


class Email(BaseModel):
    message_id: str
    sender: str
    recipient: str
    message: str
    received_time: datetime
    subject: str


@validate_call(validate_return=True)
def fetch_emails(service, max_emails: int = 100, user_id: str = "me") -> List[Email]:
    results = service.users().messages().list(userId=user_id).execute()
    messages = results.get("messages", [])

    while "nextPageToken" in results and len(messages) < max_emails:
        page_token = results["nextPageToken"]
        results = (
            service.users()
            .messages()
            .list(userId=user_id, pageToken=page_token)
            .execute()
        )
        messages.extend(results.get("messages", []))

    messages = messages[:max_emails]

    emails = []
    for message in messages:
        msg = service.users().messages().get(userId=user_id, id=message["id"]).execute()
        headers = msg["payload"]["headers"]
        sender, subject, recipient, date = (
            "Unknown sender",
            "Unknown subject",
            "Unknown recipient",
            "Sat, 1 Jan 2000 00:00:00 +0000",
        )

        for header in headers:
            header_name = header["name"].lower()
            header_value = header["value"]

            if header_name == "from":
                sender = header_value
            elif header_name == "subject":
                subject = header_value
            elif header_name == "date":
                date = header_value
            elif header_name == "to":
                recipient = header_value

        received_time = parser.parse(date)

        if "parts" in msg["payload"]:
            message_body = msg["payload"]["parts"][0]["body"]["data"]
        else:
            message_body = msg["payload"]["body"]["data"]

        email = Email(
            message_id=msg["id"],
            sender=sender,
            recipient=recipient,
            message=message_body,
            received_time=received_time,
            subject=subject,
        )
        emails.append(email)
        log.info(f"Email with id {msg['id']} added to DB")

    return emails


@validate_call(validate_return=True)
def save_to_sqlite(emails: List[Email], db_path: str = "emails.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        message_id TEXT PRIMARY KEY,
        sender TEXT,
        recipient TEXT,
        message TEXT,
        received_time TIMESTAMP,
        subject TEXT
    )
    """)

    for email in emails:
        cursor.execute(
            """
        INSERT OR REPLACE INTO emails (message_id, sender, recipient, message, received_time, subject)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                email.message_id,
                email.sender,
                email.recipient,
                email.message,
                email.received_time.isoformat(),
                email.subject,
            ),
        )

    conn.commit()
    conn.close()


@validate_call(validate_return=True)
def main(max_emails: int = 100):
    service = get_gmail_service()
    emails = fetch_emails(service, max_emails=max_emails)
    save_to_sqlite(emails)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser("Email fetcher")
    arg_parser.add_argument(
        "--max_emails",
        help="Number of latest emails to be stored in db",
        type=int,
        default=10,
        required=False,
    )
    args = arg_parser.parse_args()
    main(max_emails=args.max_emails)
