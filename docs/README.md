# Documentation

This directory contains technical documentation for the CDK Mail to Slack project.

## Document List

### Human-Readable Documentation

#### [System Design (design.md)](./design.md)
Detailed explanation of system architecture, component configuration, processing flow, and security design.

**Main Contents:**
- System architecture diagram
- Key component descriptions
- Processing flow (normal flow, error handling)
- Security design
- Scalability and constraints
- Operational considerations
- Cost estimation

**Target Audience:**
- System architects
- Developers
- Operations staff

**Japanese Version:** [design_ja.md](./design_ja.md)

#### [Coding Standards (coding-standards.md)](./coding-standards.md)
Defines coding standards, tool configurations, and testing requirements used in the project.

**Main Contents:**
- Python coding standards
- Code formatting (Black, isort)
- Linters (flake8, mypy)
- Testing standards and coverage requirements
- CDK coding standards
- Lambda coding standards
- Git standards
- CI/CD recommended configuration
- Code review criteria

**Target Audience:**
- Developers
- Code reviewers
- New contributors

**Japanese Version:** [coding-standards_ja.md](./coding-standards_ja.md)

### AI Agent Documentation

#### [AI Agent Guidelines (ai-agent-guidelines.md)](./ai-agent-guidelines.md)
Guidelines and code of conduct for AI agents (GitHub Copilot, Amazon Q Developer, etc.) when generating code or proposing changes.

**Main Contents:**
- Code generation principles
- Security guidelines
- Testing requirements
- CDK resource generation rules
- Code change checklist
- Special case handling
- Performance considerations
- Documentation update rules

**Target Audience:**
- AI code generation tools
- Developers using AI-assisted development

**Note:** Japanese version not provided as this is primarily for AI consumption.

## Quick Reference

### For New Developers

1. **Documents to Read First:**
   - [Project README](../README.md) - Setup instructions
   - [System Design](./design.md) - Architecture understanding
   - [Coding Standards](./coding-standards.md) - Development rules

2. **Pre-Development Checklist:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt -r requirements-dev.txt
   
   # Run tests
   pytest
   
   # Code quality checks
   black --check .
   isort --check .
   flake8
   mypy .
   ```

### For AI-Assisted Development

1. **AI Agent Configuration:**
   - Refer to [AI Agent Guidelines](./ai-agent-guidelines.md)
   - Provide as project context

2. **Code Generation Notes:**
   - Minimal implementation
   - Security requirements compliance
   - Simultaneous test generation

### Troubleshooting

**When Issues Occur:**

1. **Email Reception Issues:**
   - Refer to [System Design - Troubleshooting](./design.md#troubleshooting)

2. **Code Quality Issues:**
   - Check [Coding Standards](./coding-standards.md)
   - Run linters/formatters

3. **Deployment Issues:**
   - Refer to [Project README - Deployment](../README.md#6-deployment)

## Documentation Update Guidelines

### When Updates Are Needed

Update related documentation when making the following changes:

- **New Feature** → design.md, README.md
- **Configuration Parameter Addition** → README.md, design.md
- **Coding Standards Change** → coding-standards.md
- **Architecture Change** → design.md
- **Security Requirements Change** → design.md, ai-agent-guidelines.md

### Update Procedure

1. Edit relevant documentation
2. Note changes in commit message
3. Explain changes in pull request

## Related Links

### External Documentation

- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [AWS Lambda Powertools Python](https://docs.powertools.aws.dev/lambda/python/)
- [Slack API Documentation](https://api.slack.com/)
- [Amazon SES Developer Guide](https://docs.aws.amazon.com/ses/latest/dg/)

### Project Resources

- [GitHub Repository](https://github.com/hrfmtzk/cdk-mail-to-slack)
- [Issue Tracker](https://github.com/hrfmtzk/cdk-mail-to-slack/issues)

## Feedback

For documentation improvement suggestions or error reports, please use [GitHub Issues](https://github.com/hrfmtzk/cdk-mail-to-slack/issues) or Pull Requests.

---

**Last Updated:** 2025-11-30
