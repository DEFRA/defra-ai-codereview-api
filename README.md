# Code Review API

A Python FastAPI service that provides endpoints for creating and retrieving AI-powered code reviews, with asynchronous analysis using Anthropic's API.

## Features

- Create and retrieve code reviews
- Asynchronous code analysis workflow
- MongoDB storage with schema validation
- Anthropic API integration for intelligent code analysis
- Structured logging with configurable outputs
- Health check endpoint with database connectivity status
- Standard sets management for code review rules
- Classification system for technology-specific standards
- Git repository analysis and cloning
- Comprehensive test coverage

## Prerequisites

- Python 3.12.8+
- MongoDB 6.0+ (running in Docker)
- Anthropic API key
- Git (for repository analysis)

## Installation

0. Ensure you have the correct Python version:
```bash
# Install Python 3.12.8 if not already installed
pyenv install 3.12.8

# Set local Python version
pyenv local 3.12.8
```

1. Clone the repository:
```bash
git clone <repository-url>
cd code-review-api
```

2. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```env
See .env.example for required variables
```

## Running MongoDB

Start MongoDB using Docker Compose:

```bash
# Start MongoDB
docker-compose up -d mongodb

# Check MongoDB status
docker-compose ps

# View MongoDB logs
docker-compose logs -f mongodb

# Stop MongoDB
docker-compose down
```

The MongoDB data will persist in a named volume `code_review_mongodb_data`.

### MongoDB Schema Validation

The database uses schema validation to ensure data integrity:

- **Classifications**: Stores technology/language classifications
- **Standard Sets**: Contains predefined sets of standards with repository links
- **Standards**: Individual standards with text content and classifications
- **Code Reviews**: Review requests and results with compliance reports

Schema validation is automatically applied during database initialisation.

## Running the API

Start the FastAPI server:

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Code Reviews

```http
# Create a Code Review
POST /api/v1/code-reviews
Content-Type: application/json

{
    "repository_url": "https://github.com/user/repo",
    "standard_sets": ["python", "security"]
}

# List All Code Reviews
GET /api/v1/code-reviews

# Get a Specific Code Review
GET /api/v1/code-reviews/{_id}
```

### Standard Sets

```http
# Create a Standard Set
POST /api/v1/standard-sets
Content-Type: application/json

{
    "name": "python",
    "repository_url": "https://github.com/org/standards",
    "custom_prompt": "Optional custom prompt for analysis"
}

# List All Standard Sets
GET /api/v1/standard-sets
```

### Classifications

```http
# Create a Classification
POST /api/v1/classifications
Content-Type: application/json

{
    "name": "python"
}

# List All Classifications
GET /api/v1/classifications
```

### Health Check

```http
GET /health
```

## Documentation

API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Project Structure

```
src/
├── __init__.py
├── config.py           # Configuration management
├── database.py         # MongoDB connection
├── logging_config.py   # Logging setup
├── models/
│   ├── __init__.py
│   └── code_review.py  # CodeReview model
├── services/
│   ├── __init__.py
│   └── anthropic.py    # Anthropic API integration
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       └── code_reviews.py  # API endpoints
└── main.py            # FastAPI application
```

### Running Tests

```bash
pytest
```


## Error Handling

The API uses standard HTTP status codes:
- 200: Successful GET request
- 201: Successful POST request
- 400: Invalid input
- 404: Resource not found
- 500: Internal server error

## Logging

The application uses structured logging with the following format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Logs are written to stdout and can be redirected as needed.

## License

[License Type] - See LICENSE file for details