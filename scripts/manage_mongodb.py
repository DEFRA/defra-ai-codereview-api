#!/usr/bin/env python3
"""Script to manage MongoDB test data."""
import json
import os
import argparse
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

class MongoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB data types."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

def get_db():
    """Get MongoDB database connection."""
    load_dotenv()
    client = MongoClient(os.getenv("MONGO_URI"))
    return client[os.getenv("MONGO_INITDB_DATABASE")]

def dump_database(test_data_dir: str = "test_data"):
    """Dump the current state of MongoDB to the test_data directory."""
    db = get_db()
    
    # Create dumps directory if it doesn't exist
    dumps_dir = os.path.join(test_data_dir, "mongodb_dumps")
    os.makedirs(dumps_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(dumps_dir, f"mongodb_dump_{timestamp}.json")
    
    # Dump data
    dump_data = {}
    for collection_name in db.list_collection_names():
        documents = list(db[collection_name].find())
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        dump_data[collection_name] = documents
    
    # Save to file using custom encoder
    with open(output_file, 'w') as f:
        json.dump(dump_data, f, indent=2, cls=MongoJSONEncoder)
    
    print(f"Database dumped to: {output_file}")
    return output_file

def restore_database(dump_file: str = None):
    """Restore database from a dump file in test_data directory."""
    if dump_file is None:
        # If no file specified, use the most recent dump
        dumps_dir = "test_data/mongodb_dumps"
        if not os.path.exists(dumps_dir):
            print("No dumps directory found")
            return
        
        dumps = sorted([f for f in os.listdir(dumps_dir) if f.endswith('.json')],
                      key=lambda x: os.path.getmtime(os.path.join(dumps_dir, x)),
                      reverse=True)
        
        if not dumps:
            print("No dump files found")
            return
        
        dump_file = os.path.join(dumps_dir, dumps[0])
    
    if not os.path.exists(dump_file):
        print(f"Dump file not found: {dump_file}")
        return
    
    # Load dump data
    with open(dump_file, 'r') as f:
        dump_data = json.load(f)
    
    # Clear and restore database
    db = get_db()
    for collection_name in dump_data:
        # Clear existing data
        db[collection_name].delete_many({})
        
        # Convert string IDs to ObjectId
        documents = []
        for doc in dump_data[collection_name]:
            # Convert _id to ObjectId
            if '_id' in doc:
                doc['_id'] = ObjectId(doc['_id'])
            
            # Convert other *_id fields to ObjectId
            for key in doc:
                if key.endswith('_id') and isinstance(doc[key], str):
                    try:
                        doc[key] = ObjectId(doc[key])
                    except:
                        # Keep as string if not a valid ObjectId
                        pass
                elif key.endswith('_ids') and isinstance(doc[key], list):
                    # Convert list of IDs
                    doc[key] = [ObjectId(id_str) for id_str in doc[key] if isinstance(id_str, str)]
            
            documents.append(doc)
            
        # Insert dump data
        if documents:
            db[collection_name].insert_many(documents)
    
    print(f"Database restored from: {dump_file}")

def main():
    parser = argparse.ArgumentParser(description="Manage MongoDB test data")
    parser.add_argument('action', choices=['dump', 'restore'],
                       help='Action to perform (dump/restore)')
    parser.add_argument('--file', '-f',
                       help='Specific dump file to restore from (for restore action)')
    
    args = parser.parse_args()
    
    if args.action == 'dump':
        dump_database()
    elif args.action == 'restore':
        restore_database(args.file)

if __name__ == "__main__":
    main()
