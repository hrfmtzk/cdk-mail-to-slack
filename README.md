# CDK Mail to Slack

A system that saves emails received via Amazon SES to Amazon S3 and automatically notifies Slack channels via AWS Lambda, built with AWS CDK (Python).

For detailed design documentation, see [docs/README.md](docs/README.md).

**Japanese Version:** [README_ja.md](README_ja.md)

## Project Structure

```
cdk-mail-to-slack/
├── app.py                      # CDK App entry point
├── config.py                   # Environment configuration (gitignored)
├── config.py.example           # Configuration template
├── cdk.context.json            # CDK context cache (gitignored)
├── cdk_mail_to_slack/          # CDK stack definition
│   └── cdk_mail_to_slack_stack.py
├── source/
│   └── email_handler/          # Lambda function
│       ├── main.py
│       └── requirements.txt
├── tests/                      # Test code
│   ├── unit/
│   └── snapshot/
└── .vscode/                    # VSCode settings (project-wide)
    └── settings.json           # CDK type check suppressions
```

## Setup

### 1. Create Virtual Environment and Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Create Configuration File

```bash
cp config.py.example config.py
```

Edit `config.py` and configure the following values:

**Required Settings:**
- `DOMAIN_NAME`: Domain name for receiving emails
- `HOSTED_ZONE_NAME`: Route 53 hosted zone name
- `SLACK_ERROR_CHANNEL`: Slack channel name for error notifications
- `CREATE_MX_RECORD`: Automatically create MX record (True/False)
  - `True`: CDK automatically creates MX record in Route 53
  - `False`: MX record already exists or managed externally
- `USE_EXISTING_RULE_SET`: Use existing SES rule set (True/False)
  - `True`: Add rule to existing rule set
  - `False`: Create new rule set

**Optional Settings:**
- `EXISTING_RULE_SET_NAME`: Existing rule set name (required if `USE_EXISTING_RULE_SET=True`)
- `INSERT_AFTER_RULE`: Position to insert rule (specify existing rule name, defaults to beginning if not specified)
- `ENABLE_XRAY_TRACING`: Enable AWS X-Ray tracing (default: True)
- `SENTRY_DSN`: Sentry DSN for error tracking (Sentry disabled if not specified)

### 3. Create Slack Bot and Prepare Token

#### 3.1. Create Slack App

