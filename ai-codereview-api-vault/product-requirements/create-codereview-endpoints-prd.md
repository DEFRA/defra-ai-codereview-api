# PRD: Python FastAPI Code Review API

> **Version:** 1.0  
> **Last Updated:** 2025-01-08  

## 1. Overview

This Product Requirements Document (PRD) outlines the features and functionality of a **Python FastAPI** server that will:

- Provide endpoints for creating and retrieving *code review* records
- Communicate with a **MongoDB** instance (running locally via Docker) to store these records
- Manage a code review workflow against multiple standards
- Initialize an **agentic workflow** using **Anthropic's API** (currently returning a simple test response)

**Goal**: Provide a robust and extensible platform to manage, track, and analyze code bases against various standards in an automated and asynchronous manner.

## 2. Objectives and Goals

1. **Centralized Record Management**:
   - Store and track code reviews in MongoDB
   - Leverage FastAPI to expose CRUD endpoints

2. **Asynchronous Processing**:
   - Trigger an asynchronous analysis workflow upon record creation

3. **Scalable and Modular Design**:
   - Use environment-based configuration for local, development, test, and production
   - Dockerize MongoDB for easy local setup and consistent environments

4. **Agentic Workflow Integration**:
   - Introduce a placeholder agentic workflow using Anthropic API calls (simple "hello world" request)
   - Build a foundation for future enhancements (e.g., real code analysis logic)

## 3. Scope and Functional Requirements

### 3.1 High-Level Architecture

```
            +---------------------+
            |   FASTAPI Server    |
            |  (/api/v1/...)      |
            +---------+-----------+
                      |
                      |  (1) Create / GET code reviews
                      |
              +-------v--------+
              |   MongoDB      |
              |  (Docker)      |
              +----------------+
                      ^
                      |
                      | (2) Asynchronous
                      |
            +---------+-----------+
            |  Agentic Workflow   |
            | (Anthropic API)     |
            +---------------------+
```

1. **Client** sends requests to `FastAPI` server
2. **FastAPI** server creates/retrieves code review records from **MongoDB**
3. **POST** requests trigger an **asynchronous agentic workflow** (Anthropic API)
4. **MongoDB** is used to persist the data and track status

### 3.2 API Endpoints

All endpoints are under the prefix `/api/v1`.

#### 3.2.1 `POST /api/v1/code-reviews`

1. **Create a new code review record** in MongoDB
   - The new record should have an initial status of `started`
2. **Return** the newly created record with its status to the caller
3. **Trigger** an asynchronous agentic workflow (placeholder call to Anthropic API returning `{"success": true}`)

**Request Body** (JSON):
```json
{
  "repositoryUrl": "string"
}
```

**Response** (JSON):
```json
{
  "_id": "object_id",
  "repositoryUrl": "string",
  "status": "started"
}
```

#### 3.2.2 `GET /api/v1/code-reviews`

Return an array of all existing code review records.

**Response** (JSON):
```json
[
  {
    "_id": "object_id",
    "repositoryUrl": "string",
    "status": "started",
  },
  {
    "_id": "object_id_2",
    "repositoryUrl": "string2",
    "status": "completed"
  }
]
```

#### 3.2.3 `GET /api/v1/code-reviews/{id}`

Return a single code review record by its id. Include any relevant status information.

**Response** (JSON):
```json
{
  "_id": "object_id",
  "repositoryUrl": "string",
  "status": "started"
}
```

### 3.3 Data Model

A CodeReview document in MongoDB may have fields (subject to expansion):

| Field         | Type     | Description                          | Example                            |
| ------------- | -------- | ------------------------------------ | ---------------------------------- |
| _id           | ObjectId | Unique identifier (auto-generated)   | ObjectId("...")                    |
| repositoryUrl | String   | The URL/path for the code repository | "https://github.com/user/repo"     |
| status        | String   | Status of the review                 | "started" / "completed" / "failed" |
| createdAt     | DateTime | Timestamp of creation                | "2025-01-08T12:34:56Z"             |
| updatedAt     | DateTime | Timestamp of last update             | "2025-01-08T12:35:00Z"             |

Status Lifecycle (example):
- started: upon creation
- completed: once the analysis is done
- failed: status if the analysis fails

### 3.4 Agentic Workflow via Anthropic API

**Trigger**: A POST /code-reviews call triggers the agentic workflow asynchronously.

**Initial Implementation**:
- Simple "Hello World" request to Anthropic's API, using structured outputs feature
- Returns {"success": true}

**Future Enhancement**:
- Analyze the provided code base
- Generate a structured report
- Update the CodeReview record status and store the report in MongoDB

## 4. Non-Functional Requirements

**Data Validation**:
- Validate request payloads to prevent injection or malformed data

**MongoDB Security**:
- Restrict connections to the Docker container network for local development
- Use proper credentials in dev/test/production

### 4.3 Logging and Monitoring

**Logging**:
- Log critical points such as code review creation, workflow start, and completion

**Monitoring**:
- Track container health and resource usage
- Expose health-check endpoints if needed (/health)

### 4.4 Error Handling

**HTTP Status Codes**:
Follow the REST standard for all status codes:
- 201 for successful creation, 200 for retrieval
- 400 if request payload is invalid
- 404 if a record is not found
- 500 for internal failure

**Graceful Failures**:
- If the agentic workflow fails, capture the error message in the code review record for visibility

## 5. Environment Configuration

We will maintain separate configurations for:

### 5.1 Local

- MongoDB: Runs in a local Docker container, using a default username/password
- FastAPI: Runs locally
- Anthropic API: use anthropic api key in the environment files

### 5.2 Development

- TBD

### 5.3 Test

- TBD

### 5.4 Production

- TBD

## 6. Deployment

### 6.1 Docker and MongoDB Setup

MongoDB on Docker
- Install as per standard

**FastAPI**:
- Connect to the mongo service via environment variables

## 7. Appendix

### Sample .env Files

**.env.local**:
```makefile
MONGO_URI=mongodb://root:example@localhost:27017/
ANTHROPIC_API_KEY=your_local_test_key
```

**.env.dev**:
```makefile
MONGO_URI=mongodb://root:example@dev_mongo:27017/
ANTHROPIC_API_KEY=your_dev_key
```

**.env.test**:
```makefile
MONGO_URI=mongodb://root:example@test_mongo:27017/
ANTHROPIC_API_KEY=your_test_key
```

**.env.production**:
```makefile
MONGO_URI=mongodb://root:strong_password@prod_mongo:27017/
ANTHROPIC_API_KEY=your_prod_key
```

(Use a secrets manager or environment variables in your CI/CD pipeline instead of committing these files.)
