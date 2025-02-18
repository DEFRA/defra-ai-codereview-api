# Product Requirements Document (PRD)

1. Introduction

This PRD outlines the requirements for extending an existing Python FastAPI and Node.js application. The application currently checks GitHub codebases against defined standards and provides compliance reports. The new functionality introduces a **Tool Plugin Architecture** that allows external tools to be plugged into the backend for additional code checks or operations, returning structured reports to the frontend following GDS (Government Digital Service) design principles.

2. Background

2.1 Existing System

1. **Backend**:
   - Built with **Python FastAPI**.
   - Provides endpoints to analyze code against defined standards.
   - Uses an agentic workflow to generate compliance reports.

2. **Frontend**:
   - Built with **Node.js**.
   - Adheres to **GDS design guidelines**.
   - Submits code review requests and displays compliance results.

2.2 Drivers for New Functionality

- We want to add a plugin system (Tool Plugin Architecture) to easily integrate various tools (e.g., static analysis, style checks, security scanning) into the existing code review workflow.
- Each tool can be enabled or disabled, provide its own configuration, and produce a structured report for display in the frontend.

3. Goals & Scope

3.1. **Extend the backend** with:
   - A new `/tools` folder structure to dynamically load and manage tool plugins.
   - New or updated endpoints to retrieve a list of available tools and to trigger tool executions asynchronously.
   - Data model (MongoDB) updates to store tool configurations and outputs.

3.2. **Update the frontend** with:
   - A new interface on the homepage to display available tools and allow users to select which tools to run.
   - Updates to the code review detail page to display tool reports.

3.3. **Maintain GDS compliance** in both the backend API design and frontend UI/UX.

4. Requirements

4.1. High-Level Functional Requirements

| **ID** | **Requirement** | **Description** |
| --- | --- | --- |
| FR-1 | Tool Plugin Architecture | Implement a plugin system where each tool is placed in a `/tools` directory and loaded dynamically at runtime. |
| FR-2 | Tool Configuration | Each tool has a `tool.yaml` for metadata and configuration, and a `tool.py` to define the tool's execution logic. |
| FR-3 | List of Tools Endpoint | Create a `GET /api/v1/tools` endpoint that lists enabled tools. |
| FR-4 | Call a Tool | A (potential) `POST /api/v1/tools/{tool-name}` endpoint to call a specific tool with parameters (though usage may be primarily within code review endpoints). |
| FR-5 | Code Review Request Extension | Update `POST /api/v1/code-reviews` to optionally accept a `tools` array with user-supplied input parameters. |
| FR-6 | Code Review Response Extension | Update `GET /api/v1/code-reviews/{id}` to return `tools` and `tool_reports` arrays. |
| FR-7 | Frontend - Tools on Homepage | Display the available tools (from `GET /api/v1/tools`) on the homepage, allowing users to select tools to run. |
| FR-8 | Frontend - Tool Reports in Detail View | Display the tool reports on the code review detail page as additional tabs, in line with GDS design guidelines. |

4.2. Detailed Requirements

4.2.1. Folder Structure for Tools

- **Location**: New root-level directory named `/tools`.
- **Tool-specific Directory**: Each tool is placed in its own subfolder inside `/tools`, e.g., `/tools/static-analysis/`.
- **Files**:
  - **`tool.yaml`**: 
    - Contains at least:
      - `name`: String (unique tool name).
      - `enabled`: Boolean (whether the tool is active).
      - `config`: Key-value pairs for tool-specific settings.
  - **`tool.py`**:
    - The entry point for the tool logic.
    - Exports/returns a single `ToolReport` object containing:
      - `tool_name`
      - `report` (markdown string)
      - `issues` (array of issues)
      - `score` (optional number)

Example `tool.yaml`:
```yaml
name: "static-analysis"
enabled: true
config:
  example_setting: "value"
  debug_mode: false
  exclude_dirs:
    - "data/meeting_notes_local"
    - "data/meeting_notes_remote"
```

Example Folder Structure:
```
/     # application root
├── tools/                      # Tools plugin root
│   └── static-analysis/        # A specific tool plugin
│       ├── __init__.py
│       ├── tool.py             # Entry point for calling the tool
│       └── tool.yaml           # Tool definition and configuration
```

4.2.2. Plugin Mechanics

- **Tool Detection**:
  - The system scans all subdirectories under /tools for a tool.yaml file.
  - Only returns tools that have enabled: true.
- **Tool Invocation**:
  - Accepts parameters: tool_name, repository_url, and additional JSON input data.
  - Asynchronously executes the tool.py file.
  - Returns a ToolReport object, which will be stored in the database.

4.2.3. Data Model Updates

Add new schemas to MongoDB:

```typescript
interface ToolReport {
    _id: ObjectId;         // Report identifier
    tool_name: string;     // Name of the tool
    report: string;        // Detailed tool output (in Markdown)
    issues: Issue[];       // List of identified issues
    score?: number;        // Optional tool score
}

interface ToolInfo {
    _id: ObjectId;          // Tool identifier
    name: string;           // Name of the tool
    input_parameters?: string; // JSON object or string containing input parameters
}
```

Extend existing CodeReview schema:

