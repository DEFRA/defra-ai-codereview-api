### **Integration Test Quality Assessment Prompt**

Analyze the user-submitted **integration test** file for key quality attributes. Categorize each test based on the following criteria and provide actionable feedback. **Do not change any code**:

### **Test Naming & Readability**
- Is the test name descriptive of its intent?
- Are the test steps clear, structured, and self-explanatory?

### **Coverage & Redundancy**
- Does the test validate interactions between multiple components or services?
- Are there redundant tests with no additional value?
- Does it test a scenario already covered elsewhere?

### **Duplication & Maintainability**
- Does the test contain repeated setup logic that could be centralized?
- Should helper logic be refactored into reusable functions or fixtures?
- Are mocks/stubs used correctly to avoid excessive duplication?

### **Scope & Appropriateness**
- Does the test properly exercise system interactions rather than isolated functions?
- Is it incorrectly acting as a unit test instead of an integration test?
- Does it validate expected system-wide behaviors?

### **Test Data Handling**
- Does it rely on meaningful, realistic test data?
- Are test datasets too large, inconsistent, or unreliable?
- Does it use factories or setup hooks efficiently?

### **Performance & Stability**
- Are there unnecessary delays, external dependencies, or flaky conditions?
- Can slow operations be optimized, parallelized, or mocked?
- Does the test introduce excessive execution time?

### **Isolation & Environment**
- Does the test manage its environment dependencies (e.g., database, API, filesystem) correctly?
- Are setup and teardown processes ensuring clean execution?
- Does it rely on external services that could make it unreliable?

### **Brittleness & Flakiness**
- Is the test overly dependent on exact timings, external networks, or unpredictable factors?
- Does it fail intermittently due to unreliable dependencies?
- Can its stability be improved with retries, better synchronization, or robust data handling?

### **Code Smells & Best Practices**
- Does the test contain multiple responsibilities or unclear assertions?
- Are failure messages meaningful and helpful?
- Does it ignore errors instead of handling them properly?

### **Framework Consistency**
- Are assertions and test decorators consistent with best practices?
- Does it leverage framework features like setup hooks, fixtures, or dependency injection effectively?

### **Test Relevance & Necessity**
- **Is this test still required?**  
  - Does it provide unique value, or is it redundant?
  - Is it outdated due to changes in system architecture?
  - Should it be merged, refactored, or removed?

### **Classification & Recommendations**
- **Is this a valid integration test, a misclassified unit test, or no longer necessary?**
- Suggested actions (e.g., refactor, remove, improve reliability).

---

### **Output Format:**
For each test in the file, return as markdown:

```markdown
**Test Name:** `example_integration_test`
**Classification:** ("✅ Good" / "🛠️ Needs Improvement" / "💀 Redundant")
**Key Issues Identified:** (Concise bullet points)
**Recommended Actions:** (Clear, specific improvement steps)
**Still Required?** ("✅ Yes" / "❌ No - Remove" / "🔄 Merge/Refactor")
```

### **File Output:**
Save this report in the `/Reports` folder with the filename:  
**`{test_file_name}_{date_time}.md`**
