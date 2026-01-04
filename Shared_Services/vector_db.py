import os
import time
import urllib.parse
from pymongo import MongoClient
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.azure_cosmos_db import AzureCosmosDBVectorSearch
from dotenv import load_dotenv

load_dotenv()

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
class VectorDBManager:
    def __init__(self):
        # 1. Configuration (The exact settings that worked for you)
        self.username = os.getenv("DB_USERNAME")
        self.password = os.getenv("DB_PASSWORD") 
        self.username = "ssmsaknadmin"
        self.password = "sitaatisa_123"
        self.escaped_username = urllib.parse.quote_plus(self.username)
        self.escaped_password = urllib.parse.quote_plus(self.password)
        
        self.mongo_uri = f"mongodb+srv://{self.escaped_username}:{self.escaped_password}@imagine-cup-db.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
        self.db_name = "SecurityDB"
        self.collection_name = "VulnerabilityMemory" 
        self.index_name = "vectorSearchIndex"
        
        # 2. Initialize Connection
        #print(" Connecting to Azure Cosmos DB...")
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        
        # 3. Load the Brain (Embeddings)
        #print(" Loading AI Embeddings...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # 4. Auto-Setup Index (Only runs if needed)
        self._ensure_index_exists()

        # 5. Link LangChain
        self.vector_store = AzureCosmosDBVectorSearch(
            collection=self.collection,
            embedding=self.embeddings,
            index_name=self.index_name,
            embedding_key="vector"
        )
        #print(" Vector Database Ready.")

    def _ensure_index_exists(self):
        """Checks if index exists. If not, builds it using the IVF settings."""
        # Check existing indexes
        existing_indexes = self.collection.index_information()
        
        if self.index_name in existing_indexes:
            #print("Index already exists. Skipping build.")
            return

        print(" Index not found. Building IVF Index (This happens once)...")
        index_command = {
            "createIndexes": self.collection_name,
            "indexes": [
                {
                    "name": self.index_name,
                    "key": { "vector": "cosmosSearch" }, 
                    "cosmosSearchOptions": {
                        "kind": "vector-ivf",   
                        "numLists": 1,
                        "similarity": "COS",
                        "dimensions": 384 
                    }
                }
                
            ]
        }
        try:
            self.db.command(index_command)
            #print("Index creating... Waiting 30s for Azure to catch up...")
            time.sleep(30) # The magic nap
            #print("Index built successfully.")
        except Exception as e:
            pass #print(f"Index Warning: {e}")

    def add_memory(self, text, metadata=None):
        """Saves a piece of information to the long-term memory."""
        #print(f"Saving to memory: '{text[:30]}...'")
        self.vector_store.add_texts(
            texts=[text],
            metadatas=[metadata or {}]
        )

    def search_memory(self, query, top_k=3):
        """Retrieves relevant info based on meaning."""
        #print(f"Searching for: '{query}'")
        results = self.vector_store.similarity_search(query, k=top_k)
        return results