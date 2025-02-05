# Backend Tools Plugin Architecture User Stories

## User Story 1: Tools Plugin Architecture

### User Story Summary
**AS A** backend developer,  
**I WANT** a lightweight tools plugin architecture with a standardized folder structure and configuration files,  
**SO THAT** I can easily add, manage, and execute various analysis tools within the application.

### Interface Design
- Not applicable; this is a backend-only change.

### Acceptance Criteria

#### Scenario 1: Folder Structure Creation
- **Given** the application root,  
- **When** a developer adds a new tool plugin,  
- **Then** a new directory should be created under `/tools` containing at least `tool.yaml` and `tool.py`.

#### Scenario 2: Tool Configuration Parsing
- **Given** a valid `tool.yaml` file exists in a plugin directory,  
- **When** the backend scans the `/tools` folder,  
- **Then** it should load the tool's name, enabled flag, and configuration parameters correctly.

### Technical Design
- Create a `/tools` directory in the API backend root.  
- Each tool plugin resides in its own subdirectory (e.g., `/tools/static-analysis/`) and must include:  
  - `tool.yaml`: with fields such as `name`, `enabled`, and `config`.  
  - `tool.py`: the runtime entry point that returns a `ToolReport` object with a markdown-formatted `report` string.  
- Example `tool.yaml`:  
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
- Implement dynamic scanning of the /tools directory to detect valid plugins.

## User Story 2: API Endpoint for Tools List

### User Story Summary
**AS A** frontend developer,  
**I WANT** to retrieve a list of enabled tools via an API endpoint,  
**SO THAT** I can display them on the frontend for user selection.

### Interface Design
The frontend will render the list of available tools using GOV.UK design components (e.g., checkboxes in a form).

### Acceptance Criteria

#### Scenario 1: Retrieve Enabled Tools
- **Given** several tool plugins in /tools with enabled: true in their tool.yaml,
- **When** a GET request is made to /api/v1/tools,
- **Then** the API returns an array of ToolInfo objects representing only the enabled tools.

#### Scenario 2: Exclude Disabled Tools
- **Given** a tool plugin has enabled: false in its configuration,
- **When** the GET request is made,
- **Then** the disabled tool should not appear in the returned list.

### Technical Design
- Implement a GET endpoint at /api/v1/tools in the FastAPI backend.
- The endpoint will:
  - Scan the /tools directory and read each tool.yaml file.
  - Filter out plugins where enabled is set to false.
  - Return an array of ToolInfo objects (e.g., including _id, name, and optional input_parameters).
- Sample API response:
  ```json
  [
    {
      "_id": "uniqueObjectId1",
      "name": "static-analysis",
      "input_parameters": "Optional parameter info if available"
    }
  ]
  ```

## User Story 3: Tool Trigger API Endpoint

### User Story Summary
**AS A** backend developer,  
**I WANT** to trigger a specific tool via a dedicated API endpoint,  
**SO THAT** I can run tool analysis independently from the code review process when required.

### Interface Design
Not applicable; this is primarily a backend functionality.

### Acceptance Criteria

#### Scenario 1: Successful Tool Invocation
- **Given** a valid tool name and repository URL provided in the request,
- **When** a POST request is made to /api/v1/tools/{tool-name} with necessary JSON input,
- **Then** the backend should asynchronously call the corresponding tool.py entry point and respond with a success message indicating the tool has been triggered.

#### Scenario 2: Disabled Tool Handling
- **Given** the requested tool is marked as disabled in its tool.yaml,
- **When** the POST request is made,
- **Then** the API should return an error indicating that the tool is not enabled.

### Technical Design
- Implement a POST endpoint at /api/v1/tools/{tool-name}.
- The endpoint will accept:
  - URL parameter: tool-name.
  - JSON body including at least a repository_url and optional input parameters.
- Validate the tool's enabled status via its tool.yaml configuration.
- Use asynchronous calling (similar to the code review process) to invoke the tool's tool.py script.
- Sample API response on success:
  ```json
  {
    "message": "Tool execution started",
    "tool_name": "static-analysis",
    "status": "processing"
  }
  ```
- Return an appropriate error response if the tool is disabled.

## User Story 4: Code Review Tool Integration

### User Story Summary
**AS A** user,  
**I WANT** to include tools in my code review submission,  
**SO THAT** the system can run both standard compliance checks and additional tool analyses on my repository.

### Interface Design
Update the code review submission form (on the homepage) to include a "Tools" section with checkboxes, following GOV.UK design guidelines.

### Acceptance Criteria

#### Scenario 1: Including Tools in Submission
- **Given** the user fills out the code review form,
- **When** the user selects one or more tools via checkboxes,
- **Then** the POST payload to /api/v1/code-reviews must include a "tools" array with each tool's name and any specified input parameters.

#### Scenario 2: Asynchronous Tool Processing
- **Given** tool information is part of the submission,
- **When** the POST request is processed,
- **Then** the system saves the tool data in the CodeReview document and asynchronously triggers each tool's execution.

