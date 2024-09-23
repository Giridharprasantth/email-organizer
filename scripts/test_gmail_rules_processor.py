import pytest
from datetime import datetime, timedelta, timezone
import json
from gmail_rules_processor import (
    FieldName,
    StringPredicate,
    DatePredicate,
    RulePredicate,
    ActionType,
    Rule,
    Action,
    RuleSet,
    Email,
    load_rules,
    evaluate_rule,
    evaluate_string_rule,
    evaluate_date_rule,
    apply_rules,
    get_emails_from_db,
)


@pytest.fixture
def sample_ruleset():
    return RuleSet(
        rules=[
            Rule(
                field_name=FieldName.SENDER,
                predicate=StringPredicate.CONTAINS,
                value="example.com",
            ),
            Rule(
                field_name=FieldName.SUBJECT,
                predicate=StringPredicate.CONTAINS,
                value="important",
            ),
        ],
        rule_predicate=RulePredicate.ALL,
        actions=[
            Action(action_type=ActionType.MARK_AS_READ),
            Action(action_type=ActionType.MOVE_TO_MAILBOX, folder_name="Important"),
        ],
    )


@pytest.fixture
def sample_email():
    return Email(
        message_id="123",
        sender="sender@example.com",
        recipient="recipient@test.com",
        subject="This is an important email",
        message="Hello, this is the message body.",
        received_time=datetime.now(timezone.utc).isoformat(),
    )


def test_load_rules(tmp_path):
    rules_file = tmp_path / "test_rules.json"
    rules_data = {
        "rules": [
            {"field_name": "sender", "predicate": "contains", "value": "example.com"}
        ],
        "rule_predicate": "all",
        "actions": [{"action_type": "mark_as_read"}],
    }
    rules_file.write_text(json.dumps(rules_data))

    ruleset = load_rules(str(rules_file))
    assert isinstance(ruleset, RuleSet)
    assert len(ruleset.rules) == 1
    assert ruleset.rule_predicate == RulePredicate.ALL
    assert len(ruleset.actions) == 1


def test_evaluate_rule(sample_email):
    rule1 = Rule(
        field_name=FieldName.SENDER,
        predicate=StringPredicate.CONTAINS,
        value="example.com",
    )
    rule2 = Rule(
        field_name=FieldName.SUBJECT,
        predicate=StringPredicate.CONTAINS,
        value="unimportant",
    )

    assert evaluate_rule(rule1, sample_email) == True
    assert evaluate_rule(rule2, sample_email) == False


def test_evaluate_string_rule():
    rule = Rule(
        field_name=FieldName.SENDER, predicate=StringPredicate.CONTAINS, value="example"
    )
    assert evaluate_string_rule(rule, "user@example.com") == True
    assert evaluate_string_rule(rule, "user@test.com") == False

    rule = Rule(
        field_name=FieldName.SENDER,
        predicate=StringPredicate.DOES_NOT_CONTAIN,
        value="example",
    )
    assert evaluate_string_rule(rule, "user@example.com") == False
    assert evaluate_string_rule(rule, "user@test.com") == True

    rule = Rule(
        field_name=FieldName.SENDER,
        predicate=StringPredicate.EQUALS,
        value="user@example.com",
    )
    assert evaluate_string_rule(rule, "user@example.com") == True
    assert evaluate_string_rule(rule, "other@example.com") == False

    rule = Rule(
        field_name=FieldName.SENDER,
        predicate=StringPredicate.DOES_NOT_EQUAL,
        value="user@example.com",
    )
    assert evaluate_string_rule(rule, "user@example.com") == False
    assert evaluate_string_rule(rule, "other@example.com") == True


def test_evaluate_date_rule():
    now = datetime.now(timezone.utc)
    five_days_ago = (now - timedelta(days=5)).isoformat()
    ten_days_ago = (now - timedelta(days=10)).isoformat()

    rule = Rule(
        field_name=FieldName.RECEIVED_TIME,
        predicate=DatePredicate.IS_LESS_THAN,
        value="7 days",
    )
    assert evaluate_date_rule(rule, five_days_ago) == True
    assert evaluate_date_rule(rule, ten_days_ago) == False

    rule = Rule(
        field_name=FieldName.RECEIVED_TIME,
        predicate=DatePredicate.IS_GREATER_THAN,
        value="7 days",
    )
    assert evaluate_date_rule(rule, five_days_ago) == False
    assert evaluate_date_rule(rule, ten_days_ago) == True


def test_apply_rules(sample_ruleset, sample_email):
    actions = apply_rules(sample_ruleset, sample_email)
    assert len(actions) == 2
    assert actions[0].action_type == ActionType.MARK_AS_READ
    assert actions[1].action_type == ActionType.MOVE_TO_MAILBOX


def test_apply_rules_no_match(sample_ruleset):
    non_matching_email = Email(
        message_id="456",
        sender="sender@other.com",
        recipient="recipient@test.com",
        subject="This is an unimportant email",
        message="Hello, this is the message body.",
        received_time=datetime.now(timezone.utc).isoformat(),
    )
    actions = apply_rules(sample_ruleset, non_matching_email)
    assert len(actions) == 0


@pytest.fixture
def mock_db(tmp_path):
    import sqlite3

    db_path = tmp_path / "test_emails.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE emails (
        message_id TEXT PRIMARY KEY,
        sender TEXT,
        recipient TEXT,
        message TEXT,
        received_time TIMESTAMP,
        subject TEXT
    )
    """)
    conn.commit()
    conn.close()
    return str(db_path)


def test_get_emails_from_db(mock_db):
    import sqlite3

    conn = sqlite3.connect(mock_db)
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO emails (message_id, sender, recipient, message, received_time, subject)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "123",
            "sender@example.com",
            "recipient@test.com",
            "Test message",
            "2023-01-01T12:00:00+00:00",
            "Test subject",
        ),
    )
    conn.commit()
    conn.close()

    emails = get_emails_from_db(mock_db)
    assert len(emails) == 1
    assert emails[0].message_id == "123"
    assert emails[0].sender == "sender@example.com"


if __name__ == "__main__":
    pytest.main()
