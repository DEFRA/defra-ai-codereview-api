# Hybrid Requirements Document for Tool Plugin Architecture Extension

## 1. Introduction

**Purpose:**  
To extend an existing Python FastAPI and Node.js application with a dynamic tool plugin architecture. This will allow external analysis tools (e.g., static analysis, security scanning) to be added, configured, and executed as part of the code review workflow while ensuring compliance with GOV.UK (GDS) design guidelines.

**Scope:**

- **Backend:** Extend FastAPI endpoints, implement dynamic plugin loading from a new `/tools` folder, and update the MongoDB data models.
- **Frontend:** Update the Node.js UI to display available tools and render tool reports in a user-friendly manner.
- **Integration:** Seamlessly incorporate tool execution into the code review process with asynchronous handling and error management.

**Context & Drivers:**  
The current system performs code compliance checks against defined standards. Adding a plugin system provides flexibility for additional types of analyses and enhances the code review process with richer, structured reporting.

---

## 2. Background

- **Existing System:**
    - **Backend:** Python FastAPI application handling code analysis and compliance report generation.
    - **Frontend:** Node.js application following GDS guidelines for code review requests and report display.
- **Need for Extension:**  
    To enable external tools to be integrated easily, allowing for more comprehensive code analysis while preserving the user experience and system performance.

---

## 3. Goals & High-Level Features

- **Plugin Architecture:**  
    A standardized folder structure (`/tools`) where each tool is self-contained with its configuration (`tool.yaml`) and logic (`tool.py`).
    
- **API Enhancements:**  
    New endpoints to list available tools, trigger individual tools, and integrate tool execution into code review submissions.
    
- **Data Model Updates:**  
    Extend the CodeReview schema to include tool-related metadata and reports.
    
- **Frontend Enhancements:**  
    Update the homepage to display selectable tools and the code review detail page to render tool reports as separate tabs.
    

---

## 4. Detailed Requirements by Feature

Each feature is defined first as a user story (with discrete, testable acceptance criteria) followed by the technical requirements needed for implementation.

---

### 4.1. Feature: Tool Plugin Architecture

#### A. User Story

**User Story:**  
_AS A backend developer,  
I WANT a standardized plugin architecture with a consistent folder structure and configuration files,  
SO THAT I can easily add and manage new analysis tools._

**Acceptance Criteria:**

1. **Folder Structure Creation:**
    
    - **Given:** The application root directory,
    - **When:** A developer adds a new tool plugin,
    - **Then:** A new subdirectory is created under `/tools` that contains at least `tool.yaml` and `tool.py`.
2. **Configuration Parsing:**
    
    - **Given:** A valid `tool.yaml` exists in a plugin directory,
    - **When:** The backend scans the `/tools` folder,
    - **Then:** It correctly loads the tool’s name, enabled flag, and configuration parameters.

#### B. Technical Requirements

- **Directory Structure:**
    
    - Create a new root-level folder named `/tools`.
    - Each tool plugin resides in its own subfolder (e.g., `/tools/static-analysis/`).
- **Required Files per Plugin:**
    
    - **`tool.yaml`:** Contains fields such as:
        - `name`: Unique tool identifier (string)
        - `enabled`: Boolean flag indicating if the tool is active
        - `config`: A set of key-value pairs for tool-specific settings
    - **`tool.py`:** The entry point for the tool's logic, returning a `ToolReport` object containing:
        - `tool_name`
        - `report` (a markdown string)
        - `issues` (an array of issues)
        - `score` (optional numeric score)
- **Example `tool.yaml`:**
    
    ```yaml
    name: "static-analysis"
    enabled: true
    config:
      debug_mode: false
      exclude_dirs:
        - "data/meeting_notes_local"
        - "data/meeting_notes_remote"
    ```
    
- **Dynamic Loading:**  
    The system scans the `/tools` directory at startup (or on-demand) and loads only those plugins where `enabled: true`.
    
- **Testing Considerations:**  
    Automated tests should verify that:
    
    - The folder structure is present and correctly formatted.
    - Only plugins with `enabled: true` are loaded.
    - The configuration values are parsed accurately.

---

### 4.2. Feature: API Endpoint for Tools List

#### A. User Story

**User Story:**  
_AS A frontend developer,  
I WANT to retrieve a list of enabled tools via an API endpoint,  
SO THAT I can display them on the homepage for user selection._

**Acceptance Criteria:**

1. **Retrieve Enabled Tools:**
    
    - **Given:** Multiple tool plugins with varying enabled statuses exist in `/tools`,
    - **When:** A GET request is made to `/api/v1/tools`,
    - **Then:** The response returns only those tools where `enabled: true`.
2. **Response Format:**
    
    - **Given:** The enabled tools,
    - **When:** The GET request is processed,
    - **Then:** The API returns a JSON array of ToolInfo objects with fields such as `_id`, `name`, and optional `input_parameters`.

#### B. Technical Requirements

