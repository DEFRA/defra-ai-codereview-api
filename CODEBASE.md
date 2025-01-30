# Defra AI Code Review API - Codebase Documentation

## Project Structure

```
src/
├── agents/           # AI agents for different functionalities
├── api/             # API endpoints and routes
│   └── v1/         # Version 1 API implementations
├── models/          # Data models and schemas
├── repositories/    # Data access layer
├── services/        # Business logic services
├── utils/          # Utility functions and helpers
├── config.py       # Configuration settings
├── database.py     # Database connection handling
├── database_init.py # Database initialization
├── dependencies.py  # FastAPI dependencies
├── logging_config.py # Logging configuration
└── main.py         # Application entry point

tests/
├── integration/    # Integration tests
├── unit/          # Unit tests
├── e2e/           # End-to-end tests
├── utils/         # Test utilities
└── conftest.py    # Test configuration and fixtures
```

## Source Files (src/)

### Core Files

#### main.py
- **Purpose**: FastAPI application entry point
- **Functionality**: Sets up API routes, CORS middleware, and database initialization
- **Dependencies**: FastAPI, MongoDB

#### config.py
- **Purpose**: Application configuration management
- **Functionality**: Manages environment variables and settings
- **Dependencies**: pydantic

#### database.py
- **Purpose**: Database connection management
- **Functionality**: Provides MongoDB connection and session handling
- **Dependencies**: Motor (MongoDB async driver)

#### database_init.py
- **Purpose**: Database initialization and schema validation
- **Functionality**: 
  - Creates MongoDB collections with schema validation
  - Defines validation schemas for:
    - Classifications
    - Standard Sets
    - Standards
    - Code Reviews
  - Handles collection creation and schema updates
- **Dependencies**: MongoDB, Motor

#### dependencies.py
- **Purpose**: FastAPI dependency injection
- **Functionality**: Provides database and service dependencies
- **Dependencies**: FastAPI

#### logging_config.py
- **Purpose**: Logging configuration
- **Functionality**: Sets up application logging
- **Dependencies**: Python logging

### API Layer (api/v1/)

- **code_reviews.py**: Handles code review endpoints
- **classifications.py**: Manages classification endpoints
- **standard_sets.py**: Standard set management endpoints

### Agents (agents/)

- **git_repos_agent.py**: Git repository analysis agent
- **standards_agent.py**: Code standards evaluation agent

## Test Files (tests/)

### Integration Tests

#### test_code_reviews_api.py
- **Category**: API Test
- **Tests**: Code review endpoints
- **Coverage**: Request validation, response formats
- **Mocks**: MongoDB, Git operations

#### test_classifications.py
- **Category**: API Test
- **Tests**: Classification endpoints
- **Coverage**: CRUD operations
- **Mocks**: MongoDB

#### test_standard_sets.py
- **Category**: API Test
- **Tests**: Standard set management
- **Coverage**: CRUD operations, validation
- **Mocks**: MongoDB

### Unit Tests
- Tests for individual components and utilities
- Focus on isolated functionality
- Heavy use of mocking for external dependencies

### End-to-End Tests
- Full system integration tests
- Tests complete user workflows
- Minimal mocking, uses test databases

### Test Configuration (conftest.py)
- Provides test fixtures
- Sets up mock MongoDB
- Configures FastAPI test client
- Manages test environment variables

## Key Relationships

1. Each API endpoint in `src/api/v1/` has corresponding integration tests in `tests/integration/`
2. Agent implementations in `src/agents/` are tested through both unit and integration tests
3. Utility functions in `src/utils/` have corresponding unit tests in `tests/unit/utils/`
4. Database operations are tested using mock MongoDB in integration tests

## Configuration Files

- `.env`: Environment variables (not in version control)
- `.env.example`: Example environment variable template
- `.env.test`: Test environment configuration
- `requirements.txt`: Python dependencies

## Test Coverage Focus

1. API Endpoints
   - Request validation
   - Response formats
   - Error handling
   - Authentication/Authorization

2. Database Operations
   - CRUD operations
   - Error conditions
   - Connection handling

3. Agent Operations
   - Code analysis
   - Standards evaluation
   - Git operations

4. Utilities
   - Input validation
   - Token counting
   - ID validation 