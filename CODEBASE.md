# Defra AI Code Review API - Codebase Documentation

## Project Structure

```
src/
├── agents/           # AI agents for code review and analysis
│   ├── code_reviews_agent.py    # Code review processing
│   ├── git_repos_agent.py       # Git repository handling
│   ├── standards_agent.py       # Standards evaluation
│   └── standards_classification_agent.py  # Standards classification
├── api/             # API endpoints and routes
│   ├── dependencies.py          # FastAPI dependencies
│   └── v1/                      # Version 1 API implementations
│       ├── code_reviews.py      # Code review endpoints
│       ├── classifications.py   # Classification endpoints
│       ├── health.py           # Health check endpoint
│       └── standard_sets.py    # Standard set endpoints
├── config/         # Configuration modules and settings
│   ├── config.py              # Environment configuration
│   └── logging_config.py      # Logging configuration
├── database/       # Database operations and initialization
│   ├── mongodb.py            # MongoDB connection
│   └── schema_validation.py  # Collection schemas
├── models/         # Data models and schemas
│   ├── code_review.py        # Code review models
│   ├── classification.py     # Classification models
│   ├── standard_set.py       # Standard set models
│   └── common.py            # Shared model components
├── repositories/   # Data access layer
│   ├── code_reviews.py      # Code review operations
│   ├── classifications.py   # Classification operations
│   └── standard_sets.py    # Standard set operations
├── services/       # Business logic services
│   ├── code_review_service.py   # Code review logic
│   ├── classification_service.py # Classification logic
│   └── standard_set_service.py  # Standard set logic
├── utils/          # Utility functions and helpers
│   ├── anthropic_client.py     # Anthropic API client
│   ├── git_utils.py           # Git operations
│   └── validators.py         # Input validation
└── main.py         # Application entry point

tests/
├── integration/    # Integration tests
│   ├── test_code_reviews_api.py
│   ├── test_classifications_api.py
│   └── test_standard_sets_api.py
├── unit/          # Unit tests
│   ├── agents/
│   ├── services/
│   ├── repositories/
│   └── utils/
├── utils/         # Test utilities
└── conftest.py    # Test configuration and fixtures

scripts/           # Utility scripts
├── setup_db.py    # Database setup
└── seed_data.py   # Test data generation

logs/              # Application logs
test_data/         # Test fixtures and data
```

## Key Components

### Agents

#### code_reviews_agent.py
- **Purpose**: Manages code review workflow
- **Features**: 
  - Repository analysis
  - Standards compliance checking
  - Report generation
- **Dependencies**: Anthropic, Git

#### standards_classification_agent.py
- **Purpose**: Classifies code standards
- **Features**:
  - Technology detection
  - Standard categorisation
  - Rule matching
- **Dependencies**: Anthropic

### API Endpoints

#### code_reviews.py
- **Routes**: 
  - POST /code-reviews
  - GET /code-reviews
  - GET /code-reviews/{id}
- **Features**:
  - Async processing
  - Status tracking
  - Error handling

#### standard_sets.py
- **Routes**:
  - POST /standard-sets
  - GET /standard-sets
  - PUT /standard-sets/{id}
- **Features**:
  - Version control
  - Custom prompts
  - Repository linking

## Test Coverage

### Integration Tests

#### test_code_reviews_api.py
- **Coverage**: 95%
- **Focus Areas**:
  - Request validation
  - Async processing
  - Error scenarios
  - Database operations

#### test_classifications_api.py
- **Coverage**: 90%
- **Focus Areas**:
  - Classification logic
  - Data validation
  - Error handling

### Unit Tests

#### agents/
- **Coverage**: 85%
- **Components**:
  - AI processing
  - Git operations
  - Standards evaluation

#### services/
- **Coverage**: 92%
- **Components**:
  - Business logic
  - Data transformation
  - Error handling

## Configuration Files

### .env
- MongoDB connection
- Anthropic API key
- Logging settings
- Git configuration

### pytest.ini
- Test configuration
- Coverage settings
- Marker definitions

### .pylintrc
- Code style rules
- Error checking
- Naming conventions

## Development Workflow

1. Code Changes
   - Follow PEP 8
   - Add type hints
   - Update tests

2. Testing
   - Run unit tests
   - Run integration tests
   - Check coverage

3. Documentation
   - Update docstrings
   - Update README
   - Update API docs

4. Review
   - Run linters
   - Check types
   - Verify coverage 