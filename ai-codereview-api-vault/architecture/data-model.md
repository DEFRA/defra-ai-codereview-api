# Data Model Architecture

## MongoDB Schema

### CodeReview Collection

```typescript
interface CodeReview {
    _id: ObjectId;              // Unique identifier
    repository_url: string;     // Repository URL to analyze
    status: ReviewStatus;       // Current review status
    created_at: DateTime;       // Creation timestamp
    updated_at: DateTime;       // Last update timestamp
}

enum ReviewStatus {
    STARTED = "started",
    COMPLETED = "completed",
    FAILED = "failed"
}
```

## Model Relationships

Currently, the system uses a single collection design. Future extensions might include:
- Analysis results collection
- Standards/rules collection
- User/organization collections

## Data Validation

1. **Application Layer**
   - Pydantic models enforce schema validation
   - Type checking for all fields
   - Custom validators for URLs

2. **Database Layer**
   - MongoDB schema validation
   - Indexes for efficient queries
   - Timestamp management 