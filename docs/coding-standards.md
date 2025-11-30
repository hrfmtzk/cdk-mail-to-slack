# Coding Standards

## Overview

This project maintains code quality and maintainability through the following standards and tools.

## Python Coding Standards

### Basic Principles

- **PEP 8 Compliance**: Follow Python's standard style guide
- **Type Hints Required**: Add type annotations to all functions
- **Docstrings Recommended**: Document public functions with docstrings

### Code Formatting

#### Black

**Configuration (`pyproject.toml`):**
```toml
[tool.black]
line-length = 88
target-version = ['py314']
exclude = '''
/(
    \.git
  | \.venv
  | cdk\.out
  | \.cdk\.staging
)/
'''
```

**Execution:**
```bash
black .
```

#### isort

**Configuration (`pyproject.toml`):**
```toml
[tool.isort]
profile = "black"
line_length = 88
combine_as_imports = true
pythonpath = ["source/email_handler"]
skip_gitignore = true
```

**Execution:**
```bash
isort .
```

### Linters

#### flake8

**Configuration (`pyproject.toml`):**
```toml
[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
exclude = [
    ".git",
    ".venv",
    "cdk.out",
    ".cdk.staging",
]
```

**Execution:**
```bash
flake8
```

#### mypy

**Configuration (`pyproject.toml`):**
```toml
[tool.mypy]
python_version = "3.14"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
exclude = [
    "cdk.out",
    ".cdk.staging",
]
```

**Execution:**
```bash
mypy .
```

## Testing Standards

### Test Coverage

**Target: 80% or higher**

**Configuration (`pyproject.toml`):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["source/email_handler"]
addopts = "--cov --cov-report=html --cov-report=term --cov-fail-under=80"
```

**Execution:**
```bash
pytest
pytest --cov  # With coverage report
```

### Test Types

#### 1. Unit Tests

**Location:** `tests/unit/`

**Target:**
- Lambda function business logic
- CDK stack resource configuration

**Mocking:**
- AWS SDK calls (`boto3`)
- Slack SDK calls
- Environment variables

**Example:**
```python
@patch("main.s3_client")
@patch("main.secrets_client")
@patch("main.WebClient")
def test_handler_success(
    mock_webclient: MagicMock,
    mock_secrets: MagicMock,
    mock_s3: MagicMock,
    s3_event: dict[str, Any],
    sample_email: bytes,
    lambda_context: MagicMock,
) -> None:
    # Test logic
    pass
```

#### 2. Snapshot Tests

**Location:** `tests/snapshot/`

**Target:**
- CDK stack CloudFormation templates

**Purpose:**
- Detect unintended infrastructure changes

#### 3. Integration Tests

**Current Status:** Manual execution

**Future Automation Considerations:**
- Actual email sending
- Slack notification verification
- E2E flow validation

### Test Naming Convention

```python
def test_<target>_<condition>_<expected_result>():
    pass

# Examples:
def test_handler_success()
def test_handler_slack_error_fallback()
def test_extract_channel_invalid_format()
```

## CDK Coding Standards

### Resource Naming

**Prefix:** `MailSlack`

**Examples:**
```python
s3.Bucket(self, "MailSlackS3Bucket", ...)
lambda_.Function(self, "MailSlackLambdaFunction", ...)
```

### CDK Nag Compliance

**Required:** Address all security warnings

**Suppression Requirements:**
- Clear reason description
- Limit scope with `applies_to`

**Example:**
```python
NagSuppressions.add_resource_suppressions(
    resource,
    [
        NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Wildcard permissions are required for X-Ray tracing",
            applies_to=["Resource::*"],
        ),
    ],
)
```

### Configuration Externalization

**Required:** Manage environment-specific values in `config.py`

**Prohibited:** Hardcoded values

**Example:**
```python
# Good
domain_name = config.DOMAIN_NAME

# Bad
domain_name = "example.com"
```

## Lambda Coding Standards

### AWS Lambda Powertools Usage

**Required Tools:**
- `Logger`: Structured logging
- `Tracer`: X-Ray tracing

**Recommended Pattern:**
```python
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    logger.info("Processing event", extra={"event": event})
    # Processing
    return {"statusCode": 200}

@tracer.capture_method
def some_function():
    # Traced by X-Ray
    pass
```

### Error Handling

**Principles:**
1. Catch expected errors appropriately
2. Re-throw unexpected errors
3. Log all errors

**Example:**
```python
try:
    # Main processing
    post_to_slack(client, channel, from_addr, subject, body)
except SlackApiError as e:
    # Expected error: Fallback processing
    logger.error(f"Slack API error: {e.response['error']}")
    post_error_to_slack(client, error_channel, channel, e.response["error"])
except Exception:
    # Unexpected error: Log and re-throw
    logger.exception("Unexpected error")
    raise
```

### Security Considerations

**Prohibited:**
1. Logging secrets
2. Including secrets in X-Ray traces
3. Setting secrets directly in environment variables

**Recommended:**
```python
# Good: Retrieve from Secrets Manager
def get_slack_token() -> str:
    """Get Slack bot token from Secrets Manager.
    
    Note: Not traced with @tracer.capture_method to avoid exposing
    the token in X-Ray traces.
    """
    secret_name = os.environ["SLACK_BOT_TOKEN_SECRET_NAME"]
    response = secrets_client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    return str(secret["SLACK_BOT_TOKEN"])

# Bad: Direct retrieval from environment variable
token = os.environ["SLACK_BOT_TOKEN"]  # NG
```

## Git Standards

### Commit Messages

**Format:**
```
<type>: <subject>

<body>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Refactoring
- `test`: Test addition/modification
- `chore`: Build/tool changes

**Example:**
```
feat: Add Sentry error tracking support

- Add SENTRY_DSN configuration parameter
- Initialize Sentry SDK in Lambda handler
- Add unit tests for Sentry initialization
```

### Branching Strategy

**Recommended:** GitHub Flow

- `main`: Production environment
- `feature/*`: Feature development
- `fix/*`: Bug fixes

### .gitignore

**Required Exclusions:**
- `config.py`: Environment-specific configuration
- `cdk.context.json`: AWS account information
- `.venv/`: Virtual environment
- `cdk.out/`: CDK artifacts
- `*.pyc`, `__pycache__/`: Python cache

## CI/CD Recommended Configuration

### GitHub Actions Example

```yaml
name: Test and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: black --check .
      - run: isort --check .
      - run: flake8
      - run: mypy .
      - run: pytest
      - run: cdk synth
```

## VSCode Configuration

**Project-wide Settings (`.vscode/settings.json`):**
```json
{
  "python.analysis.diagnosticSeverityOverrides": {
    "reportArgumentType": "none"
  }
}
```

**Reason:** Suppress Pylance warnings for CDK JSII-generated type definitions

## Review Criteria

### Pull Request Requirements

**Required:**
- [ ] All tests pass
- [ ] Coverage maintained at 80% or higher
- [ ] No linter/formatter errors
- [ ] CDK Nag warnings addressed
- [ ] Appropriate commit messages

**Recommended:**
- [ ] Change description
- [ ] Screenshots (for UI changes)
- [ ] Breaking changes noted

### Code Review Points

1. **Security**
   - No secret leakage
   - Principle of least privilege
   - Input validation

2. **Performance**
   - No unnecessary API calls
   - Appropriate error handling
   - Resource limit considerations

3. **Maintainability**
   - Appropriate naming
   - Comments/docstrings
   - Test coverage

4. **Best Practices**
   - DRY principle
   - SOLID principles
   - AWS Well-Architected Framework
