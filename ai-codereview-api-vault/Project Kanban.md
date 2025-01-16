---

kanban-plugin: board

---

## To Do

- [ ] extend dependency.py injection file for the existing code review?
- [ ] refactor to have an array of reports, currently hard-coded (poc / demos)
- [ ] generate report with name using id
- [ ] add e2e tests in playwright
- [ ] Future iteration - logging_config - only write to logfile when running locally, not in aws envs
- [ ] Tag standards and store them in mongo. Use the tags to only find relevant standards (Todds diagram)
- [ ] Future feature for standards ingest - other sources standards
- [ ] Spike - "Graph RAG" for large codebases?
- [ ] refactor async def check_compliance() as its HUGE


## Doing



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