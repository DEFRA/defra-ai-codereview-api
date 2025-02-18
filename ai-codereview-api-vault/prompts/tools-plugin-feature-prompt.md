# Background

We have an existing Python FastAPI server that checks github codebases against a set of standards, then reports on how compliant the code base is to the standards using an agentic workflow.

We also have a node.js frontend that follows GDS design guidelines that calls the backend to submit new code checking requests and report the results.

We now want to add a new feature to the application that adds the concept of a lightweight tools plugin architecture to the backend that allows us to call specific tools and report back the output to the frontend.

# New Functionality - Tool Plugin Architecture

We want to create a new plugin architecture that allows for tools to be loaded and called on the backend when triggered via the API.

## New folder structure

The plugin architecture should add a new folder to the root of the API backend called `/tools` .  All the tools for the plugin architecture will be found in this folder.

Within the `/tools` directory, will be more directories, one for each new tool we want to add as a plugin.  For example, if we were to add a static analysis tool as a plugin, we would create a new folder in the tools directory, such as `/tools/static-analysis`, then the plugin management functions would detect the new tool for use in the API.

### Tool plugin configuration

Within each tool plugin directory, there will be, at minimum, two files:
- `tool.yaml` which will define the tool's definition and configuration variables
- `tool.py` which will be the entry point to call the tool at runtime.   The `tool.py` will return a single `ToolReport` object, as outlined below. Note that the ToolReport `report` parameter is expecting a long string of text in markdown format.

A `tool.yaml` file would contain, at minimum, the following fields:
- `name` - the unique name of the tool (string)
- `enabled` - if the tool is enabled for use in the API (boolean)
- `config` - an array of configurations relevant to the tool itself, which the `tool.py` file would load as it's configuration.

Example `tool.yaml`:
```
name: "static-analysis"
enabled: true
config:
  example_setting: "value"
  debug_mode: false
  exclude_dirs:
    - "data/meeting_notes_local"
    - "data/meeting_notes_remote"
```

### Tool plugin folder structure

In our example with the static analysis tool, the folder structure would look like this:
```
/     # application root   
├── tools/                # tools plugin root
│   └── static-analysis/            # a tool within the tools directory, in this case 'static-analysis' is an instance of a tool
│       ├── __init__.py
│       ├── tool.py      # The entry point for calling the tool at runtime
│       └── tool.yaml    # The configuration for the tool's definition and configuration parameters
```

## Plugin Mechanics

There will need to be one or more feature that manages the detection and calling of tools.  These features would do the following:
- **Return a list of enabled tools** - loop over all the directories within the `/tools` directory and search or `tool.yaml` files.  Returns an array of `ToolInfo` objects only for tools that are enabled in their configuration
- **Call a tool** - accepts a tool name, repository_url, and any JSON input parameters, then calls the corresponding `tool.py` entry point asynchronously for the designated tool.  Will error if the tool is not enabled.  (see the implementation of code reviews for an example of how to handle async calling)

## Data model updates

We will need to update the mongoDB data model schema to add the new "toolReport object"

```
interface ToolReport {
    _id: ObjectId;             // Report identifier
    tool_name: string; // Name of the tool
    report: string;           // Detailed tool output report
    issues: Issue[];          // List of identified issues
    score?: number;           // Optional tool score
}

interface ToolInfo {
    _id: ObjectId;             // Standard set identifier
    name: string;              // Name of the standard set
    input_parameters?: string;          // Optional input parameter information
}
```

We will also need to update the follow :

```
interface CodeReview {
    _id: ObjectId;              // Unique identifier
    repository_url: string;     // Repository URL to analyze
    status: ReviewStatus;       // Current review status
    standard_sets: StandardSetInfo[]; // Associated standard sets
    compliance_reports: ComplianceReport[]; // Review results
    tools: ToolInfo[]; // NEW toolInfo object
    tool_reports: ToolReport[]; // NEW tool reports array
    created_at: DateTime;       // Creation timestamp
    updated_at: DateTime;       // Last update timestamp
    error_message?: string;     // Optional error message
    git_ref?: string;          // Optional Git reference (branch/tag)
}
```

## New API endpoints

We will add new API endpoints to the backend server as follows:
- A GET to `/api/v1/tools`, will return the list of enabled tools
- A POST to `/api/v1/tools/{tool-name}`, will call the tool and pass in the report and JSON body as input parameters. (**NOTE:** Not sure this endpoint is needed, given we are likely to only call tools via the code_reviews endpoints.  Might be needed if we wanted to call a tool directly).

## Updates to exiting API endpoints

 ### POST to `/api/v1/code-reviews` currently accepts the following post data:
 
```
{
  "repository_url": "string",
  "standard_sets": [
    "FfDEBf8f1178E6FcEBEcD43d"
  ]
}
```

