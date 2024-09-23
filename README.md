# Gmail Scripts

This repository contains Python scripts for fetching, storing and processing Gmail messages.

## Contents

- `scripts/gmail_fetch.py`: Script for fetching emails from Gmail and storing in local sqlite db.
- `scripts/gmail_rules_processor.py`: Script for processing Gmail messages based on defined rules.

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Steps

1. Clone the repository:

   ```
   git clone https://github.com/Giridharprasantth/email-organizer.git
   cd scripts
   ```

2. Set up a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:

   For production use:

   ```
   pip install -r requirements.txt
   ```

   For development:

   ```
   pip install -r requirements-dev.txt
   ```

## Usage

Before running the scripts, you need to set up authentication with Gmail API. Follow these steps:

1. Set up a Google Cloud Project and enable the Gmail API.
2. Create credentials (OAuth 2.0 Client ID) for a desktop application.
3. Download the credentials file and rename it to `credentials.json`.
4. Place `credentials.json` in the root directory of the project.
5. For gmail rules processor create your rules in `rules.json` file then execute the script.

To run the scripts:

```
python scripts/gmail_fetch.py --max_emails 100
```

```
python scripts/gmail_rules_processor.py
```

## Running Tests

To run the tests, make sure you have installed the development requirements, then execute:

```
pytest scripts/
```

## Getting Tokens

The first time you run either script, it will prompt you to authorize the application:

1. The script will open a new window in your default web browser.
2. Log in to your Google account and grant the requested permissions.
3. After authorization, the script will save the token for future use.

The token will be stored in a file named `token.json` in the project directory. This file allows the scripts to access your Gmail account without requiring re-authorization each time.

# Email Rules System: Value Table

This table provides a quick reference for all possible values for `rules.json`.

| Enumeration     | Value            | Description                                    |
| --------------- | ---------------- | ---------------------------------------------- |
| FieldName       | sender           | The email sender                               |
|                 | recipient        | The email recipient                            |
|                 | subject          | The email subject                              |
|                 | message          | The email body                                 |
|                 | received_time    | The time the email was received                |
| StringPredicate | contains         | Check if a string contains a substring         |
|                 | does not contain | Check if a string does not contain a substring |
|                 | equals           | Check if two strings are exactly equal         |
|                 | does not equal   | Check if two strings are not equal             |
| DatePredicate   | is less than     | Check if a date is earlier than a given date   |
|                 | is greater than  | Check if a date is later than a given date     |
| RulePredicate   | all              | All rules must be true                         |
|                 | any              | At least one rule must be true                 |
| ActionType      | mark_as_read     | Mark the email as read                         |
|                 | mark_as_unread   | Mark the email as unread                       |
|                 | move_to_mailbox  | Move the email to a specified mailbox          |

## Example JSON

```json
{
  "rules": [
    {
      "field_name": "subject",
      "predicate": "contains",
      "value": "Important"
    },
    {
      "field_name": "received_time",
      "predicate": "is less than",
      "value": "2 days"
    }
  ],
  "rule_predicate": "all",
  "actions": [
    {
      "action_type": "move_to_mailbox",
      "folder_name": "Priority"
    },
    {
      "action_type": "mark_as_read"
    }
  ]
}
```
