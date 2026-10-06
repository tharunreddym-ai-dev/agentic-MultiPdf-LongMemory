import os
import shutil
import tempfile

from fastapi import (APIRouter, 
                     HTTPException, 
                     UploadFile, 
                     File)

from config import SQLITE_CONNECTION_PATH,RECENT_MESSAGES_LIMIT
from db.database import get_connection
from db.crud import (create_set, 
                     list_sets, 
                     get_message_count, 
                     add_document, 
                     list_documents,
                     delete_documents_by_set,
                     delete_messages_by_set,
                     delete_set,
                     get_latest_messages)
from vectorstore.qdrant_client import get_qdrant_client
from vectorstore.collections import (create_set_collections, 
                                     get_collection_names, 
                                     delete_set_collections)
from vectorstore.ingest import (prepare_chunks, 
                                embed_and_upsert_chunks)
from agent.chat import chat as run_chat

router = APIRouter()

MAX_CHUNKS = 150

_qdrant_client = get_qdrant_client()


def _get_db_connection():
    """Fresh SQLite connection per request, closed at the end of the request."""
    return get_connection(path=SQLITE_CONNECTION_PATH)


def _set_exists(connection, set_id: int) -> bool:
    sets = list_sets(connection=connection)
    return any(row[0] == set_id for row in sets)


@router.post("/sets")
def create_new_set(payload: dict):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="'name' is required")

    connection = _get_db_connection()
    try:
        set_id = create_set(connection=connection, name=name)

        try:
            create_set_collections(client=_qdrant_client, set_id=set_id)
        except Exception as e:
            
            raise HTTPException(
                status_code=500,
                detail=f"Set created in database but Qdrant collections failed: {e}",
            )

        return {"id": set_id, "name": name}
    finally:
        connection.close()


@router.get("/sets")
def get_all_sets():
    connection = _get_db_connection()
    try:
        rows = list_sets(connection=connection)
        return [
            {"id": row[0], "name": row[1], "created_at": row[2]}
            for row in rows
        ]
    finally:
        connection.close()

@router.get("/sets/{set_id}/messages")
def get_set_messages(set_id:int):
    connection=_get_db_connection()
    try:
        if not _set_exists(connection=connection,set_id=set_id):
            raise HTTPException(status_code=404,detail=f"Set {set_id} not found")

        rows=get_latest_messages(connection=connection,set_id=set_id,n=RECENT_MESSAGES_LIMIT)
        return [
            {
                "role":role,
                "content":content
            }
            for role,content in rows
        ]
    finally:
        connection.close()
        
@router.post("/sets/{set_id}/documents")
def upload_document(set_id: int, file: UploadFile = File(...)):
    connection = _get_db_connection()
    try:
        if not _set_exists(connection=connection, set_id=set_id):
            raise HTTPException(status_code=404, detail=f"Set {set_id} not found")
    finally:
        connection.close()

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        new_chunks = prepare_chunks(tmp_path)

        docs_name, _ = get_collection_names(set_id)
        current_count = _qdrant_client.count(docs_name).count

        if current_count + len(new_chunks) > MAX_CHUNKS:
            os.remove(tmp_path)
            tmp_path = None
            raise HTTPException(
                status_code=400,
                detail=f"This set has reached its capacity ({MAX_CHUNKS} chunks). Start a new set for additional material.",
            )

        embed_and_upsert_chunks(
            client=_qdrant_client,
            set_id=set_id,
            chunks=new_chunks,
            filename=file.filename,
        )

        connection = _get_db_connection()
        try:
            add_document(
                connection=connection,
                set_id=set_id,
                filename=file.filename,
                chunk_count=len(new_chunks),
            )
        finally:
            connection.close()

        total_chunks = current_count + len(new_chunks)

        return {
            "status": "uploaded",
            "set_id": set_id,
            "filename": file.filename,
            "chunks_added": len(new_chunks),
            "total_chunks": total_chunks,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/sets/{set_id}/documents")
def get_set_documents(set_id: int):
    connection = _get_db_connection()
    try:
        if not _set_exists(connection=connection, set_id=set_id):
            raise HTTPException(status_code=404, detail=f"Set {set_id} not found")

        rows = list_documents(connection=connection, set_id=set_id)
        return [
            {
                "filename": row[0],
                "chunk_count": row[1],
                "uploaded_at": row[2]
            }
            for row in rows
        ]
    finally:
        connection.close()


@router.post("/sets/{set_id}/chat")
def chat_with_set(set_id: int, payload: dict):
    user_input = payload.get("message")
    if not user_input:
        raise HTTPException(status_code=400, detail="'message' is required")

    connection = _get_db_connection()
    try:
        if not _set_exists(connection=connection, set_id=set_id):
            raise HTTPException(status_code=404, detail=f"Set {set_id} not found")

        try:
            answer = run_chat(
                connection=connection,
                client=_qdrant_client,
                set_id=set_id,
                user_input=user_input,
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat failed: {e}")

        return {"answer": answer}
    finally:
        connection.close()


@router.get("/sets/{set_id}/status")
def set_status(set_id: int):
    """Small helper endpoint the frontend can use to know if a set has any
    documents/messages yet, and to show chunk-capacity usage for the set."""
    connection = _get_db_connection()
    try:
        if not _set_exists(connection=connection, set_id=set_id):
            raise HTTPException(status_code=404, detail=f"Set {set_id} not found")
        message_count = get_message_count(connection=connection, set_id=set_id)
        docs_name, _ = get_collection_names(set_id)
        chunk_count = _qdrant_client.count(docs_name).count
        return {
            "set_id": set_id,
            "message_count": message_count,
            "chunk_count": chunk_count,
            "chunk_limit": MAX_CHUNKS,
        }
    finally:
        connection.close()

@router.delete("/sets/{set_id}")
def remove_set(set_id:int):
    connection=_get_db_connection()
    try:
        if not _set_exists(connection=connection,set_id=set_id):
            raise HTTPException(status_code=404,detail=f"Set {set_id} not found")

        delete_messages_by_set(connection=connection,set_id=set_id)
        delete_documents_by_set(connection=connection,set_id=set_id)
        delete_set(connection=connection,set_id=set_id)
        try:
            delete_set_collections(client=_qdrant_client,set_id=set_id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Set Deleted in database but deletion of Qdrant collections failed: {e}",
            )
        return {"status":"deleted","set_id":set_id}
    finally:
        connection.close()