- **Endpoint Implementation:**
    
    - **Method:** GET
    - **Path:** `/api/v1/tools`
    - **Operation:**
        - Scan the `/tools` directory.
        - Parse each plugin’s `tool.yaml`.
        - Filter out any tools that are not enabled.
        - Return the resulting list in JSON format.
- **Sample Response:**
    
    ```json
    [
      {
        "_id": "uniqueObjectId1",
        "name": "static-analysis",
        "input_parameters": {}
      }
    ]
    ```
    
- **Testing Considerations:**  
    Write tests to ensure:
    
    - Disabled tools (with `enabled: false`) do not appear.
    - The JSON response format meets the specifications.

---

### 4.3. Feature: Tool Trigger API Endpoint

#### A. User Story

**User Story:**  
_AS A backend developer,  
I WANT to trigger a specific tool via a dedicated API endpoint,  
SO THAT I can run tool analysis independently from the code review process when required._

**Acceptance Criteria:**

1. **Successful Tool Invocation:**
    
    - **Given:** A valid tool name and repository URL are provided in the request,
    - **When:** A POST request is made to `/api/v1/tools/{tool-name}`,
    - **Then:** The backend should asynchronously invoke the corresponding tool’s `tool.py` and return a success message.
2. **Disabled Tool Handling:**
    
    - **Given:** The requested tool is marked as disabled in its `tool.yaml`,
    - **When:** A POST request is made,
    - **Then:** The API returns an error message indicating that the tool is not enabled.

#### B. Technical Requirements

- **Endpoint Implementation:**
    
    - **Method:** POST
    - **Path:** `/api/v1/tools/{tool-name}`
    - **Input:** JSON payload containing at least:
        - `repository_url`: URL of the repository to analyze
        - `input_parameters`: Optional object with tool-specific parameters
- **Behavior:**
    
    - Validate that the tool is enabled by reading its `tool.yaml`.
    - Asynchronously invoke the tool’s logic in `tool.py`.
    - Return a JSON response indicating the tool’s execution status.
    - If the tool is disabled, return an error response.
- **Sample Success Response:**
    
    ```json
    {
      "message": "Tool execution started",
      "tool_name": "static-analysis",
      "status": "processing"
    }
    ```
    
- **Testing Considerations:**  
    Simulate both successful tool execution and error scenarios when a disabled tool is invoked.
    

---

### 4.4. Feature: Code Review Integration

#### A. User Story

**User Story:**  
_AS A user,  
I WANT to include tools in my code review submission,  
SO THAT the system can run both standard compliance checks and additional tool analyses on my repository._

**Acceptance Criteria:**

1. **Including Tools in Submission:**
    
    - **Given:** A code review form on the homepage,
    - **When:** A user selects one or more tools (via checkboxes),
    - **Then:** The POST payload to `/api/v1/code-reviews` includes a `tools` array with each tool’s name and any input parameters.
2. **Asynchronous Tool Processing:**
    
    - **Given:** The code review submission contains tool data,
    - **When:** The submission is processed,
    - **Then:** The system saves the tool information in the CodeReview document and asynchronously triggers each tool’s execution.

#### B. Technical Requirements

- **Endpoint Update:**
    
    - Extend the POST `/api/v1/code-reviews` endpoint to accept an additional field `tools` in the JSON payload.
- **Data Model Updates:**
    
    - Update the CodeReview document schema to include:
        - `tools`: An array of ToolInfo objects.
        - `tool_reports`: An array of ToolReport objects.
- **Sample Request Payload:**
    
    ```json
    {
      "repository_url": "string",
      "standard_sets": ["FfDEBf8f1178E6FcEBEcD43d"],
      "tools": [
        {
          "name": "static-analysis", 
          "input_parameters": {
            "param1": true, 
            "another": "testing 123"
          }
        },
        {
          "name": "guideline-tool",
          "input_parameters": {
            "someparam": "test", 
            "anotherParam": "testing 123"
          }
        }
      ]
    }
    ```
    
- **Testing Considerations:**  
    Ensure that:
    
    - The tool information is correctly saved with the code review.
    - Tool execution is triggered asynchronously.
    - The CodeReview document includes both `tools` and `tool_reports` after execution.

---

### 4.5. Feature: Tool Report Tab Display

#### A. User Story

**User Story:**  
_AS A user,  
I WANT to view tool reports as separate tabs on the code review detail page,  
SO THAT I can easily navigate between standard compliance reports and additional tool outputs._

**Acceptance Criteria:**

1. **Code Review Detail Response Contains Tool Data:**
    
    - **Given:** A code review that includes tool execution,
    - **When:** A GET request is made to `/api/v1/code-reviews/{id}`,
    - **Then:** The response includes both `tools` and `tool_reports` arrays.
2. **Display of Tool Reports:**
    
    - **Given:** Tool report data is available,
    - **When:** The code review detail page is rendered,
    - **Then:** Each tool report appears in a separate tab, with the tab label formatted (e.g., converting "static-analysis" to "Static Analysis") and the content displayed in Markdown.

#### B. Technical Requirements

