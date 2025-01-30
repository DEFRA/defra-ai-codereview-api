---

kanban-plugin: board

---

## Backlog

- [ ] Spike - "Graph RAG" for large codebases?
	- is there a way we can save tokens


## To Do

- [ ] Investigate and fix the rate limit issue - bedrock?
- [ ] Get running on CDP dev w/ bedrock
- [ ] add local LLM ollama dev for backend
- [ ] verify - logging_config - only write to logfile when running locally, not in aws envs
- [ ] Hooks: Linting, formatting, commit hooks for python api backend
		- pylint --rcfile=/path/to/.pylintrc src tests
- [ ] pip freeze, python lib mgmt - add to .cursorrules?


## Doing

- [ ] refactor - see snag list canvas
- [ ] improve testing and refactoring prompts


## Done

**Complete**
- [x] max tokens limit in llm call?
- [x] [[standards-ingest-prd]]
- [ ] fix async issue
- [ ] current branch:
	
	Remove the id field
	
	Review the versions of the libraries
	
	Add tests and test coverage
- [ ] Update cursor rules to tell it to always ensure it using the latest versions of libraries in the requirements.txt
- [x] merge 5.5 branch into standards ingest
- [x] review .cursorrules
- [x] Update Docs in code checker tool




%% kanban:settings
```
{"kanban-plugin":"board","list-collapse":[false,false,false,false]}
```
%%