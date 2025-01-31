# Create Test Analysis Report

- Analyze the user submitted  unit test file for key quality attributes. 
- Categorize each test based on the following criteria and provide actionable feedback.
- Do not change any code:

## Test Naming & Readability

- Is the test name descriptive of its intent?
- Are the test steps clear and self-explanatory?

## Coverage & Redundancy

- Does the test cover core behaviors, edge cases, or both?
- Are there redundant tests with no additional value?

## Duplication & Maintainability

- Does the test contain repeated setup logic that could be centralized?
- Should helper logic be moved to production code?

## Scope & Granularity

- Is the test too broad (acting as an integration test) or too narrow (testing trivial code)?
- Does it stay within expected unit test boundaries?

## Test Data Handling

- Does it rely on hardcoded/magic values instead of meaningful constants?
- Is the test data realistic for its use case?

## Performance & Stability

- Are there unnecessary delays, external dependencies, or flaky conditions?
- Can slow operations be optimized or mocked?

## Isolation & Environment

- Does the test modify global state, filesystem, or shared resources?
- Are setup and teardown processes ensuring test independence?

## Code Smells & Best Practices

- Does the test contain multiple responsibilities or unclear assertions?
- Are errors handled explicitly rather than ignored?

## Framework Consistency

- Are assertions and test decorators consistent with best practices?
- Does it leverage framework features like setup hooks effectively?

## Classification & Recommendations

- Is this a unit test, integration test, or misclassified?
- Suggested actions (e.g., refactor, remove, improve reliability).

Output Format:
For each test in the file, return as markdown:

- **Test Name:** `example_test_function`
- **Classification:** ("✅ Good" / "🛠️ Needs Improvement" / "💀 Redundant")
- **Key Issues Identified:** (Concise bullet points)    
- **Recommended Actions:** (Clear, specific improvement steps)

Output this file in /Reports folder with the filename "{test_file_name}_{date_time}.md"