# Testing Standards

## Tools and Framework
- pytest as the primary testing framework
- pytest-cov for coverage reporting
- pytest-asyncio for async tests

## Focus
- Test functionality, not implementation
- Integration tests over unit tests
- Test multiple units together in a functional way
- For API's call the REST endpoints and mock external dependencies, testing multiple modules / units together
- For agents call the initiating process and mock external dependencies, testing multiple modules / units together
- The goal is to have functional tests that enable the code to be refactored without the tests breaking i.e. avoiding brittle tests

## Style
- Tests should document the functionality of the application
- Tests should be clear, easy to read and reason about
- Tests should be written from the perspective of the user of the application
- Use "Given-When-Then" pattern to structure test cases:
  ```python
  """
  Given: [preconditions/setup]
  When: [action being tested]
  Then: [expected outcomes]
  """
  ```
- Test names should follow pattern: test_[what]_[scenario]_[expected]

## Test Directory Structure
```bash 
tests/
├── conftest.py  # Fixtures and configuration
├── integration/ # Integration tests
├── unit/        # Unit tests   
├── utils/       # Utility functions
```

## Mocking
- Mock all external dependencies, including:
  - MongoDB (the tests must run without the database running)
  - Anthropic API calls
  - Git Operations
- Mock configuration
- Do not mock internal modules, classes or functions - test multiple modules / units together

## Coverage Requirements
- Minimum 80% code coverage
- Must cover:
  - Happy path scenarios
  - Known error conditions