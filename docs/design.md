# System Design Document

## Overview

A system that automatically saves emails received via Amazon SES to Amazon S3 and notifies Slack channels via AWS Lambda.

## System Architecture

```
┌─────────────┐
│   Email     │
│  Sender     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Amazon SES                      │
│  - TLS Required (TlsPolicy: Require)   │
│  - Spam/Virus Scan Enabled             │
│  - ReceiptRule: Domain Email Reception │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Amazon S3                       │
│  - ses-emails/ prefix                  │
│  - Auto-delete after 30 days           │
│  - SSL Enforcement                     │
│  - Access Logs (90 days retention)    │
└──────┬──────────────────────────────────┘
       │ (S3 Event Notification)
       ▼
┌─────────────────────────────────────────┐
│         AWS Lambda                      │
│  - Python 3.14                         │
│  - Memory: 128MB                       │
│  - Timeout: 30s                        │
│  - Concurrency: 10                     │
│  - X-Ray Tracing (Optional)            │
│  - Sentry Error Tracking (Optional)    │
└──────┬──────────────────────────────────┘
       │
       ├─→ AWS Secrets Manager (Get Slack Token)
       │
       └─→ Slack API (chat.postMessage)
              │
              ▼
         ┌─────────────┐
         │   Slack     │
         │  Channel    │
         └─────────────┘
```

## Key Components

### 1. Amazon SES (Simple Email Service)

**Role:**
- Receive emails for specified domain
- Automatic save to S3

**Security Settings:**
- **TLS Required**: Reject unencrypted connections
- **Spam/Virus Scan**: Automatically block malicious emails

**Configuration:**
- ReceiptRuleSet: Create new or use existing
- Recipients: Domain specified in `config.DOMAIN_NAME`
- Actions: Save to S3 (`ses-emails/` prefix)

### 2. Amazon S3

**Bucket Configuration:**

1. **Email Storage Bucket**
   - Prefix: `ses-emails/`
   - Lifecycle: Auto-delete after 30 days
   - Encryption: S3-managed (SSE-S3)
   - SSL Enforcement: Implemented via bucket policy

2. **Access Log Bucket**
   - Lifecycle: Auto-delete after 90 days
   - Long-term retention for audit purposes

### 3. AWS Lambda

**Execution Environment:**
- Runtime: Python 3.14
- Memory: 128MB
- Timeout: 30 seconds
- Concurrency: 10 (Slack API rate limit mitigation)

**Environment Variables:**
- `DOMAIN_NAME`: Email receiving domain
- `SLACK_BOT_TOKEN_SECRET_NAME`: Secrets Manager secret name
- `SLACK_ERROR_CHANNEL`: Error notification channel
- `LOG_LEVEL`: Log level (INFO)
- `POWERTOOLS_SERVICE_NAME`: Service name
- `ENABLE_XRAY_TRACING`: Enable X-Ray tracing (Optional)
- `SENTRY_DSN`: Sentry DSN (Optional)

**Libraries:**
- `aws-lambda-powertools`: Logging, tracing
- `slack-sdk`: Slack API integration
- `sentry-sdk`: Error tracking (Optional)

### 4. AWS Secrets Manager

**Stored Content:**
- Slack Bot Token (`xoxb-...`)
- JSON format: `{"SLACK_BOT_TOKEN": "xoxb-..."}`

**Security:**
- Minimum permissions granted to Lambda execution role
- No automatic rotation support (manual management)

### 5. Amazon Route 53

**Managed Records:**
- MX Record: `10 inbound-smtp.{region}.amazonaws.com` (Optional)
- DKIM Records: For SES Identity verification (Manual setup)

## Processing Flow

### Normal Flow

1. **Email Reception**
   - Email sent to `channel-name@domain.com`
   - SES performs TLS/scan checks

2. **S3 Storage**
   - SES saves email to S3
   - Key: `ses-emails/{message-id}`

3. **Lambda Invocation**
   - Lambda triggered by S3 event notification
   - Retrieve email file from S3

4. **Email Parsing**
   - Extract channel name from To address
   - Parse MIME format email
   - Decode RFC 2047 encoded subject

5. **Slack Notification**
   - Get Bot Token from Secrets Manager
   - Post to specified channel via Slack API

### Error Handling

**Slack API Errors:**
- Catch error
- Notify `SLACK_ERROR_CHANNEL` with error details
- Include original channel name and error message

**AWS SES Setup Notification:**
- Sender: `no-reply-aws@amazon.com`
- Subject: `Amazon SES Setup Notification`
- → Silently skip (log only)

**Other Exceptions:**
- Log to CloudWatch
- Send to Sentry (if configured)
- Re-throw Lambda exception

## Security Design

### Principle of Least Privilege

**Lambda Execution Role:**
```
- S3 Read: ses-emails/* only
- Secrets Manager Read: Specific secret only
- CloudWatch Logs Write
- X-Ray Write (when enabled)
```

### Data Protection

1. **Encryption in Transit**
   - SES: TLS required
   - S3: SSL enforcement (bucket policy)
   - Secrets Manager: TLS

2. **Encryption at Rest**
   - S3: SSE-S3
   - Secrets Manager: AWS KMS

3. **Data Retention**
   - Emails: Auto-delete after 30 days
   - Access Logs: Auto-delete after 90 days

### Monitoring and Tracing

**AWS X-Ray (Optional):**
- Lambda execution tracing
- Automatic boto3 SDK call tracing
- `get_slack_token()` excluded (prevent token exposure)

**Sentry (Optional):**
- Automatic error capture
- Stack trace recording
- Alert notifications

**CloudWatch Logs:**
- Structured logging (JSON)
- Lambda Powertools Logger
- 1 week retention

## Scalability

### Constraints

1. **SES Email Size Limit**
   - Maximum 10MB (including headers)
   - Approximately 13MB after Base64 encoding

2. **Slack API Rate Limit**
   - Tier 3: 50+ req/min
   - Mitigated by Lambda concurrency limit of 10

3. **Lambda Concurrency**
   - Reserved concurrent executions: 10
   - Queuing during high email volume

### Extensibility

**Future Improvements:**
- SQS queuing
- DynamoDB deduplication
- Step Functions for complex flows
- SNS for multiple notification targets

## Operational Considerations

### Deployment

**Required Steps:**
1. Create Route 53 hosted zone
2. Verify SES Identity (DKIM setup)
3. Configure Slack Bot Token
4. CDK deployment
5. Activate SES RuleSet
6. Invite Slack Bot to channels

**Optional Steps:**
- Remove SES sandbox (production)
- Configure Sentry
- Enable X-Ray

### Monitoring

**Recommended Metrics:**
- Lambda execution error rate
- Lambda execution duration
- S3 bucket size
- Slack API call failure rate

**Alert Examples:**
- Error rate > 5% (5 minutes)
- 3 consecutive errors

### Troubleshooting

**Email Not Received:**
1. Verify SES RuleSet is active
2. Check MX record configuration
3. Confirm SES Identity verification
4. Check CloudWatch Logs for errors

**Slack Notification Not Received:**
1. Verify Bot Token is correct
2. Confirm Bot is invited to channel
3. Check channel name is correct
4. Check CloudWatch Logs for errors

## Cost Estimation

**Assuming 1,000 emails per month:**

- SES: $0.10 (receiving)
- S3: $0.02 (storage) + $0.01 (requests)
- Lambda: $0.20 (execution time)
- Secrets Manager: $0.40 (secret storage)
- Route 53: $0.50 (hosted zone)

**Total: Approximately $1.23/month**

*Actual costs vary based on usage
