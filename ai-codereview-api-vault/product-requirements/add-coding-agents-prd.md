# PRD: Extension to `/api/v1/codereviews` Endpoint

## 1. Overview

### 1.1 Purpose

This document details the requirements for extending the existing microservice—which includes a set of REST APIs built using Python and FastAPI—to add new functionality to the `/api/v1/codereviews` endpoint. The goal is to incorporate two new agents:

1. **Git Repos Agent**  
2. **Standards Checking Agent**

These agents will work together to download a target code repository, fetch a set of software standards, and generate a comprehensive compliance report.

These agents will run asynchronously, the POST endpoint will respond in a separate process immediately as it currently does.

### 1.2 Background

The `/api/v1/codereviews` endpoint currently exists but needs enhanced functionality to:
- Accept a code repository URL  
- Download and flatten the files from that repository  
- Download the files from a hardcoded standards repository into separate files  
- Check the codebase's compliance against the standards  
- Return a comprehensive compliance report  

### 1.3 High-Level Flow

```
POST /api/v1/codereviews (payload='repository_url') | ↓ [Git Repos Agent] | ↓ [Standards Checking Agent] | ↓ Compliance Report
```

## 2. Feature Requirements

### 2.1 Functional Requirements

1. **Extend the `/api/v1/codereviews` endpoint (POST)**
   - **Request Body**: JSON object containing `repository_url`
   - **Behavior**:
     - When called, invoke the asynchronous flow to:
       1. Trigger the _Git Repos Agent_
       2. Pass the output to the _Standards Checking Agent_
       3. Generate a markdown-based compliance report

2. **Git Repos Agent**
   - **Description**: Downloads the specified repository and a hardcoded standards repository, then flattens the code repository into one file and downloads each standard as separate files.
   - **Inputs**:
     - The `repository_url` from the `/api/v1/codereviews` POST request
     - A hardcoded standards repository URL:
       - `https://github.com/DEFRA/software-development-standards`
   - **Process**:
     - **Clone/Download** the code repository from `repository_url`
     - **Flatten** each file in the repo into a single text file:
       - **File naming**:
         - The output file should be saved under `/data/codebase/<REPO_NAME>.txt`
         - Each file's content is preceded by a heading which is the filename
       - **Overwrite** the file if it already exists
     - **Clone/Download** the standards repository
     - **For each file** in the standards repo:
       - Save each standard as a separate `.txt` file in `/data/standards/`
       - Each file's content is preceded by a heading which is the filename
       - **Overwrite** each file if it already exists
   - **Outputs**:
     - **One file path** for the flattened codebase file:
       1. `codebase_flattened_file_path` (e.g., `/data/codebase/<REPO_NAME>.txt`)
     - **An array of file paths** for the standards files:
       2. `standards_files_list` (e.g., a list of file paths in `/data/standards/`)
   - **Notes**:
     - Generate **verbose logging** to assist in debugging the repository cloning and flattening process

3. **Standards Checking Agent**
   - **Description**: Receives the flattened codebase file path plus an array of standards file paths to perform a compliance check
   - **Inputs**:
     - `codebase_flattened_file_path`  
     - `standards_files_list` (array of file paths for each standard)
   - **Process**:
     1. Create system prompts using the following context:
        ```
        You are a code compliance analysis expert,
        Analyze code against compliance standards,
        Determine if code meets each standard,
        Provide detailed recommendations for non-compliant areas,
        Consider the codebase as a whole when evaluating compliance
        ```
     2. For each file in `standards_files_list`, generate a user prompt incorporating:
        - The content of that standard (from the individual `.txt` file)
        - The content of the `codebase_flattened_file_path`
        - Add the content into the prompt via f-strings
        - The format:
          ```text
          Given the standard below:
          {standard_file_content}.
          
          Compare the entire codebase of the submitted repository below, to assess how well 
          the relevant standards are adhered to:
          {codebase}
          
          For each standard:
          - Determine if the codebase as a whole is compliant (true/false)
          - List specific files/sections relevant to the standard
          - If non-compliant, provide detailed recommendations
          - Consider dependencies and interactions between different parts of the code
          
          Generate a detailed compliance report that includes:
          - Overall compliance assessment
          - Per-standard analysis
          - Specific recommendations for improvements
          ```
        - Invoke the **Anthropic `claude-3-5-sonnet-20241022`** model to generate the compliance result for that standard
     3. **Aggregate the results** from each standard into one final markdown compliance report by **appending** the content from each LLM call to the end of a single output file.
   - **Outputs**:
     - A markdown-based compliance report detailing:
       - Overall compliance assessment
       - Per-standard analysis
       - Recommendations for improvement

4. **Coding Standards**
   - **Verbose Logging**: During the repository download, flattening process, and standards checking, ensure debug-level logs provide insights into:
     - Function calls
     - File operations
     - Interactions with the Anthropic model

5. **Behaviors NOT to Do**
   - **Do Not** modify any other API endpoints besides `POST /api/v1/codereviews`
   - **Do Not** modify the API signature i.e `POST /api/v1/codereviews` - the agents will get called by this endpoint

## 3. Technical Details

### 3.1 Architecture & Sequence

1. **Client Request**: `POST /api/v1/codereviews` with `{"repository_url": "<URL>"}`
2. **Git Repos Agent**:
   1. Uses an async method to clone/pull the given `<URL>`
   2. Iterates over each file, extracts the content, and writes them to `/data/codebase/<REPO_NAME>.txt`
   3. Clones/downloads the hardcoded standards repo `https://github.com/DEFRA/software-development-standards`
   4. Iterates over each standards file, extracts content, and writes them individually as separate `.txt` files in `/data/standards/`
3. **Standards Checking Agent**:
   1. Receives the path for the codebase file (`/data/codebase/<REPO_NAME>.txt`) and the array of standards file paths in `/data/standards/`
   2. For each standard file, constructs the user prompt using the snippet above
   3. Invokes the Anthropic model (`claude-3-5-sonnet-20241022`) for compliance checking on each standard
   4. Appends each compliance result to the same markdown file, creating one final aggregated compliance report

## 4. Acceptance Criteria

### Successful Download & Flatten

- Given a valid repository_url, the system should create:
  - One flattened file: `/data/codebase/<REPO_NAME>.txt`  
  - Multiple standard files saved in `/data/standards/`
- The content for each codebase file must include headings equal to the original filename; likewise, each standard file in `/data/standards/` must also include a heading of its original filename.
- The process must overwrite existing files if they exist

### Successful Compliance Report

- The compliance report must show:
  - Overall compliance assessment
  - Per-standard analysis
  - Specific recommendations
- The final output must be generated via the Anthropic claude-3-5-sonnet-20241022 model
- The Standards Checking Agent must iterate over each standard file individually, rather than sending all standards at once
- The content from each LLM call must be appended to one single aggregated markdown file

### No Impact on Other Endpoints

- No calls or behaviors of other endpoints (besides `/api/v1/codereviews`) are changed

### Verbose Logging

- All key steps in the process—downloading, file handling, model invocation—log relevant debug messages