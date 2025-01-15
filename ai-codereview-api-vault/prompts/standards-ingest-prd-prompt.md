Create a detailed PRD document in an markdown format outlining the following feature requirements.  I want the PRD to be in a single downloadable markdown file.  Ensure you use the best practices standards.

# Background context - Exec summary

We are developing an application that compares an entire code base against multiple sets of standards, then generates a report for each set of standards
## Core Functionality
- Accept code submissions for review
- Process these submissions asynchronously using AI agents
- Check code against multiple predefined standards
- Store review results in MongoDB for persistence
- Provide API endpoints to retrieve and manage code review results

We currently have an end to end flow that processes the code submissions against a hard-coded set of standards, however, this PRD will add functionally to ingest any type of standard to review the code base against.

All frontend code follows GDS standards for design and content.

# Background context - API backend

## Current State

The Defra Coder Review API is a Python-based service designed to perform automated code reviews using AI agents. The system is built on FastAPI, providing a modern, async-first API framework that enables high-performance code analysis operations. The project leverages Anthropic's Claude AI model for intelligent code analysis and stores results in MongoDB.
## Technical Architecture

The application follows a modular structure with clear separation of concerns, utilizing FastAPI's dependency injection and async capabilities. The codebase is set up with robust logging, strict typing, and comprehensive testing infrastructure. The project enforces high standards for code quality through multiple tools including Pylint for linting and Pyright for type checking.

# Background context - Frontend

## Technical Context

This is a modern Node.js web application built using the Hapi.js framework, following the GOV.UK Design System patterns and standards. The application serves as a frontend interface for a code review system, allowing users to submit repositories for review and interact with the review results.

The architecture follows a clean separation of concerns, with distinct client and server-side code organization. The frontend utilizes vanilla JavaScript without any heavy frameworks, adhering to progressive enhancement principles. Server-side rendering is handled through Nunjucks templating, integrated with GOV.UK Frontend components for consistent government service styling and accessibility.

## Current Implementation

The application employs a comprehensive development stack:

- Server: Node.js with Hapi.js for routing and request handling
- Frontend: GOV.UK Frontend design system with SCSS for styling
- Build Tools: Webpack for asset bundling, Babel for transpilation
- Quality Assurance: Jest for testing, ESLint/Prettier for code quality, TypeScript for type checking

## Current Functionality

The application currently provides:
- A home page interface for submitting code repositories
- Health check endpoints for monitoring
- Error handling pages and logic
- Basic routing structure for future feature expansion

# New Functionality - Standards ingest and review

## Overview

We want to add an user journey to add standards to the mongoDB database that allows a user to select one or more standards from the list to check against the codebase they want to analyze.  There will be multiple parts to adding this feature, such as:
- Adding a Tag Manager - the tag manager will help to match a codebase to individual standards.  For instance, if the codebase is a 'Node.js' type of codebase, then we will match all the standards that are relevant to Node.js, as well as general standards applicable to all codebases.
- Adding a standards Ingest flow (detailed below), including:
	- A new 'Manage standards' navigation menu item in the frontend
	- A frontend form to post a repository name and URL of standards to the backend for processing
	- Backend API routes to receive the standards name and URL and process the standards and save them to the database
	- A frontend standards detail page to view the standards saved in the database

## New Features

### Tag Manager

The tag manager will function to help match types of codebases to standards that are most relevant to the codebase.

#### Tag manager - backend API requirements
- A new table will need to be created in the backend database to manage tags, per the requirements below
- create a new backend API endpoint `/api/v1/tags`
- A POST to `/api/v1/tags`, will create a new tag in the backend database
- A GET to `/api/v1/tags`, will list all the tags in the database, in alphabetical order
- A DELETE to `/api/v1/tags/{id}` will delete the tag from the database and remove any tag relationships using that tag elsewhere in the database.

#### Tag Manager - Frontend requirements
- Create a new navigation menu item called 'Manage tags'
- Create a new page linked to 'Manage tags' that lists all the current tags in a table that are available via a GET to `/api/v1/tags` .  This page should allow you to add and delete tags into the database via the backend API.
	- Adding tags will call a POST to `/api/v1/tags`
	- Deleting tags will call a DELETE to `/api/v1/tags/{id}`
- Add messaging that adding or deleting tags means that all the standards will have to be re-ingested to use the new tagging scheme
#### Examples list of separate tags that cold be stored in the database, with each tag representing a type of language or technology that could be found in a codebase:

```
"Python","C#","Node.js","JavaScript","Java",".NET"
 ```

### Standards Ingest

