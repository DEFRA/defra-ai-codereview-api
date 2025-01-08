Create a detailed PRD document in an markdown format outlining the following feature requirements.  I want the PRD to be in a single downloadable markdown file.  Ensure you use the best practices standards.
## Context

We want to create a Python fastapi server that will check a code base against multiple standards

The API will create an instance of a code base review record in mongoDB to then be tracked.  We will query this instance to get handle the workflow of analyzing a user-entered code base against a set of standards.  The record in the mongDB will be used for tracking that workflow, and report status, as well as managing the reports themselves.

We want to run MongoDB locally using Docker.

We want a separate config for each environment (local, dev, test, production)

The API route will be prepended with /api/v1 (we will only support a v1 at this time)
## Creating code review endpoints

I want to create the following endpoint:
/api/v1/code-reviews

A POST request to /api/v1/code-reviews will do the following:
1. Create a new code review record in the mongoDB, with the status of 'started'
2. The endpoint will return the newly created record, along with the status to the caller
3. The endpoint will trigger a asynchronous agentic workflow using Antropic API calls directly.  Right now this should just be a simple 'hello world' LLM query that returns a structured output of {"success": true}.  This should be a separate, fully functioning agent within the codebase, however, we will add functionality to this later.

A GET request to /api/v1/code-reviews will do the following:
1. This request will return a JSON array of all the code review records in the mongoDB, along with their status

A GET request to /api/v1/code-reviews/[id] will do the following:
1. This will return the single code review record by 'id' in JSON format, along with any relevant status information

