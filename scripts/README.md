# Scripts

This directory contains utility scripts for managing the project.

## MongoDB Management Script

The `manage_mongodb.py` script provides functionality to manage MongoDB data for testing purposes. It allows you to dump the current state of the database and restore it later, which is particularly useful for setting up test data.

### Prerequisites

- Python 3.x
- MongoDB running locally
- Environment variables set in `.env` file:
  - `MONGO_URI`: MongoDB connection string
  - `MONGO_INITDB_DATABASE`: Database name

### Usage

#### Dumping Database State

To create a dump of the current database state:

```bash
./scripts/manage_mongodb.py dump
```

This will:
1. Create a timestamped JSON dump file in `test_data/mongodb_dumps/`
2. Convert MongoDB-specific data types (ObjectId, datetime) to JSON-serializable formats
3. Save all collections and their documents

#### Restoring Database State

To restore the database from a dump, you have two options:

1. Restore from the most recent dump:
```bash
./scripts/manage_mongodb.py restore
```

2. Restore from a specific dump file:
```bash
./scripts/manage_mongodb.py restore --file test_data/mongodb_dumps/mongodb_dump_YYYYMMDD_HHMMSS.json
```

The restore process will:
1. Clear the existing data in each collection
2. Insert the data from the dump file
3. Preserve the original document IDs and timestamps

### File Structure

```
test_data/
└── mongodb_dumps/
    └── mongodb_dump_YYYYMMDD_HHMMSS.json
```

Each dump file is a JSON document containing:
- Collection names as top-level keys
- Array of documents for each collection
- Serialized ObjectIds and ISO-formatted dates
