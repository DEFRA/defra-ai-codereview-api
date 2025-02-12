# Unified One-Step Prompt

1. **Read and Assess the Plan**  
   - Read the submitted integration test plan file thoroughly to understand the overall integration test plan.  
   - Compare the plan's strategy against the existing codebase to confirm whether the plan is sensible and feasible.  
     - Provide a brief explanation of your assessment (e.g., whether it fits well with the current codebase or if you foresee issues).

2. **Focus on the highlighted section of the integration test plan**  
   - You are implementing the highlighted section of the integration test plan.  
   - Expand or refine this section with a **step-by-step instruction set**—a checklist that details each task required for successful implementation.  
     - Format these tasks in Markdown (e.g., `- [ ] Task 1`, `- [ ] Task 2`) so they can be checked off (`- [x]`) once each step is **completed** and **tests pass**.

3. **Create a Markdown Tracker**  
   - Place this checklist into a Markdown file in the `/progress` directory.
   - Clearly label each step or subtask so it's easy to track progress (e.g., "Step 1", "Step 2", etc.).  

4. **Prompt for Feedback**  
   - Once you have drafted the expanded plan and checklist, **prompt me for feedback** before making any changes.  
   - Incorporate any feedback received into your plan as needed.  

5. **Implementation & Testing**  
   - **Implement the plan step by step**, only modifying test files—**do not alter the source code**.  
   - **Run the tests after each change** to ensure the new or updated tests pass.  
   - If a test fails:  
     - Investigate the cause step by step,  
     - Formulate a plan of action to fix the test or refine your testing approach,  
     - Make the necessary adjustments to the tests.  

6. **Progress Updates & Completion Marks**  
   - After each successful test run (i.e., when tests pass for a given step), **update** the Markdown file:  
     - Mark the completed step with a check (`- [x] Completed`)  
     - Add any relevant context updates or notes on what changed or was discovered during that step.  
   - Continue until all tasks in the highlighted section of the integration test plan are checked off and the tests pass successfully.

7. **Behavior**
   - Explain Your Chain of Reasoning before writing the tests or making changes.
   Clearly document the expected behavior of the integration tests, including both successful outcomes and error conditions.
   - Ensure that every test verifies proper resource cleanup, accurate error messages, and correct logging.
   - Any deviations from expected results should be noted and investigated.

