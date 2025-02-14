AGENT FUNCTIONAL TESTING PROMPT 

────────────────────────────
Pre-requisites
- You are given a feature/agent description 
- You given a [file path] to the feature/agent in the codebase.

If you are not, prompt the user for the missing information.

────────────────────────────
Goal
Create integration tests for [feature/agent name] located at [file path].

────────────────────────────
Context  
• Feature/Agent Location: [file path]  
• Description: This agent is responsible for processing inputs (e.g., codebase files, configuration parameters, standards data) and producing a final output (e.g., a compliance report or result message).  
• Related Services/Dependencies: [list any supporting services, external APIs, or databases]  

────────────────────────────
Initial Feature Description & Dependency Confirmation  
1. As a first step, describe the feature/agent in detail and determine all related services and dependencies.  
2. Present this description and dependency list to the user for acknowledgment before proceeding with test implementation.  
   - Example: "This feature [feature/agent name] processes inputs from [source] and interacts with [external API, database, etc.]. Please confirm that this understanding is correct."  

────────────────────────────
Analysis Requirements  
1. Review the testing standards defined in .cursor/rules/02_testing.mdc.  
2. Study existing integration tests for patterns and conventions.  
3. Analyze the agent by identifying:  
  - Entry points or public functions (e.g., the main processing function).  
  - The expected input types and data structures.  
  - The output format and success conditions.  
  - Integration points where external dependencies require mocking.  
  - Error handling scenarios that trigger exceptions or alternate flows.
4. Output the detailed analysis in a markdown file in /reports/{a-useful-name}.md

────────────────────────────
Implementation Guidelines  
1. Test Structure:  
  – Use the Given-When-Then pattern with clear comments.  
  – Focus on end-to-end workflows rather than internal implementation details.  
  – Simulate realistic input scenarios and validate complete end results (e.g., generated reports or returned messages).  
  – Mock external dependencies (database calls, external API invocations) to isolate agent behavior.

2. Test Coverage:  
  – Happy Path: Verify that valid inputs produce correctly formatted outputs.  
  – Edge Cases: Evaluate behavior with boundary or unexpected input data.  
  – Error Conditions: Confirm that failures in dependencies or invalid input result in appropriate exceptions or error responses.

3. Quality Standards:  
  – Write descriptive test names and comments.  
  – Use meaningful assertions to validate outputs.  
  – Ensure efficient setup and teardown using existing test utilities (e.g., @conftest.py, test data fixtures).  
  – Follow project conventions regarding test data management (e.g., using @test_data.py) and avoid hardcoding test data directly in the tests.

────────────────────────────
Constraints  
• Scope: Modify only the test files and supporting test utilities.  
• Format: Provide complete, production-ready test code adhering to project patterns.  
• Dependencies: Leverage existing test helpers and mocks for external dependencies.

────────────────────────────
Output  
Provide the complete test implementation in a single code block, ensuring it can be integrated into the project without modifications.

────────────────────────────

Prompt the user for the missing information if you need it.
Prompt the user for feedback before writing code.
