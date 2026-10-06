from qdrant_client.models import VectorParams,Distance
from config import EMBEDDING_MODEL_DIMENSION



def get_collection_names(set_id):
    docs_name=f"{set_id}_docs"
    memory_name=f"{set_id}_memory"

    return docs_name,memory_name

def create_collection(client, collection_name):
    if client.collection_exists(collection_name):
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=EMBEDDING_MODEL_DIMENSION,
            distance=Distance.COSINE
        )
    )

def create_set_collections(client, set_id):
    docs_name,memory_name=get_collection_names(set_id=set_id)

    create_collection(client=client,collection_name=docs_name)
    create_collection(client=client,collection_name=memory_name)

def delete_set_collections(client, set_id):
    docs_name,memory_name=get_collection_names(set_id=set_id)

    if client.collection_exists(docs_name):
        client.delete_collection(docs_name)
    if client.collection_exists(memory_name):
            client.delete_collection(memory_name)
 