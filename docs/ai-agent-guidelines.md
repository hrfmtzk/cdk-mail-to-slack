# AI Agent Guidelines

## Overview

This document defines the code of conduct and guidelines for AI agents (GitHub Copilot, Amazon Q Developer, and other code generation AIs) when working on this project.

## Required Reading

AI agents should reference the following documents before generating code or proposing changes:

1. **[design.md](./design.md)** - System design and architecture
2. **[coding-standards.md](./coding-standards.md)** - Coding standards and tool configuration
3. **[README.md](../README.md)** - Project overview and setup instructions

## Code Generation Principles

### 1. Minimal Implementation

**Principle:** Generate only the minimum code necessary to meet requirements

**Rationale:**
- Improved maintainability
- Easier testing
- Avoid unnecessary complexity

**Example:**
```python
# Good: Simple and clear
def extract_channel_from_email(to_address: str, domain: str) -> str:
    match = re.match(rf"(.+)@{re.escape(domain)}", to_address)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid email format: {to_address}")

# Bad: Overly complex
def extract_channel_from_email(to_address: str, domain: str) -> str:
    # Unnecessary validation, logging, exception handling
    # Multiple regex patterns
    # Unnecessary helper functions
    pass
```

### 2. Follow Existing Patterns

**Principle:** Maintain existing coding patterns within the project

**Check:**
- Naming conventions (`MailSlack` prefix)
- Error handling patterns
- Log output format
- Test structure

### 3. Type Safety

**Principle:** Add type hints to all functions

**Required:**
```python
from typing import Any, Dict

def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    pass
```

**Prohibited:**
```python
def handler(event, context):  # No type hints
    pass
```

## Security Guidelines

### Absolute Prohibitions

1. **Hardcoded Secrets**
   ```python
   # NG
   SLACK_TOKEN = "xoxb-1234567890-..."
   
   # OK
   slack_token = get_slack_token()  # Retrieve from Secrets Manager
   ```

2. **Logging Secrets**
   ```python
   # NG
   logger.info(f"Token: {slack_token}")
   
   # OK
   logger.info("Retrieved Slack token from Secrets Manager")
   ```

3. **Including Secrets in X-Ray Traces**
   ```python
   # NG
   @tracer.capture_method
   def get_slack_token() -> str:
       pass
   
   # OK (no decorator)
   def get_slack_token() -> str:
       """Note: Not traced to avoid exposing token in X-Ray traces."""
       pass
   ```

### Principle of Least Privilege

**When generating IAM policies:**
- Specify resource ARNs explicitly
- Minimize wildcards (`*`)
- Provide clear reasons for CDK Nag suppressions

```python
# Good
email_bucket.grant_read(lambda_function, "ses-emails/*")

# Bad
email_bucket.grant_read(lambda_function)  # Entire bucket
```

## Testing Requirements

### When Adding New Features

**Required:**
1. Add unit tests
2. Maintain coverage at 80% or higher
3. Do not break existing tests

**Test Pattern:**
```python
@patch("main.s3_client")
@patch("main.secrets_client")
def test_new_feature(mock_secrets, mock_s3):
    # Arrange
    mock_s3.get_object.return_value = {...}
    
    # Act
    result = new_function()
    
    # Assert
    assert result == expected_value
    mock_s3.get_object.assert_called_once()
```

### When Fixing Bugs

**Required:**
1. Create test that reproduces the bug first
2. Verify test passes after fix
3. Keep as regression test

## CDK Resource Generation

### Resource Naming

**Pattern:**
```python
resource = ResourceType(
    self,
    "MailSlack<ResourceName>",  # Construct ID
    resource_name="MailSlackResourceName",  # Physical name (optional)
    ...
)
```

### CDK Nag Compliance

**When warnings occur:**

1. **Try to fix first**
   ```python
   # Warning: S3 bucket lacks SSL enforcement
   # → Add SSL enforcement via bucket policy
   ```

2. **Suppress only with valid reason**
   ```python
   NagSuppressions.add_resource_suppressions(
       resource,
       [
           NagPackSuppression(
               id="AwsSolutions-XXX",
               reason="Clear reason description",
               applies_to=["Specific resource"],
           ),
       ],
   )
   ```

### Configuration Externalization

**Required:** Retrieve environment-specific values from `config.py`

```python
# Good
domain_name = config.DOMAIN_NAME

# Bad
domain_name = "example.com"
```

## Code Change Checklist

