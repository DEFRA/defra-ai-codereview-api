---

kanban-plugin: board

---

## Backlog

- [ ] Spike - "Graph RAG" for large codebases?
	- is there a way we can save tokens


## To Do

- [ ] max tokens limit in llm call?
- [ ] merge 5.5 branch into standards ingest
- [ ] Investigate and fix the rate limit issue - bedrock?
- [ ] Get running on CDP dev w/ bedrock
- [ ] add local LLM ollama dev for backend
- [ ] refactor dependency.py injection file for the existing code review?
- [ ] pull out the anthropic model into the .env file
- [ ] Extensive testing on endpoints to ensure they are consistent
- [ ] verify - logging_config - only write to logfile when running locally, not in aws envs
- [ ] refactor async def check_compliance() as its HUGE
- [ ] Hooks: Linting, formatting, commit hooks for python api backend
		- pylint --rcfile=/path/to/.pylintrc src tests
- [ ] Check out the errors.py file and how error type handling works
- [ ] review .cursorrules
- [ ] pip freeze, python lib mgmt - add to .cursorrules?


## Doing



## Done

**Complete**
- [x] [[standards-ingest-prd]]
- [ ] fix async issue
- [ ] current branch:
	
	Remove the id field
	
	Review the versions of the libraries
	
	Add tests and test coverage
- [ ] Update cursor rules to tell it to always ensure it using the latest versions of libraries in the requirements.txt




%% kanban:settings
```
{"kanban-plugin":"board","list-collapse":[false,false,false,false]}
```
%%