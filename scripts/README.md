# Scripts

This directory contains utility scripts for managing various aspects of the project during local development and testing.

Important: These scripts are not intended for use in environments other than local development and testing.

## MongoDB Backup Script

The `mongo_backup.py` script provides functionality to manage MongoDB data for local testing purposes. It allows you to dump the current state of the database and restore it later.

### Prerequisites:

- Python 3.x
- MongoDB running locally
- Environment variables set in the `.env` file:
  - `MONGO_URI`: MongoDB connection string
  - `MONGO_INITDB_DATABASE`: Database name

### Execution:

#### Dumping Database State

```bash
./scripts/mongo_backup.py dump
```

This creates a timestamped JSON dump file in `test_data/mongodb_dumps/` with all collections and documents.

#### Restoring Database State

To restore the most recent dump:

```bash
./scripts/mongo_backup.py restore
```

Or to restore from a specific dump file:

```bash
./scripts/mongo_backup.py restore --file test_data/mongodb_dumps/mongodb_dump_YYYYMMDD_HHMMSS.json
```

## Mongo Reset Script

The `mongo_reset.sh` script resets the local MongoDB database to a clean state for fresh testing.

### Execution:

```bash
./scripts/mongo_reset.sh
```

## Mongo Delete Data Script

The `mongo_delete_data.py` script is designed to delete specific data from the local MongoDB database collections; useful for resetting states or clearing test data without having to manually delete each item or reset the database.

### Execution:

Run directly if executable:

```bash
./scripts/mongo_delete_data.py
```

## Files Cleanup Script

The `files_cleanup.sh` script removes temporary files from the project directory.

### Execution:

```bash
./scripts/files_cleanup.sh
```

## Server Start Script

The `server_start.sh` script is a utility to start the application server.

### Execution:

```bash
./scripts/server_start.sh
```

## Git Cleanup Script

The `git_cleanup.sh` script helps remove unnecessary files and clean up Git branches or caches to maintain a tidy repository.

### Execution:

```bash
./scripts/git_cleanup.sh
```