#!/usr/bin/env python3
"""Script to delete collections from MongoDB."""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def get_mongodb_client():
    """Get MongoDB client and database."""
    mongo_uri = os.getenv("MONGO_URI")
    database = os.getenv("MONGO_INITDB_DATABASE", "code_reviews")
    
    if not mongo_uri:
        print("Error: MONGO_URI environment variable is not set")
        return None, None
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client[database]
    return client, db

async def delete_all_code_reviews():
    """Delete all code reviews from the database."""
    client, db = await get_mongodb_client()
    if db is None:
        return
    
    try:
        collection = db.code_reviews
        result = await collection.delete_many({})
        print(f"Successfully deleted {result.deleted_count} code reviews")
    except Exception as e:
        print(f"Error deleting code reviews: {e}")
    finally:
        client.close()

async def delete_all_standard_sets():
    """Delete all standard sets and their associated standards."""
    client, db = await get_mongodb_client()
    if db is None:
        return
    
    try:
        # Delete from both standard_sets and standards collections
        standard_sets = db.standard_sets
        standards = db.standards
        
        standards_result = await standards.delete_many({})
        sets_result = await standard_sets.delete_many({})
        
        print(f"Successfully deleted {sets_result.deleted_count} standard sets")
        print(f"Successfully deleted {standards_result.deleted_count} standards")
    except Exception as e:
        print(f"Error deleting standard sets: {e}")
    finally:
        client.close()

async def delete_all_classifications():
    """Delete all classifications from the database."""
    client, db = await get_mongodb_client()
    if db is None:
        return
    
    try:
        collection = db.classifications
        result = await collection.delete_many({})
        print(f"Successfully deleted {result.deleted_count} classifications")
    except Exception as e:
        print(f"Error deleting classifications: {e}")
    finally:
        client.close()

async def delete_all():
    """Delete all documents from all collections."""
    await delete_all_code_reviews()
    await delete_all_standard_sets()
    await delete_all_classifications()

def print_menu():
    """Print the menu options."""
    print("\nMongoDB Collection Cleanup Tool")
    print("1. Delete all code reviews")
    print("2. Delete all standard sets (includes standards)")
    print("3. Delete all classifications")
    print("4. Delete everything")
    print("5. Exit")
    print("\nEnter your choice (1-5): ", end="")

async def main():
    """Main function with menu interface."""
    while True:
        print_menu()
        choice = input()
        
        if choice == "1":
            await delete_all_code_reviews()
        elif choice == "2":
            await delete_all_standard_sets()
        elif choice == "3":
            await delete_all_classifications()
        elif choice == "4":
            confirm = input("Are you sure you want to delete ALL collections? (y/N): ")
            if confirm.lower() == "y":
                await delete_all()
        elif choice == "5":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    asyncio.run(main())