```typescript
interface CodeReview {
    _id: ObjectId;                   // Unique identifier
    repository_url: string;          // Repository URL
    status: ReviewStatus;            // Current review status
    standard_sets: StandardSetInfo[];// Associated standard sets
    compliance_reports: ComplianceReport[]; // Existing compliance reports
    tools: ToolInfo[];               // NEW - Tools array
    tool_reports: ToolReport[];      // NEW - Tool reports array
    created_at: Date;                // Creation timestamp
    updated_at: Date;                // Last update timestamp
    error_message?: string;          // Optional error message
    git_ref?: string;                // Optional Git reference (branch/tag)
}
```

4.2.4. New and Updated API Endpoints

**GET /api/v1/tools**

Purpose: Returns an array of enabled tools.
Response:
```json
[
  {
    "_id": "123abc",
    "name": "static-analysis",
    "input_parameters": {} // optional
  },
  ...
]
```

**POST /api/v1/tools/{tool-name}** (optional)

Purpose: Directly triggers execution of a tool with supplied parameters.
Request Body:
```json
{
  "repository_url": "string",
  "input_parameters": {
    "example_setting": "value"
  }
}
```
Response: ToolReport object.

**POST /api/v1/code-reviews** (UPDATED)

Existing Request Body:
```json
{
  "repository_url": "string",
  "standard_sets": [
    "FfDEBf8f1178E6FcEBEcD43d"
  ]
}
```

Extended to Include Tools:
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

Behavior:
- Save tools data in the CodeReview document.
- Asynchronously invoke each specified tool.
- On completion, store the resulting ToolReport objects in the tool_reports array.

**GET /api/v1/code-reviews/{id}** (UPDATED)

Existing Response:
```json
{
  "_id": "679b6ca0080a49f100b0edae",
  "repository_url": "...",
  "status": "completed",
  "standard_sets": [...],
  "compliance_reports": [...],
  "created_at": "...",
  "updated_at": "..."
}
```

Extended Response:
```json
{
  "_id": "679b6ca0080a49f100b0edae",
  "repository_url": "...",
  "status": "completed",
  "standard_sets": [...],
  "compliance_reports": [...],
  "tools": [
    {
      "_id": "6798f4151cb87d7c7420b554",
      "name": "static-analysis",
      "input_parameters": {
        "testing": 123
      }
    }
  ],
  "tool_reports": [
    {
      "_id": "679b6cfd3355648a5282ddd",
      "tool_name": "static-analysis",
      "report": "# Test reporting output in markdown format",
      "issues": [...],
      "score": 85
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

5. Frontend Updates

5.1. Home Page (/)

- Fetch Tools:
  - Perform a GET /api/v1/tools request.
  - Display a list of enabled tools below the existing standards section.
- Checkboxes for Tools:
  - Each tool in the list should have a checkbox allowing users to select/deselect.
  - When selected, tool parameters may be added if needed (similar to how standards are selected).
- Form Submission:
  - When the user submits:
    - The tools array is included in the request body to POST /api/v1/code-reviews.

5.2. Code Review Detail Page (/code-reviews/{id})

- Fetch Code Review Data:
  - Perform a GET /api/v1/code-reviews/{id} request.
- Parse tool_reports:
  - Display each tool's report as an additional tab or section, following the GDS tab pattern.
  - Tab Label: Convert tool_name to a readable format (replace dashes/underscores with spaces, sentence case).
  - Tab Content: Render the report field as Markdown content, similar to how compliance reports are displayed.

6. Non-Functional Requirements

6.1. Performance:
- Tool loading should happen on server startup or on-demand, with minimal performance overhead.
- Asynchronous tool execution should not block the main thread.

6.2. Security:
- Validate tool parameters to prevent code injection or malicious input.
- Ensure that only enabled tools can be executed.

6.3. Scalability:
- The plugin architecture must support adding multiple new tools without requiring extensive rework.

6.4. Maintainability:
- Clearly defined folder structure and data model changes.
- GDS-compliant UI patterns for consistent and maintainable front-end code.

7. Dependencies & Assumptions

7.1. MongoDB:
- Updated schemas must be applied. Database migrations (if needed) should be considered.

7.2. FastAPI:
- The tool detection and invocation rely on scanning the filesystem for tool.yaml.

7.3. Node.js Frontend:
- The GDS design library and existing UI patterns remain intact. Use existing styling components for new sections/tabs.

7.4. User Permissions (Assumption):
- The current application user model will remain unchanged. All authenticated users can select or run tools unless a future requirement specifies otherwise.

8. Acceptance Criteria

8.1. Tool Plugin Architecture Implemented:
- The /tools directory exists.
- Tools can be added simply by creating a new subfolder with tool.yaml and tool.py.

8.2. Enabled Tools List Endpoint:
- GET /api/v1/tools returns all tools with enabled: true in tool.yaml.

8.3. Tool Invocation:
- Tools are invoked either through POST /api/v1/tools/{tool-name} or automatically via POST /api/v1/code-reviews if included in the request body.
- The system stores resulting ToolReport objects in MongoDB.

8.4. Extended Code Review API:
- POST /api/v1/code-reviews accepts a tools array.
- GET /api/v1/code-reviews/{id} includes tools and tool_reports in the response.

8.5. Updated Frontend:
- Home page displays available tools.
- Code review detail page shows each tool report in a separate tab.

9. Additional Notes

- Ensure all new endpoints follow GDS service design and RESTful best practices.
- Consider providing a sample plugin (static-analysis) for demonstration.
- Proper error handling is crucial: if a tool is not enabled or fails to run, provide user-friendly error messages.