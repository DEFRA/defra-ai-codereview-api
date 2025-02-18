# Unified One-Step Prompt

**You are an interactive assistant tasked with analyzing and implementing an integration test plan for the submitted feature.**  

Explain your chain of reasoning at all times

1. **Analyze and Strategize the Integration Test Plan**  
   - **Identify**:  
     - The main entry point to the agent, along with its inputs and outputs.  
     - External dependencies.  
     - Happy path functionality.  
     - Non-happy path functionality.  
   - **Key Considerations**:  
     - Test behavior, not implementation.  
     - Prefer **integration tests** over isolated unit tests—test multiple units together in a functional way.  
     - **Mock external dependencies** only at the lowest level (e.g., database operations, API calls, etc.).  
     - Prioritize clarity and readability.  
     - Follow the **Given-When-Then** pattern with inline comments.  
   - Provide an **explanation of the functionality** and an **approach to integration testing** by:  
     - Defining each integration test using **pseudo-logic** in BDD style.  
     - Avoid writing actual code; use logic statements with enough detail to be easily implemented later.  
   - Create this report as a **single, downloadable Markdown file** in `/tests/specs`.

2. **Read and Assess the Plan**  
   - Thoroughly review the newly created `/tests/specs` file to confirm whether the plan is **sensible and feasible** given the existing codebase.  
   - Provide a **brief explanation** of your assessment (e.g., whether it fits well or if you foresee potential conflicts).  

3. **Focus on the Highlighted Section**  
   - You will now **implement the highlighted section** of the integration test plan.  
   - **Expand or refine** this highlighted section with a **step-by-step instruction set**—a checklist detailing each **required task** for successful implementation.  
   - Format these tasks in Markdown with checkboxes so they can be marked completed once finished (e.g., `- [ ] Task 1`).

4. **Create a Markdown Tracker**  
   - **Place this checklist** into a **Markdown file** in the `/progress` directory.  
   - Clearly label each step or subtask (e.g., "Step 1", "Step 2", etc.) so progress is easy to track.

5. **Prompt for Feedback**  
   - After drafting the **expanded plan** and checklist, **prompt me for feedback** before making any further changes.  
   - Incorporate any feedback received into your plan and checklist as needed.  

6. **Implementation & Testing**  
   - **Implement** the plan step by step, **modifying only the test files**—do not alter source code.  
   - **Run the tests after each change** to ensure the new or updated tests pass.  
   - If a test fails:  
     - Investigate the cause.  
     - Formulate a plan of action to fix or refine the test approach.  
     - Make the necessary adjustments and re-run.  

7. **Progress Updates & Completion Marks**  
   - After each **successful test run** (i.e., tests pass for a given step), **update** the Markdown tracker:  
     - Mark the completed step with a checkmark (`- [x] Completed`).  
     - Add any relevant context, changes, or **discoveries**.  
   - Continue until **all tasks** are checked off and the tests pass successfully.

8. **Behavior**  
   - **Explain your chain of reasoning** for each step or test you create.  
   - Clearly document the **expected behavior** of the integration tests, including both **successful outcomes** and **error conditions**.  
   - Ensure that every test **verifies** proper resource cleanup, accurate error messages, and correct logging.  
   - Note and investigate **any deviations** from expected results.

---

### Output Requirements
- Produce **one overarching output** that includes:  
  1. The **integration test plan** (placed in `/tests/specs`).  
  2. The **ongoing step-by-step progress tracker** (placed in `/progress`).  
  3. Continuous updates within the same output document whenever new progress is made, clarifications are discovered, or tasks are completed.  

### Goal
Achieve fully tested and documented integration coverage, ensuring a clear, auditable history of each test and adjustment along the way.
