import json
from typing import List, Union
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field, validate_call
from enum import Enum
import sqlite3
from gmail_service import get_gmail_service
import logging

logging.basicConfig(format="%(levelname)s %(asctime)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


class FieldName(str, Enum):
    SENDER = "sender"
    RECIPIENT = "recipient"
    SUBJECT = "subject"
    MESSAGE = "message"
    RECEIVED_TIME = "received_time"


class StringPredicate(str, Enum):
    CONTAINS = "contains"
    DOES_NOT_CONTAIN = "does not contain"
    EQUALS = "equals"
    DOES_NOT_EQUAL = "does not equal"


class DatePredicate(str, Enum):
    IS_LESS_THAN = "is less than"
    IS_GREATER_THAN = "is greater than"


class RulePredicate(str, Enum):
    ALL = "all"
    ANY = "any"


class ActionType(str, Enum):
    MARK_AS_READ = "mark_as_read"
    MARK_AS_UNREAD = "mark_as_unread"
    MOVE_TO_MAILBOX = "move_to_mailbox"


class Rule(BaseModel):
    field_name: FieldName
    predicate: Union[StringPredicate, DatePredicate]
    value: str


class Action(BaseModel):
    action_type: ActionType
    folder_name: str = Field(None, alias="folder_name")


class RuleSet(BaseModel):
    rules: List[Rule]
    rule_predicate: RulePredicate
    actions: List[Action]


class Email(BaseModel):
    message_id: str
    sender: str
    recipient: str
    message: str
    received_time: str
    subject: str


@validate_call(validate_return=True)
def load_rules(file_path: str) -> RuleSet:
    with open(file_path, "r") as f:
        data = json.load(f)
    return RuleSet(**data)


@validate_call(validate_return=True)
def evaluate_rule(rule: Rule, email: Email) -> bool:
    field_value = getattr(email, rule.field_name)

    if rule.field_name == FieldName.RECEIVED_TIME:
        return evaluate_date_rule(rule, field_value)
    else:
        return evaluate_string_rule(rule, field_value)


@validate_call(validate_return=True)
def evaluate_string_rule(rule: Rule, field_value: str) -> bool:
    if rule.predicate == StringPredicate.CONTAINS:
        return rule.value.lower() in field_value.lower()
    elif rule.predicate == StringPredicate.DOES_NOT_CONTAIN:
        return rule.value.lower() not in field_value.lower()
    elif rule.predicate == StringPredicate.EQUALS:
        return rule.value.lower() == field_value.lower()
    elif rule.predicate == StringPredicate.DOES_NOT_EQUAL:
        return rule.value.lower() != field_value.lower()
    else:
        raise ValueError(f"Invalid string predicate: {rule.predicate}")


@validate_call(validate_return=True)
def evaluate_date_rule(rule: Rule, field_value: str) -> bool:
    email_date = datetime.fromisoformat(field_value)
    current_date = datetime.now(timezone.utc)

    value_parts = rule.value.split()
    amount = int(value_parts[0])
    unit = value_parts[1]

    if unit.startswith("day"):
        delta = timedelta(days=amount)
    elif unit.startswith("month"):
        delta = timedelta(days=amount * 30)
    else:
        raise ValueError(f"Invalid time unit: {unit}")

    if rule.predicate == DatePredicate.IS_LESS_THAN:
        return current_date - email_date < delta
    elif rule.predicate == DatePredicate.IS_GREATER_THAN:
        return current_date - email_date > delta
    else:
        raise ValueError(f"Invalid date predicate: {rule.predicate}")


@validate_call(validate_return=True)
def apply_rules(ruleset: RuleSet, email: Email) -> List[Action]:
    results = [evaluate_rule(rule, email) for rule in ruleset.rules]

    if ruleset.rule_predicate == RulePredicate.ALL:
        if all(results):
            return ruleset.actions
    elif ruleset.rule_predicate == RulePredicate.ANY:
        if any(results):
            return ruleset.actions

    return []


@validate_call(validate_return=True)
def get_emails_from_db(db_path: str) -> List[Email]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM emails")
    rows = cursor.fetchall()

    emails = []
    for row in rows:
        email = Email(
            message_id=row[0],
            sender=row[1],
            recipient=row[2],
            message=row[3],
            received_time=row[4],
            subject=row[5],
        )
        emails.append(email)

    conn.close()
    return emails


@validate_call(validate_return=True)
def execute_actions(service, email: Email, actions: List[Action]):
    log.info("Executing actions")
    for action in actions:
        if action.action_type == ActionType.MARK_AS_READ:
            service.users().messages().modify(
                userId="me", id=email.message_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
        elif action.action_type == ActionType.MARK_AS_UNREAD:
            service.users().messages().modify(
                userId="me", id=email.message_id, body={"addLabelIds": ["UNREAD"]}
            ).execute()
        elif action.action_type == ActionType.MOVE_TO_MAILBOX:
            label_id = get_or_create_label(service, action.folder_name)
            service.users().messages().modify(
                userId="me", id=email.message_id, body={"addLabelIds": [label_id]}
            ).execute()


@validate_call(validate_return=True)
def get_or_create_label(service, label_name: str) -> str:
    try:
        labels = service.users().labels().list(userId="me").execute()
        for label in labels["labels"]:
            if label["name"] == label_name:
                return label["id"]

        label = (
            service.users()
            .labels()
            .create(userId="me", body={"name": label_name})
            .execute()
        )
        return label["id"]
    except Exception as e:
        log.error(f"Error getting or creating label: {e}")
        return None


@validate_call(validate_return=True)
def main(rules_file: str, db_path: str):
    ruleset = load_rules(rules_file)
    emails = get_emails_from_db(db_path)

    service = get_gmail_service()

    for email in emails:
        actions_to_execute = apply_rules(ruleset, email)
        if actions_to_execute:
            execute_actions(service, email, actions_to_execute)


if __name__ == "__main__":
    main("rules.json", "emails.db")
