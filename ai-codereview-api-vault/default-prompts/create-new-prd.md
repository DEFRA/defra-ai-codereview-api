
This workflow is designed to assist in creating, iterating, and refining a Product Requirements Document (PRD) for the feature/project titled **[FEATURE NAME]**. The PRD should focus on the specific objectives, requirements, and context for this feature and be saved in the correct location.

You are not creating a PRD for Python Development best practices - this is designed to used for a conversation between the user and Windsurf AI to correctly define a PRD for a feature.


Prompt the user for what [FEATURE NAME] is.

You do not write code when running this workflow with the user - you can only utilise making markdown files int the PRD file directory (`product-requirements/`)

---

## **Workflow Instructions**:


1. **File Location Validation**
	- Save the PRD file in the `product-requirements/` directory.
	- Validate the directory’s existence and accessibility before creating the file.
	- Create a [FEATURE NAME].md file
2. **Content Focus**
	- Draft the PRD specifically for the feature/project at hand.
	- Do not include generic content (e.g., unrelated best practices) unless it directly applies to the feature's implementation or objectives.
3. **PRD Sections**  
    Windsurf AI will initiate the creation of a PRD in Markdown format, structured to include the following sections:
    - **Project Name**: Descriptive title of the feature or project.
    - **Overview**: Objective and context, summarizing the purpose and background of the feature.
    - **Functional Requirements**: A detailed list of the features and responsibilities broken down into actionable items.
    - **User Stories & Acceptance Criteria**: Scenarios described in BDD (Behavior-Driven Development) format, highlighting how the feature should behave from a user perspective.
    - **Technical Requirements**: Specific technical details, including languages, frameworks, inputs, and outputs.
    - **Non-Functional Requirements**: Performance, scalability, error handling, security, and other constraints.
4. **Codebase Analysis**
    - Automatically scans the codebase to identify modules, functions, or dependencies that are likely to be impacted by the new feature.
    - Flags areas of the codebase that may require refactoring or extension.
    - Provides recommendations for integrating the feature while maintaining code quality and consistency.
5. **Interactive User Collaboration**
    - Prompts the user for additional information or clarification when details are missing or ambiguous.
    - Engages the user to define specific user stories and acceptance criteria.
    - Adjusts the PRD dynamically based on user input, ensuring that the document remains accurate and comprehensive.
6. **Implementation Architecture**
    - Drafts a high-level architectural plan for the feature, outlining key components, interactions, and workflows.
    - Identifies reusable components within the existing codebase to minimize redundant implementation efforts.
    - Highlights any new components or patterns required for the feature.
7. **Finalisation**
    - Iterates on the PRD until all key aspects are sufficiently addressed.
    - Suggests wrapping up the PRD when it has reached a state of completeness and clarity.
    - Ensures the final document is well-structured, technically robust, and ready for team review.

---

### **Additional Features for User Guidance**

Windsurf AI will:

- Suggest a **performance benchmark** and error-handling strategies in the **Non-Functional Requirements** section.
- Automatically draft **Acceptance Criteria** in BDD format based on the feature description and user input.
- **Error Handling**: If any errors occur during file creation or writing, provide a clear explanation of the problem and offer actionable next steps.
- Summarise the contents of the PRD and the file location.
- Prompt the user to review the PRD and specify additional details or adjustments if needed.

### **Outcome**

This enhanced workflow ensures the PRD:

- Includes all necessary sections to guide implementation and review.
- Captures detailed user stories and technical requirements, promoting clarity and alignment among stakeholders.
- Is informed by insights from codebase analysis, enabling efficient and informed development planning.

When the PRD is complete, Windsurf AI will recommend finalization and provide options to export or share the document for team review.