1. Access [Slack API](https://api.slack.com/apps)
2. Click "Create New App"
3. Select "From scratch"
4. Enter App Name (e.g., `Mail Notifier`) and select workspace

#### 3.2. Configure Bot Token Scopes

1. Select "OAuth & Permissions" from left menu
2. Add the following to "Bot Token Scopes" in "Scopes" section:
   - `chat:write` - Permission to post messages

#### 3.3. Install App

1. Click "Install to Workspace" at top of "OAuth & Permissions" page
2. Review permissions and click "Allow"
3. Copy "Bot User OAuth Token" (string starting with `xoxb-`)

### 4. Configure Sentry (Optional)

To use Sentry for error tracking:

1. Create account at [Sentry](https://sentry.io/) (free plan available)
2. Create new project (Platform: Python)
3. Copy DSN (Data Source Name)
4. Set `SENTRY_DSN` in `config.py`:
   ```python
   SENTRY_DSN = "https://your-key@sentry.io/your-project-id"
   ```

If not using Sentry, leave `SENTRY_DSN` undefined in `config.py`.

### 5. Run Tests

```bash
pytest
```

### 6. Deploy

#### 6.1. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap
```

#### 6.2. Deploy Stack

```bash
cdk deploy
```

## Post-Deployment Manual Setup

CDK does not manage certain resources that require manual creation and configuration.

### 1. Slack Bot Token in Secrets Manager

**Why Required:** Lambda function retrieves Slack Bot Token from Secrets Manager

**Creation Method:**

Via AWS Console:
1. Open Secrets Manager in AWS Management Console
2. Create new secret
3. Select "Other type of secret"
4. Enter key/value:
   - Key: `SLACK_BOT_TOKEN`
   - Value: Token obtained in Setup Step 3 (`xoxb-...`)
5. Set secret name: `MailSlack/SlackBotToken`
6. Complete creation

Via AWS CLI:
```bash
aws secretsmanager create-secret \
  --name MailSlack/SlackBotToken \
  --secret-string '{"SLACK_BOT_TOKEN":"xoxb-your-token-here"}'
```

### 2. Route 53 Hosted Zone

**Why Required:** Manage domain DNS records

**Creation Method:**
```bash
# Create via AWS CLI
aws route53 create-hosted-zone \
  --name example.com \
  --caller-reference $(date +%s)
```

Or via AWS Console:
1. Route 53 > Hosted zones > Create hosted zone
2. Enter domain name (e.g., `example.com`)
3. Type: Public hosted zone

**Note:** Update nameservers at domain registrar to Route 53 NS records

### 3. SES Email Identity (Domain Verification)

**Why Required:** Prove domain ownership to receive emails via SES

**Creation Method:**

Via AWS Console:
1. Amazon SES > Identities > Create identity
2. Identity type: Domain
3. Domain: `example.com` (same as `DOMAIN_NAME` in `config.py`)
4. DKIM signatures: Enabled (default)
5. Add displayed DKIM CNAME records (3 records) to Route 53

**Required DNS Records:**
- DKIM records: 3 CNAME records (used for domain verification and email authentication)
- MX record: `10 inbound-smtp.{region}.amazonaws.com` (automatically created if `CREATE_MX_RECORD=True`)

**Note:** Verification may take up to 72 hours after adding DKIM records

### 4. Activate SES Receipt Rule Set

**Why Required:** Rule set created by CDK is inactive by default

**Configuration Method:**
```bash
# Activate via AWS CLI
aws ses set-active-receipt-rule-set \
  --rule-set-name MailSlackRuleSet
```

Or via AWS Console:
1. Amazon SES > Email receiving > Rule sets
2. Select `MailSlackRuleSet`
3. Click "Set as active"

### 5. Remove SES Sandbox (Production Environment)

**Why Required:** Sandbox environment only receives from verified email addresses

**Application Method:**
1. Amazon SES > Account dashboard
2. Click "Request production access"
3. Fill in use case details and submit

**Note:** Approval typically takes about 1 business day

### 6. Invite Slack Bot to Channels

**Why Required:** Bot must be channel member to post messages

**Configuration Method:**
1. Open target Slack channel for notifications
2. Execute `/invite @your-bot-name`
3. Similarly invite to error notification channel (`SLACK_ERROR_CHANNEL` in `config.py`)

## Usage

### Slack Notification via Email

This system interprets the **local part** (before @) of the email address as the Slack channel name.

#### Basic Usage

**Email Address Format:**
```
<channel-name>@<DOMAIN_NAME>
```

**Example:**
- If `DOMAIN_NAME = "mail.example.com"` in `config.py`
- Email to `general@mail.example.com` → Notification to `#general` channel
- Email to `dev-team@mail.example.com` → Notification to `#dev-team` channel
- Email to `random@mail.example.com` → Notification to `#random` channel

#### Notification Content

Messages posted to Slack include the following information:
- Sender (From)
- Subject
- Email body

#### Error Handling

In the following cases, an error notification is sent to `SLACK_ERROR_CHANNEL` configured in `config.py`:
- Specified channel does not exist
- Bot is not invited to the channel
- Slack API error occurs

#### Notes

- Channel name must not include `#` (automatically added)
- Bot must be invited to the channel in advance
- For private channels, Bot invitation is also required

## Development

### VSCode Settings

`.vscode/settings.json` contains project-wide settings:
- Suppresses Pylance warnings for AWS CDK JSII-generated type definitions
- These warnings do not affect runtime and are a known CDK issue

### Code Formatting

```bash
black .
isort .
```

### Linters

```bash
flake8
mypy .
```

### Test Coverage

```bash
pytest --cov
```

## Architecture

For detailed system design, see [docs/design.md](docs/design.md).

**Key Components:**
- Amazon SES: Email reception
- Amazon S3: Email storage
- AWS Lambda: Email processing and Slack notification
- AWS Secrets Manager: Slack Bot Token storage
- Amazon Route 53: DNS management

## Security

- **TLS Enforcement**: SES rejects unencrypted connections
- **Spam/Virus Scanning**: Automatic malicious email blocking
- **Minimum Permissions**: Lambda execution role has minimal required permissions
- **Secret Management**: Slack token stored in Secrets Manager
- **Data Retention**: Emails auto-deleted after 30 days

## Monitoring

- **CloudWatch Logs**: Lambda execution logs (1 week retention)
- **X-Ray Tracing**: Execution flow visualization (optional)
- **Sentry**: Error tracking and alerting (optional)

## Cost

Estimated monthly cost for 1,000 emails:
- SES: $0.10
- S3: $0.03
- Lambda: $0.20
- Secrets Manager: $0.40
- Route 53: $0.50

**Total: Approximately $1.23/month**

*Actual costs vary based on usage

## License

This project is licensed under the MIT License.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
