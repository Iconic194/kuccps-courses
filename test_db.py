from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

def test_connection():
    MONGODB_URI = "mongodb+srv://iconichean:1Loye8PM3YwlV5h4@cluster0.meufk73.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        print("🔄 Attempting to connect to MongoDB...")
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=15000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        
        # List databases
        databases = client.list_database_names()
        print("📊 Available databases:", databases)
        
        # Check if user_data database exists
        if 'user_data' in databases:
            print("✅ user_data database exists")
            db_user_data = client['user_data']
            collections = db_user_data.list_collection_names()
            print("📁 Collections in user_data:", collections)
            
            # Check for our specific collections
            target_collections = ['user_payments', 'user_courses']
            for coll in target_collections:
                if coll in collections:
                    print(f"✅ {coll} collection exists")
                    # Count documents
                    count = db_user_data[coll].count_documents({})
                    print(f"   📄 Documents in {coll}: {count}")
                else:
                    print(f"❌ {coll} collection does not exist (will be created automatically)")
        else:
            print("❌ user_data database does not exist (will be created automatically)")
        
        # Check course databases
        course_dbs = ['Degree', 'diploma', 'kmtc', 'certificate', 'artisan']
        for db_name in course_dbs:
            if db_name in databases:
                print(f"✅ {db_name} database exists")
                db = client[db_name]
                collections = db.list_collection_names()
                print(f"   📁 Collections in {db_name}: {len(collections)} collections")
            else:
                print(f"❌ {db_name} database does not exist")
        
        client.close()
        return True
        
    except ConnectionFailure as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_connection()