#### Terminology
- **code repository:** the code repository we would like to analyze against a set of standards.
- **standard-sets**: the parent object of a set of individual standards.  Has a database `_id`,  a name, a repository URL and a custom reporting LLM prompt
- **standards**: an individual standard in a standard-set to be assessed against the code repository.  Has a database `_id`,  the text of the standard, a path in the standard-set repository to where the standard can be found, and a relation to any relevant tags that apply to the standard. Note: a standard may have no tags associated with it, which would mean that it is applicable to all codebases, regardless of the technologies listed in the tags.
- **tags:** a list of tags related to technologies, languages or functions within a codebase that can be used to define attributes of the code repositories. For example, a code repository that has a codebase that is primarily written in Python would meet the tagging requirements for the 'Python' tag in the database.  In addition, a standard that has a description that only pertains to Python wold also meet the tagging requirements for the 'Python' tag in the database.

#### Standards Ingest - Backend requirements
- New tables will need to be created to manage 'standard-sets' and 'standards'
- A relation is required between 'standard-sets' (parent) and individual 'standards' (children)
- A relation is required between 'standards' and 'tags', where each standard can have 0 or more tag ids associated with the tags stored in the database
- a new `/api/v1/standard-sets` endpoint will need to be crated
- a POST to `/api/v1/standard-sets` will create a new standard-set with the required payload of a name, a repository URL and a custom reporting LLM prompt.  If a Standard Set of the same name already exists in the database, then the existing standard-set object and all the standards sub-objects (and their tags) will be deleted and replace with the new version of the standard-set.
- a GET to `/api/v1/standard-sets` will return the list of standard-set objects in the database, without their associated standards.
- a GET to `/api/v1/standard-sets/{id}` will return the standard-set object in the database relating to the id slug passed in the URL, INCLUDING an array of all the standards objects associated with the standard-set
- a DELETE to `/api/v1/standard-sets/{id}` will delete a standard-set for the given id and all the associated standards (and any associated standards to tags references)
- a new `/api/v1/standards` endpoint will need to be crated
- a POST to `/api/v1/standards` will create a new standard in the database with the attributes of the text of the standard, a path in the standard-set repository to where the standard can be found, and a relation to any relevant tags that apply to the standard. Note that a standard may have no tags associated with it, which would mean that it is applicable to all codebases, regardless of the technologies listed in the tags.
- a GET to `/api/v1/standards/{id}` will return the standards object from the database for the given id slug in the URL, including all the associated tags.
- a new `/api/v1/standards/{id}/tags` endpoint will need to be created
- a POST to `/api/v1/standards/{id}/tags` with the payload of a tag database id will add a tag association between the standard id passed and the tag payload
- a DELETE to `/api/v1/standards/{id}/tags/{tag-id}` will remove the tag association in the database between a standard and the tag
##### Standards ingest functionality for the `/api/v1/standard-sets` (POST) api endpoint

When a user sends a POST request to `/api/v1/standard-sets`, the endpoint will do the following:
- Check if a standard-set with the same name already exists in the database, if so, then delete out the existing standards-set object and it's associated standards
- Create a standard-set record in the database with the information posted
- Download the the standards repository into a temporary folder
- Loop over each file that was downloaded and use an LLM agent to separate each standard file out into individual detailed standards and, at the same time, evaluate each individual standard against the tags available in the database.
- Save each standard identified in the database with the information outlined above.  If any tags are identified, then the tagging relationship should also be saved against the new standard record.  The standard should also be associated with the new standard-set record.  Standards that are relevant to all code bases, regardless of what tags are available, should always be saved with no tags.
- When complete, remove the temporary standards repository downloaded files.
- At the end of this process, you should have a new (or replaced) standard-set, a set of detailed standards associated with the new standards-set and a set of tags associated with each standard, if applicable.

#### Standards Ingest - Frontend requirements
- Create a new navigation menu item called 'Manage standards', linked to `/standard-sets`
- **Manage Standards Page (`/standard-sets`):**
	- The main standards page that will list out all the available standards in a table similar to the one used in the 'View code reviews' page.  The table should show: the standard-set Name (linked to the 'Standard Set Detail Page' detailed below), the standards repository link (linked to open in a new tab), and a delete standard button (when pressed, sends a DELETE API request to `/api/v1/standard-sets/{id}` ) 
	- On page load, a GET request to the `/api/v1/standard-sets` API backend will be called to get the list of standard-sets
	- On the frontend, the Manage Standards page will be found at `/standard-sets`
	- There will be a button for a user to add new standards, linked to `/standard-sets/new`
- **Standard Set New Page (`/standard-sets/new`):**
	- This page will allow a user to create a new Standard Set and load the associated standards
	- It will be found at `/standard-sets/new` on the frontend
	- The page will include a form to create a new standard-set, including fields for a name, a repository URL and a custom reporting LLM prompt.
	- The form will POST to the `/api/v1/standard-sets` API endpoint to create the standard, then, if successful, it will redirect to the Standard Set Detail page for the new id as defined below. i.e. `/api/v1/standard-sets/{id}`
