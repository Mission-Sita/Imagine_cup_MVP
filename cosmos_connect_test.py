import os
from azure.cosmos import CosmosClient,PartitionKey
from dotenv import load_dotenv

load_dotenv()
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)


database = client.create_database_if_not_exists(
    id="cyber_knowledge"
)

container = database.create_container_if_not_exists(
    id="documents",
    partition_key=PartitionKey(path="/type")
)

print("Database and container created successfully (serverless)")