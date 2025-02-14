# MongoDB Mocking Patterns in Our Codebase

## Overview

This repository contains a comprehensive approach to mocking MongoDB, ensuring that tests run reliably without an actual database connection. The implementation leverages Python's unittest.mock library, combining AsyncMock, MagicMock, and PropertyMock to simulate asynchronous database operations.

## Global Database Patching

- The primary fixture is `mock_database_setup` (e.g., in `tests/conftest.py`). This fixture patches the following:
  - `src.main.init_database` to return a mocked database.
  - `src.database.database_utils.client` is patched using MagicMock.
  - `src.database.database_utils.get_database` is patched to return the fake database.
  - `motor.motor_asyncio.AsyncIOMotorClient` is patched to return a MagicMock.

These patches ensure that any database initialization within the application uses the mock rather than connecting to a live MongoDB.

## Collection Mocks

- **Async Mocks for Collections:**
  - Collections like `classifications`, `code_reviews`, `standard_sets`, and `standards` are instantiated as `AsyncMock` objects.
  - Each collection is attached as an attribute on the mocked database.

- **Database Property Patching:**
  - Using `PropertyMock`, the tests simulate nested attributes. For example:
    ```python
    type(standards_collection).database = PropertyMock(return_value=mock_db)
    ```
  This pattern is used consistently across multiple test files to ensure that the collection mocks are linked to a parent database mock.

## Operation Mocking Patterns

- **Find and Cursor Operations:**
  - The `find` method returns a mocked cursor. The cursor's `to_list` method is also mocked to return a predefined list of documents.
  - A dedicated `setup_list_cursor` fixture is available for list operations:
    ```python
    @pytest.fixture
    def setup_list_cursor(mock_docs=None):
        """Helper fixture to setup cursor for list operations."""
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_docs or [])
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        return mock_cursor
    ```
  - This fixture handles both the data return and sorting operations commonly used in list endpoints.

- **CRUD Operations:**
  - **Insert Operations:** `insert_one` is mocked to return an object with an `inserted_id` (often via a helper fixture named `setup_mock_result`).
  - **Update/Delete Operations:** Operations such as `update_one` and `delete_one` are mocked to return objects containing `modified_count`, `matched_count`, or `deleted_count` respectively.

- **Error Simulation:**
  - Some tests simulate errors by setting side effects on mocks (e.g., using `side_effect=Exception('Database error')`) to validate error handling logic.

## Service and Dependency Injection

- **Service Setup:**
  - Tests often establish a service-repository pattern where the repository wraps the collection mock, and the service is instantiated with both the repository and `mock_database_setup`.
  - Dependency overrides in the FastAPI app are used, such as:
    ```python
    app.dependency_overrides[get_service] = lambda: service
    ```
  This ensures that when endpoints are invoked during tests, they use the mocked services.

## Standardized Test Fixtures

- **Autouse Fixtures for Setup and Teardown:**
  - Fixtures like `setup_and_teardown` are defined with `autouse=True` to automatically manage state for each test, clearing dependency overrides and ensuring test isolation.

- **Custom Result Fixtures:**
  - Helper fixtures such as `setup_mock_result` simplify the creation of mock results for insert, update, and delete operations. This standardizes the format of the return objects across tests.

## Extending the Patterns

To add or extend the mocking behavior:

- **New Collections or Operations:**
  - Follow the same pattern: initialize an `AsyncMock`, patch its `database` property if needed, and define operations like `find_one`, `insert_one`, etc., according to the established patterns.

- **Error Cases:**
  - Utilize the `side_effect` attribute on the asynchronous mocks to simulate error conditions.

- **Integrating with Additional Services:**
  - When a new service depends on MongoDB, create similar repository fixtures and override dependencies in the FastAPI app.

## Environment and Configuration

- **Environment Variables:**
  - The testing environment automatically mocks essential MongoDB configuration:
    ```python
    @pytest.fixture(autouse=True)
    def mock_env_vars(monkeypatch):
        """Mock environment variables."""
        monkeypatch.setenv("MONGODB_URL", "mongodb://test:27017")
        monkeypatch.setenv("DATABASE_NAME", "test_db")
    ```

## Test Data Management

- **Mock Data Setup:**
  - Test data utilities are available in `tests/utils/test_data.py`
  - Helper functions like `create_standard_set_test_data`, `create_classification_test_data`, and `create_standard_test_data` provide consistent test data structures
  - These utilities should be used to maintain consistency across tests

- **Collections with Initial Data:**
  - A specialized fixture `mock_collections_with_data` is available for tests requiring pre-populated collections:
    ```python
    @pytest.fixture
    async def mock_collections_with_data(mock_database_setup, mock_standard_set_data, 
                                       mock_classifications, mock_standards):
        """Setup mock collections with initial data and behaviors."""
        # ... collection setup ...
        standards_collection.insert_one = AsyncMock(
            return_value=AsyncMock(inserted_id=ObjectId()))
        standards_cursor = AsyncMock()
        standards_cursor.to_list = AsyncMock(return_value=mock_standards)
        # ... additional setup ...
        return standard_sets_collection, standards_collection, classifications_collection
    ```
  - This pattern is useful for integration tests that need to verify behavior with existing data

## Common Gotchas and Best Practices

1. **Cursor Chain Mocking:**
   - When mocking cursors that chain methods (e.g., `find().sort().to_list()`), ensure the intermediate methods return the cursor:
     ```python
     mock_cursor.sort = MagicMock(return_value=mock_cursor)
     ```

2. **Database Property Access:**
   - Always mock the database property for collections that need to access their parent database:
     ```python
     type(collection).database = PropertyMock(return_value=mock_db)
     ```

3. **Collection Resolution:**
   - When mocking multiple collections, use a side_effect with a dictionary to properly route collection requests:
     ```python
     mock_db.get_collection = MagicMock(side_effect=lambda name: {
         "standards": standards_collection,
         "classifications": classifications_collection
     }[name])
     ```

## File Types Impacted by MongoDB Mocking

1. **Test Files:**
   - `tests/conftest.py` - Global test configuration and fixtures
   - `tests/integration/api/*_test.py` - API integration tests
   - `tests/agents/*_test.py` - Agent-specific tests
   - `tests/utils/test_data.py` - Test data utilities and factories

2. **Repository Layer:**
   - `src/repositories/*.py` - Database access layer files that need to be mocked in tests
   - These files typically contain direct MongoDB operations that need comprehensive mocking

3. **Service Layer:**
   - `src/services/*.py` - Business logic files that use repositories
   - These files need their repository dependencies mocked

4. **API Layer:**
   - `src/api/v1/*.py` - API endpoint files
   - These files need their service dependencies mocked, which in turn use mocked repositories

5. **Database Configuration:**
   - `src/database/*.py` - Database configuration and initialization files
   - These files are typically patched globally in tests

6. **Agent Files:**
   - `src/agents/*.py` - AI agent files that interact with the database
   - These files often need both database and external service mocks

When adding new functionality that involves MongoDB:
1. Add corresponding test files in the appropriate test directory
2. Update or add test data utilities if needed
3. Ensure repository tests have comprehensive mock coverage
4. Add integration tests for new endpoints or agent functionality

## Conclusion

The repository employs a robust and consistent mocking strategy for MongoDB, leveraging Python's mock capabilities to simulate database interactions. These practices not only improve test reliability but also speed up the testing process by avoiding actual database operations.

✅ 