- **Endpoint Update:**
    
    - Update GET `/api/v1/code-reviews/{id}` to include:
        - `tools`: Array of ToolInfo objects.
        - `tool_reports`: Array of ToolReport objects.
- **Frontend Changes:**
    
    - Modify the code review detail page to create separate tabs for each tool report using GOV.UK tab components.
    - Convert tool names from their raw format to sentence case for the tab labels.
- **Testing Considerations:**  
    Verify that:
    
    - The JSON response includes the new fields.
    - The frontend correctly renders tabs with appropriate labels and Markdown content.

---

### 4.6. Feature: Homepage Tool Selection

#### A. User Story

**User Story:**  
_AS A user,  
I WANT to see a list of available tools on the homepage,  
SO THAT I can select which tools to run as part of my code review._

**Acceptance Criteria:**

1. **Display Tools List:**
    
    - **Given:** The GET `/api/v1/tools` endpoint returns enabled tools,
    - **When:** The homepage loads,
    - **Then:** A "Tools" section is rendered with a checkbox for each available tool.
2. **Inclusion in Form Submission:**
    
    - **Given:** A user checks one or more tool checkboxes,
    - **When:** The form is submitted,
    - **Then:** The POST payload to `/api/v1/code-reviews` includes a `tools` array with the selected tools and any specified input parameters.

#### B. Technical Requirements

- **Frontend Update:**
    
    - Modify the homepage logic (e.g., in `/src/server/home/index.js`) to perform an asynchronous GET request to `/api/v1/tools` when the page loads.
    - Render a new section titled "Tools" using GOV.UK design components (e.g., checkboxes).
    - Ensure that the tool selections are correctly serialized into the form submission.
- **Testing Considerations:**  
    Validate that:
    
    - Tools are fetched and displayed correctly.
    - Selected tool data is included in the form payload sent to the backend.

---

## 5. Integration & End-to-End Testing

**Integration Testing:**

- Validate that the entire workflow—from tool selection on the homepage, through code review submission, asynchronous tool execution, and finally, tool report display on the detail page—functions as expected.
- Confirm that data flows correctly between frontend and backend and that MongoDB stores the extended CodeReview document appropriately.

**End-to-End Test Scenarios:**

- A user selects one or more tools, submits a code review, and the system processes both compliance checks and tool executions.
- Verify error handling when attempting to trigger a disabled tool.
- Ensure that UI components correctly render tool report tabs with the expected content.

---

## 6. Non-Functional Requirements

- **Performance:**  
    Tool scanning and asynchronous execution must not degrade overall system performance.
    
- **Security:**  
    Validate all tool parameters to prevent code injection or other attacks. Only execute tools that are enabled in their configuration.
    
- **Scalability:**  
    The plugin architecture must support the easy addition of new tools without significant changes to the codebase.
    
- **Maintainability:**  
    Follow a clear folder structure, standard coding practices, and GDS UI guidelines for both backend and frontend changes.
    
- **Documentation:**  
    Ensure thorough documentation of new endpoints, data model changes, and integration flows.
    

---

## 7. Data Model Updates

**ToolReport Object:**

```typescript
interface ToolReport {
    _id: ObjectId;         // Report identifier
    tool_name: string;     // Name of the tool
    report: string;        // Detailed tool output in Markdown
    issues: Issue[];       // List of identified issues
    score?: number;        // Optional numeric score
}
```

**ToolInfo Object:**

```typescript
interface ToolInfo {
    _id: ObjectId;         // Tool identifier
    name: string;          // Name of the tool
    input_parameters?: string; // JSON object or string with tool input parameters
}
```

**Updated CodeReview Document:**

```typescript
interface CodeReview {
    _id: ObjectId;
    repository_url: string;
    status: ReviewStatus;
    standard_sets: StandardSetInfo[];
    compliance_reports: ComplianceReport[];
    tools: ToolInfo[];          // Newly added field
    tool_reports: ToolReport[]; // Newly added field
    created_at: Date;
    updated_at: Date;
    error_message?: string;
    git_ref?: string;
}
```

---

## 8. Sample File Structure

```
/ (application root)
├── tools/                      # Root directory for tool plugins
│   └── static-analysis/        # Example tool plugin
│       ├── __init__.py
│       ├── tool.py             # Execution logic for the tool
│       └── tool.yaml           # Configuration and metadata for the tool
├── src/
│   └── server/                 # Frontend server code (e.g., homepage and detail page)
└── ...                         # Other application directories and files
```

---

## 9. Summary and Next Steps

- **Review:**  
    Ensure that each feature’s user story and technical requirements have been reviewed and agreed upon by both development and QA teams.
    
- **Development Plan:**  
    Create a roadmap for incremental development, ensuring that each feature is implemented and tested individually before full integration.
    
- **Validation:**  
    Use the defined acceptance criteria and automated tests to validate the implementation at both the unit and integration levels.
    
- **Documentation:**  
    Update system documentation and architecture diagrams to reflect the new plugin architecture and endpoint modifications.
    
