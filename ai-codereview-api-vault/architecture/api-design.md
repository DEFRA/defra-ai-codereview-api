# API Design

## RESTful Endpoints

### Base URL: `/api/v1`

#### Code Reviews Resource

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/code-reviews` | Create new review |
| GET | `/code-reviews` | List all reviews |
| GET | `/code-reviews/{id}` | Get specific review |

## Request/Response Format

### Create Code Review

**Request:**
```json
{
    "repository_url": "string"
}
```

**Response:**
```json
{
    "_id": "string",
    "repository_url": "string",
    "status": "started",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## Status Codes

- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Server Error

## Authentication & Authorization

*Future Implementation:*
- API key authentication
- Role-based access control
- Rate limiting 