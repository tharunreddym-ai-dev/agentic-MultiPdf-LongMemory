from fastapi import FastAPI

from config import SQLITE_CONNECTION_PATH
from db.database import get_connection
from db.database import create_table
from api.routes import router

app = FastAPI(title="MultiPDF Agentic Chat")

app.include_router(router)


@app.on_event("startup")
def on_startup():
    # Ensure tables exist before any request comes in.
    connection = get_connection(path=SQLITE_CONNECTION_PATH)
    create_table(path=SQLITE_CONNECTION_PATH)
    connection.close()
