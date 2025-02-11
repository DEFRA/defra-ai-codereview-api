# Standards Agent Integration Tests

## Overview

The Standards Agent is responsible for processing and analyzing standard sets from repositories. It integrates with multiple components and external dependencies to achieve its functionality.

### Main Entry Point
- Primary function: `process_standard_set(standard_set_id: str, repository_url: str)`
- Purpose: Processes a standard set by downloading a repository, analyzing standards, and storing results in the database

### External Dependencies
1. Database (MongoDB)
   - Collections: standards, classifications
   - Repositories: ClassificationRepository, StandardSetRepository

2. Git Operations
   - Clone repositories
   - Temporary file system operations

3. LLM Integration (Anthropic/Claude)
   - Used for analyzing standards and determining classifications

4. File System Operations
   - Temporary directory management
   - File reading/writing

## Integration Test Strategy

### Test Categories

1. Happy Path Tests
2. Error Handling Tests
3. Edge Cases
4. External Dependency Tests

### Test Specifications

#### 1. Complete Standard Set Processing

Given:
- A valid standard set ID exists in the database
- A valid repository URL containing markdown standards
- Classifications exist in the database
- All external services are available

When:
- The process_standard_set function is called with the standard set ID and repository URL

Then:
- The repository should be successfully cloned
- Standards should be extracted from markdown files
- Each standard should be analyzed for classifications
- Standards should be stored in the database with correct classifications
- Temporary resources should be cleaned up
- No errors should be raised

#### 2. Repository Processing

Given:
- A valid repository URL
- The repository contains a mix of markdown and non-markdown files
- Some files are in subdirectories

When:
- The download_repository function is called

Then:
- A temporary directory should be created
- The repository should be cloned successfully
- The function should return a valid Path object
- The cloned repository should contain all expected files
- Non-markdown files should be present but ignored in processing

#### 3. Classification Analysis

Given:
- A standard's content
- A list of valid classifications from the database
- The LLM service is available

When:
- The analyze_standard function is called

Then:
- The LLM should receive a well-formatted prompt
- The response should be parsed correctly
- The returned classifications should be valid and exist in the database
- Universal standards should return an empty classification list
- The function should handle both single and multiple classifications

#### 4. Error Handling - Database Unavailable

Given:
- A valid standard set ID and repository URL
- The database connection is unavailable

When:
- The process_standard_set function is called

Then:
- The function should raise an appropriate error
- Any temporary resources should be cleaned up
- No partial data should be persisted
- Error should be logged with appropriate context

#### 5. Error Handling - Invalid Repository

Given:
- A valid standard set ID
- An invalid or inaccessible repository URL

When:
- The process_standard_set function is called

Then:
- The function should raise an appropriate error
- No standards should be processed or stored
- Temporary resources should be cleaned up
- Error should be logged with appropriate context

#### 6. Error Handling - LLM Service Unavailable

Given:
- A valid standard set and repository
- The LLM service is unavailable

When:
- The process_standard_set function is called

Then:
- The function should raise an appropriate error
- Partial results should not be stored
- Temporary resources should be cleaned up
- Error should be logged with appropriate context

#### 7. Edge Case - Empty Repository

Given:
- A valid standard set ID
- A repository URL pointing to an empty repository

When:
- The process_standard_set function is called

Then:
- The function should complete successfully
- No standards should be stored
- Appropriate logging should indicate no standards found
- Temporary resources should be cleaned up

#### 8. Edge Case - Large Standards

Given:
- A valid standard set ID
- A repository containing very large markdown files
- Valid classifications

When:
- The process_standard_set function is called

Then:
- Large files should be processed without memory issues
- Standards should be stored correctly
- LLM analysis should handle large inputs appropriately
- Performance should be within acceptable bounds

#### 9. Edge Case - Special Characters

Given:
- A valid standard set ID
- A repository containing markdown files with special characters
- Standards in multiple languages or encodings

When:
- The process_standard_set function is called

Then:
- Files should be read correctly regardless of encoding
- Special characters should be preserved in database storage
- LLM analysis should handle special characters appropriately

## Implementation Notes

1. Mock External Dependencies:
   - Use MongoDB test container or in-memory database
   - Mock Git operations for repository tests
   - Mock LLM responses for predictable testing
   - Use temporary directories for file system operations

2. Test Data:
   - Create fixture repositories with known content
   - Prepare classification fixtures
   - Include various markdown file types and structures

3. Assertions:
   - Verify database state after operations
   - Check file system state and cleanup
   - Validate classification assignments
   - Ensure error states are handled correctly

4. Test Environment:
   - Isolated database instance
   - Controlled file system access
   - Mocked external services
   - Appropriate logging configuration 