We want to extend this to add a "tools" array with input parameters (optional) as follows:
```
{
  "repository_url": "string",
  "standard_sets": [
    "FfDEBf8f1178E6FcEBEcD43d"
  ]
  "tools": [
    {"name": "static-analysis", "input_parameters": {"param1": true, "another": "testing 123"}},
    {"name": "guideline-tool", "input_parameters": {"someparam": "test", "anotherParam": "testing 123"}}
  ]
}
```

When the tool information is passed in, it will be saved in the database in the new 'tools' array of the `CodeReview` collection.

During the POST processing for `/api/v1/code-reviews`, each of the tools will be parsed and passed to the functionality that handles tool calling, passing the input parameters (optional).

The endpoint will then asynchronously process each tool in the array, similar to what it does with the existing code review process.

### GET to `/api/v1/code-reviews/{id}` current returns the following response:

```
{
  "_id": "679b6ca0080a49f100b0edae",
  "repository_url": "https://github.com/DEFRA/find-ffa-data-ingester",
  "status": "completed",
  "standard_sets": [
    {
      "_id": "6798f4151cb87d7c7420b554",
      "name": "Test Standards"
    }
  ],
  "compliance_reports": [
    {
      "_id": "679b6cfd3355648a5282c421",
      "tool_name": "Test Standards",
      "file": "data/codebase/679b6ca0080a49f100b0edae-Test Standards.md",
      "report": "# Test Standards Code Review\nDate: 30 January 2025 12:13:49\nMatched Classifications: Javascript, Node.js\n\nI'll analyze the codebase against the Node.js Coding Standards provided. Here's the compliance report:\n\n## Standard: Node.js Coding Standards\n\nCompliant: <span style=\"color: #1d70b8\">**Partially**</span>\n\nRelevant Files/Sections:\n- src/**/*.js\n- .eslintrc.cjs\n- .prettierrc.js\n- package.json\n- tsconfig.json\n\nThe codebase implements many of the required standards but has some gaps. Let's break it down by category:\n\n## General Guidelines\n\n..."
    }
  ],
  "created_at": "2025-01-30T12:12:16.507000",
  "updated_at": "2025-01-30T12:13:49.701000"
}
```

We want to extend this response to add a "tools" array and a "tool_reports" array to response that will be an array of 'ToolReport' objects (as defined in the data model section above).  Example new response:

```
{
  "_id": "679b6ca0080a49f100b0edae",
  "repository_url": "https://github.com/DEFRA/find-ffa-data-ingester",
  "status": "completed",
  "standard_sets": [
    {
      "_id": "6798f4151cb87d7c7420b554",
      "name": "Test Standards"
    }
  ],
- "tools": [
    {
      "_id": "6798f4151cb87d7c7420b554",
      "name": "Test Standards",
      "input_parameters": {"testing": 123}
    }
  ],
  "compliance_reports": [
    {
      "_id": "679b6cfd3355648a5282c421",
      "standard_set_name": "Test Standards",
      "file": "data/codebase/679b6ca0080a49f100b0edae-Test Standards.md",
      "report": "# Test Standards Code Review\nDate: 30 January 2025 12:13:49\nMatched Classifications: Javascript, Node.js\n\nI'll analyze the codebase against the Node.js Coding Standards provided. Here's the compliance report:\n\n## Standard: Node.js Coding Standards\n\nCompliant: <span style=\"color: #1d70b8\">**Partially**</span>\n\nRelevant Files/Sections:\n- src/**/*.js\n- .eslintrc.cjs\n- .prettierrc.js\n- package.json\n- tsconfig.json\n\nThe codebase implements many of the required standards but has some gaps. Let's break it down by category:\n\n## General Guidelines\n\n..."
    }
  ],
  "tool_reports": [
    {
      "_id": "679b6cfd3355648a5282ddd",
      "tool_name": "static-analysis",
      "report": "# Test reporting output in mardown format"
    }
  ],
  "created_at": "2025-01-30T12:12:16.507000",
  "updated_at": "2025-01-30T12:13:49.701000"
}
```


## Frontend updates

In the existing Node.js frontend, we would like to make the following updates:

### update to the `/` homepage (/src/server/home/index.js route)

- The page should call a GET to `/api/v1/tools` to load the list of available tools.
- Underneath the existing standards checkboxes, there should be a new section called 'Tools'
- The 'Tools' section should contain a list of tools that can be called from the GET endpoint, including a checkbox to add the tool to the from post (see the standards section functionality for reference)
- When the form is submitted to the POST to `/api/v1/code-reviews`, the "tools" section will be populated with the checked tools as outlined above

### update to the /code-reviews/{id}  detail page

- The code reviews detail page should parse the additional `tool_reports` array from the `/api/v1/code-reviews/{id}` GET request and append the tool reports as additional tabs to the reporting output tab group, with the content to be the 'report' field, same as with the 'compliance_reports' handling.
- The name of each tap should be the `tool_name` parsed to replace any dashes or underscores as spaces, and convert to sentence case.