### Technical Design
- Extend the POST /api/v1/code-reviews endpoint to accept an additional "tools" array in the request body.
- Update the request body schema to match the following example:
  ```json
  {
    "repository_url": "string",
    "standard_sets": ["FfDEBf8f1178E6FcEBEcD43d"],
    "tools": [
      { "name": "static-analysis", "input_parameters": {"param1": true, "another": "testing 123"} },
      { "name": "guideline-tool", "input_parameters": {"someparam": "test", "anotherParam": "testing 123"} }
    ]
  }
  ```
- Modify the CodeReview MongoDB schema to include:
  - tools: an array of ToolInfo objects.
  - tool_reports: an array of ToolReport objects.
- Ensure asynchronous processing of tools similar to existing standard set processing.

## User Story 5: Code Review Tool Reports

### User Story Summary
**AS A** user,  
**I WANT** to view tool information and tool reports in my code review details,  
**SO THAT** I can see the output from the additional analysis tools alongside standard compliance reports.

### Interface Design
- Update the code review detail page to include new tabs for tool reports.
- Tab labels must use GOV.UK styling and convert tool names (e.g., "static-analysis") to a human-readable sentence case format (e.g., "Static analysis").

### Acceptance Criteria

#### Scenario 1: Code Review Detail Response Contains Tool Data
- **Given** a code review that includes tools,
- **When** a GET request is made to /api/v1/code-reviews/{id},
- **Then** the response includes both a "tools" array and a "tool_reports" array with the corresponding data.

#### Scenario 2: Displaying Tool Reports as Tabs
- **Given** the response contains tool reports,
- **When** the detail page renders,
- **Then** each tool report appears in a separate tab labeled with the tool name (formatted in sentence case) and displays the markdown content from the report field when selected.

### Technical Design
- Update the GET /api/v1/code-reviews/{id} endpoint to extend the response with:
  - "tools": [...] — an array of ToolInfo objects.
  - "tool_reports": [...] — an array of ToolReport objects.
- Sample extended response:
  ```json
  {
    "_id": "679b6ca0080a49f100b0edae",
    "repository_url": "https://github.com/DEFRA/find-ffa-data-ingester",
    "status": "completed",
    "standard_sets": [
      { "_id": "6798f4151cb87d7c7420b554", "name": "Test Standards" }
    ],
    "tools": [
      { "_id": "6798f4151cb87d7c7420b554", "name": "static-analysis", "input_parameters": {"testing": 123} }
    ],
    "tool_reports": [
      { "_id": "679b6cfd3355648a5282ddd", "tool_name": "static-analysis", "report": "# Test reporting output in markdown format" }
    ],
    "created_at": "2025-01-30T12:12:16.507000",
    "updated_at": "2025-01-30T12:13:49.701000"
  }
  ```
- Ensure backward compatibility for code reviews that do not include tool data.

## User Story 6: Homepage Tool Selection

### User Story Summary
**AS A** user,  
**I WANT** to see a list of available tools on the homepage,  
**SO THAT** I can select which tools to run as part of my code review.

### Interface Design
- Update the homepage (/src/server/home/index.js) to include a new "Tools" section below the standards checkboxes.
- Use GOV.UK design standards for form controls and checkboxes.

### Acceptance Criteria

#### Scenario 1: Display Tools List
- **Given** that the GET /api/v1/tools endpoint returns a list of enabled tools,
- **When** the homepage loads,
- **Then** a "Tools" section is rendered with a checkbox for each available tool.

#### Scenario 2: Inclusion in Form Submission
- **Given** a user checks one or more tool checkboxes,
- **When** the form is submitted,
- **Then** the POST payload to /api/v1/code-reviews includes a "tools" array with the selected tools and any input parameters.

### Technical Design
- Modify /src/server/home/index.js to perform an asynchronous GET request to /api/v1/tools on page load.
- Render the "Tools" section with checkboxes using GOV.UK form components.
- Ensure the form serialization includes the "tools" array formatted as per the API's requirements.

## User Story 7: Tool Report Tab Display

### User Story Summary
**AS A** user,  
**I WANT** to view tool reports as separate tabs on the code review detail page,  
**SO THAT** I can easily navigate between standard compliance reports and the outputs of the additional tools.

### Interface Design
- Update the code review detail page to include additional tabs for each tool report.
- Tab labels should use GOV.UK tab components and format the tool_name by replacing dashes/underscores with spaces and converting to sentence case.

### Acceptance Criteria

#### Scenario 1: Render Tool Report Tabs
- **Given** that the GET /api/v1/code-reviews/{id} response includes a "tool_reports" array,
- **When** the detail page is rendered,
- **Then** separate tabs are created for each tool report with appropriate labels.

#### Scenario 2: Display Correct Content
- **Given** a tool report for "static-analysis",
- **When** the corresponding tab is selected,
- **Then** the content area displays the markdown formatted report from the report field.

### Technical Design
- Extend the detail page rendering logic to parse the "tool_reports" array from the API response.
- For each tool report, generate a new tab using GOV.UK tab components.
- Format the tab label by converting the tool_name (e.g., "static-analysis") to sentence case (e.g., "Static analysis").
- Ensure the content of each tab displays the markdown from the report field.