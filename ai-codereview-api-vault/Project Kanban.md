---

kanban-plugin: board

---

## To Do

- [ ] Do we need to break down the standards file ingest into more granular standards (adding a loop over the file to have an LLM pull out individual standards)?
- [ ] extend dependency.py injection file for the existing code review?
- [ ] pull out the anthropic model into the .env file
- [ ] Future iteration - logging_config - only write to logfile when running locally, not in aws envs
- [ ] Spike - "Graph RAG" for large codebases?
	- is there a way we can save tokens
- [ ] refactor async def check_compliance() as its HUGE
- [ ] Hooks: Linting, formatting, commit hooks for python api backend
		- pylint --rcfile=/path/to/.pylintrc src tests
- [ ] Check out the errors.py file and how error type handling works
- [ ] snaglist: logging in code-reviews
- [ ] covert the classification IDs in the standards table from strings to IDs:
	
	Looking at the code and test data, I can see that we have inconsistency in how classification_ids are stored:
	
	1. In the model (src/models/standard.py), they're defined as List[PyObjectId]
	
	- In some tests they're stored as strings ("classification_ids": ["class1"])
	
	- In other tests they're stored as ObjectIds ("classification_ids": [ObjectId(), ObjectId()])


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