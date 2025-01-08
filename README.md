# Code Review API

A Python FastAPI service that provides endpoints for creating and retrieving code reviews, with asynchronous analysis using Anthropic's API.

## Features

- Create and retrieve code reviews
- Asynchronous code analysis workflow
- MongoDB storage
- Anthropic API integration
- Structured logging
- Health check endpoint

## Prerequisites

- Python 3.8+
- MongoDB (running in Docker)
- Anthropic API key

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
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
```env
MONGO_URI=mongodb://root:example@localhost:27017/
ANTHROPIC_API_KEY=your_anthropic_api_key
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

## Running the API

Start the FastAPI server:

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Create a Code Review

```http
POST /api/v1/code-reviews
Content-Type: application/json

{
    "repository_url": "https://github.com/user/repo"
}
```

### List All Code Reviews
`
```http
GET /api/v1/code-reviews
```

### Get a Specific Code Review

```http
GET /api/v1/code-reviews/{review_id}
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

## Environment Variables

| Variable | Description | Required |
|----------|-------------|-----------|
| MONGO_URI | MongoDB connection string | Yes |
| ANTHROPIC_API_KEY | Anthropic API key | Yes |

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