- **Standard Set Detail Page (`/standard-sets/{id}`):**
	- This page will show the standard-set detailed information and the associated standards.
	- It will be found at `/standard-sets/{id}` on the frontend, where the id is the database id of the standard-set in the database
	- upon load, this page will query the GET to `/api/v1/standard-sets/{id}` API endpoint to get the information to render the page.
	- The page will show the details of the Standard Set, such as the name and repository url (linked to open in a new tab).  The custom reporting prompt text will be hidden by an accordion feature as per the GDS design standards.
	- The page will show a table of all the standards associated with the standard-set as a read-only list.  This table will show the information on each standard in the database, including the  text of the standard, a comma-delimited list of the tags associated with the standard and a clickable  (opens in a new tab) path in the standard-set repository to where the standard can be found.

### Updates to exiting frontend

- **Home page updates:** Currently there is a placeholder list of standards check boxes a user can check to run the codebase against the chosen standards.  This list will need to be updated with the list of standard-sets, so a user can check off the standard-sets they wish to run reports against.  To get the list of standard-sets, the home page controller will need to run a GET request to the `/api/v1/standard-sets` API backend.  Each standard-set ID that is checked will then be posted, alongside the existing `repository_url` as an array to the `/api/v1/code-reviews` backend as outlined below.
- **Code Review Record Detail Page Updates:** The reports for each standard group will be returned as an array of reports available as part of the GET request to `/api/v1/code-reviews/{id}`, then the tabbed area where the reports are show can use the array of reports to populate the tabs (and the tab names as the name of the standards set).  Also, the page can list the standard-sets that were used to run the reports for the given Code Review Record in the details section of the page.

### Updates to exiting API

#### Overview of NEW flow for POST request to `/api/v1/code-reviews`:
1) User sends the code repository they want to analyze via a POST request to  `/api/v1/code-reviews`. Note: this endpoint will be updated to include an array of standard-sets as ID values to the standard-sets in the database to run the standards against, for example:

```
{
  "repository_url": "https://github.com/DEFRA/find-ffa-data-ingester",
  "standard_sets": [
	  "xyz123",
	  "abc123"
  ]
}
```
   
2) The code repository to be analyzed will be downloaded and merged into a single file (existing functionality)
3) A new 'Standards Selection' agent will categorize the code base repository based on the tags in the database (true/false JSON object for each tag)
4) The 'Standards Selection' agent will then query the database for all the standards that meet the 'true' tag requirements AND the standards that have no tags associated (as they are applicable to all code bases)
5) The 'Standards Selection' agent will then send these standards over to the existing reporting agent to be combined with the flatted code repository file to call the LLM to run the reporting (existing functionality)

#### Detailed updates to existing API

- Currently, when a user sends a POST request to `/api/v1/code-reviews`, this starts the process to download the code base to be analyzed and also downloads a hard coded list of standards.
- We want the behavior to be changed as follows: 
	1) the `/api/v1/code-reviews` receives the POST request
	2) the codebase repository is downloaded and combined into a single file (same as existing behavior, update to fit into the new flow)
	3) a new 'Standards Selection' LLM agent analyses the merged codebase files against the tags available in the database and produces a JSON object that reports 'true' or 'false' depending if the code base in the code repository meets the tag requirements.  In the example below, the new 'Standards Selection' LLM agent will analyze the code base repository to see if it meets the tag requirements.  In the example below it is a Node.JS app, so it is true, but Python, for example, would be false:
	   
```
{
  "Python": false,
  "C#": false,
  "Node.js": true,
  "JavaScript": true,
  "Java": false,
  ".NET": false
 }
 ```

4) the 'Standards Selection' agent will then loop over each standard-set ID that was passed from the `/api/v1/code-reviews` endpoint to and use the above JSON output to query the standards and tags table in the database to select the standards that match the tags for each individual standard in the set.  It will also include standards that do not have any tags (general standards applicable to all code bases).
5) These standards will them be sent to the existing reporting agent, along with the code repository information for analysis (existing functionality, to be enhanced)
6) The loop to find the standards that match the tagging and the current standard-set id will continue for each standard-sets passed to the `/api/v1/code-reviews` endpoint.
7) The report for each standard-set will use the custom prompt saved with the standards set when it was created.  Each file for the standard set will be saved separately with the following markdown format: `{datetime (in yyyy-mm-dd-HH-ii-ss format)}-{code-review-record-id}-{standards-set-name (filename friendly)}.md`
8) The GET request to `/api/v1/code-reviews/{id}` will be updated to include the array of available reports for each standard-set, and their markdown contents, to be displayed in the Code Review Record Detail Page on the frontend, the name of the standard-set should also be included in the reports array for each item.

#### Existing API functionality to remove

We will remove the following existing functionality from the backend API:
- We no longer need to download the standards when a POST to `/api/v1/code-reviews` is called, because the standards will already be stored in the database per the new feature requirements above this is no longer required.