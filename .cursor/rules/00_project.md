# Project Overview

## Stack
- Python
- FastAPI
- Anthropic
- MongoDB

## Directory Structure
```
src/
├── api/v1/      # Routing and HTTP endpoints
├── services/    # Business logic
├── repositories/# Data access
├── agents/      # AI agents
├── utils/       # Utility functions
├── config/      # Configuration
├── database/    # Database operations
└── models/      # Data models
```

## Key Principles
- Security-first approach
- Clean code practices
- Async by default

## Git Commits
- Use conventional commit prefixes (feat:, fix:, etc.)
- Keep messages concise and reference issues

## Security
- No secrets in code
- Validate inputs
- Encrypt sensitive data