### Before Changes

- [ ] Review existing code patterns
- [ ] Review related tests
- [ ] Review documentation

### After Changes

- [ ] Format with `black .`
- [ ] Organize imports with `isort .`
- [ ] Check with `flake8`
- [ ] Type check with `mypy .`
- [ ] Run tests with `pytest`
- [ ] Verify CDK with `cdk synth`

### Before Commit

- [ ] Appropriate commit message
- [ ] Verify no unnecessary files included
- [ ] Check `.gitignore`

## Special Cases

### AWS SES Setup Notification

**Background:** AWS sends notification email when ReceiptRule is created

**Handling:** Skip silently

```python
# Skip AWS SES setup notification emails
if (
    from_address == "Amazon Web Services <no-reply-aws@amazon.com>"
    and subject == "Amazon SES Setup Notification"
):
    logger.info("Skipping AWS SES setup notification email")
    return {"statusCode": 200, "body": "Skipped setup notification"}
```

### MIME Encoded Subjects

**Background:** Subjects in Japanese etc. are encoded in RFC 2047 format

**Handling:** Decode with `email.header.decode_header()`

```python
def decode_mime_header(header: str) -> str:
    """Decode MIME encoded header (RFC 2047)."""
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            decoded_parts.append(
                part.decode(encoding or "utf-8", errors="replace")
            )
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts)
```

### ReceiptRule Unification

**Background:** Code was duplicated between existing RuleSet usage and new creation

**Handling:** Unify RuleSet retrieval and use `add_rule()` for common processing

```python
# Get or create SES receipt rule set
if use_existing_rule_set:
    rule_set = ses.ReceiptRuleSet.from_receipt_rule_set_name(...)
else:
    rule_set = ses.ReceiptRuleSet(...)

# Common rule creation
rule_set.add_rule(
    "MailSlackRule",
    recipients=rule_recipients,
    actions=rule_actions,
    after=after_rule,
    tls_policy=ses.TlsPolicy.REQUIRE,
    scan_enabled=True,
)
```

## Error Messages

### User-Facing Errors

**Principle:** Provide clear and actionable information

```python
# Good
raise ValueError(
    "existing_rule_set_name must be specified when "
    "use_existing_rule_set=True"
)

# Bad
raise ValueError("Invalid configuration")
```

### Log Messages

**Principle:** Include context information with structured logging

```python
# Good
logger.info(
    "Processing email",
    extra={
        "bucket": bucket,
        "key": key,
        "channel": channel,
    }
)

# Bad
logger.info(f"Processing {key}")
```

## Performance Considerations

### Lambda Optimization

1. **Initialize in Global Scope**
   ```python
   # Good: Execute only during cold start
   s3_client = boto3.client("s3")
   secrets_client = boto3.client("secretsmanager")
   
   def handler(event, context):
       # Reuse clients
       pass
   ```

2. **Skip Unnecessary Processing**
   ```python
   # Early return for AWS notification emails
   if is_aws_notification(from_address, subject):
       return {"statusCode": 200, "body": "Skipped"}
   
   # Heavy processing (S3 retrieval, Slack API calls) not executed
   ```

3. **Concurrency Control**
   ```python
   # Configure in CDK
   reserved_concurrent_executions=10  # Slack API rate limit mitigation
   ```

## Documentation Updates

### When Code Changes

**Documentation update required for:**
- New feature addition
- Configuration parameter addition
- Architecture changes
- Security requirement changes

**Update Targets:**
- `README.md` and `README_ja.md`: User-facing instructions
- `docs/design.md` and `docs/design_ja.md`: System design
- `docs/coding-standards.md` and `docs/coding-standards_ja.md`: Standards changes
- `docs/ai-agent-guidelines.md`: AI guidelines (English only)

**Important:** This project maintains both English and Japanese documentation. When updating documentation:
1. Update English version (main)
2. Update Japanese version (`*_ja.md`)
3. Ensure consistency between versions
4. Update cross-references if needed

**Exception:** `ai-agent-guidelines.md` is English-only (not read by humans)

## Questions and Clarifications

### When Uncertain

**Recommended Actions:**
1. Check existing code patterns
2. Re-review documentation
3. Reference test code
4. Choose conservative implementation

**Avoid:**
- Implementation based on guesswork
- Overly complex solutions
- Security-risky implementations

## Version Control

This guideline is updated as the project evolves.

**Last Updated:** 2025-11-30
**Version:** 1.0.0
