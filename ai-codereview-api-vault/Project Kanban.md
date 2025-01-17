---

kanban-plugin: board

---

## To Do

- [ ] extend dependency.py injection file for the existing code review?
- [ ] Future iteration - logging_config - only write to logfile when running locally, not in aws envs
- [ ] Spike - "Graph RAG" for large codebases?
	- is there a way we can save tokens
- [ ] refactor async def check_compliance() as its HUGE
- [ ] Hooks: Linting, formatting, commit hooks for python api backend
		- pylint --rcfile=/path/to/.pylintrc src tests
- [ ] Check out the errors.py file and how error type handling works


## Doing

- [ ] [[standards-ingest-prd]]


## Done

- [ ] fix async issue
- [ ] current branch:
	
	Remove the id field
	
	Review the versions of the libraries
	
	Add tests and test coverage
- [ ] Update cursor rules to tell it to always ensure it using the latest versions of libraries in the requirements.txt




%% kanban:settings
```
{"kanban-plugin":"board","list-collapse":[false,false,false]}
```
%%