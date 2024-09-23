import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from gmail_fetch import Email, fetch_emails, save_to_sqlite
import sqlite3


@pytest.fixture
def mock_gmail_service():
    mock_service = MagicMock()
    mock_messages = [
        {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Mon, 1 Jan 2023 12:00:00 +0000"},
                ],
                "body": {"data": "Test message body"},
            },
        }
    ]
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg1"}]
    }
    mock_service.users().messages().get().execute.return_value = mock_messages[0]
    return mock_service


@pytest.fixture
def sample_emails():
    return [
        Email(
            message_id="msg1",
            sender="sender@example.com",
            recipient="recipient@example.com",
            message="Test message body",
            received_time=datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc),
            subject="Test Subject",
        )
    ]


def test_fetch_emails(mock_gmail_service):
    emails = fetch_emails(mock_gmail_service, max_emails=1)
    assert len(emails) == 1
    email = emails[0]
    assert isinstance(email, Email)
    assert email.message_id == "msg1"
    assert email.sender == "sender@example.com"
    assert email.recipient == "recipient@example.com"
    assert email.subject == "Test Subject"
    assert email.message == "Test message body"
    assert email.received_time == datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_fetch_emails_pagination(mock_gmail_service):
    mock_gmail_service.users().messages().list().execute.side_effect = [
        {"messages": [{"id": "msg1"}], "nextPageToken": "token1"},
        {"messages": [{"id": "msg2"}]},
    ]
    emails = fetch_emails(mock_gmail_service, max_emails=2)
    assert len(emails) == 2
    assert mock_gmail_service.users().messages().list().execute.call_count == 2


def test_save_to_sqlite(sample_emails, tmp_path):
    db_path = tmp_path / "test_emails.db"
    save_to_sqlite(sample_emails, str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM emails")
    rows = cursor.fetchall()

    assert len(rows) == 1
    row = rows[0]
    email = sample_emails[0]

    assert row[0] == email.message_id
    assert row[1] == email.sender
    assert row[2] == email.recipient
    assert row[3] == email.message
    assert row[4] == email.received_time.isoformat()
    assert row[5] == email.subject

    conn.close()


@pytest.mark.parametrize(
    "max_emails,expected",
    [
        (1, 1),
        (5, 5),
        (100, 100),
    ],
)
def test_fetch_emails_max_limit(mock_gmail_service, max_emails, expected):
    mock_gmail_service.users().messages().list().execute.return_value = {
        "messages": [{"id": f"msg{i}"} for i in range(150)]
    }
    emails = fetch_emails(mock_gmail_service, max_emails=max_emails)
    assert len(emails) == expected


if __name__ == "__main__":
    pytest.main()
