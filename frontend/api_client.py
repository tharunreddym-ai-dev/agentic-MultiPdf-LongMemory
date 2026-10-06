import os

import requests
from dotenv import load_dotenv

# Loads a root .env if one exists (shared with the backend). The frontend runs
# as its own process, so this is independent of config.py's load_dotenv() call.
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

QUICK_TIMEOUT = 10       # sets list, status, documents list
UPLOAD_TIMEOUT = 120     # embedding a full document can take a while
CHAT_TIMEOUT = 120       # agent loop + a possible synchronous compaction pass
DELETE_TIMEOUT=120

class APIError(Exception):
    """Raised for every failure mode below. The message is written to be
    shown directly in the UI — never a raw traceback."""


def _handle_response(response: requests.Response):
    if response.ok:
        return response.json()

    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text or f"Backend returned status {response.status_code}"

    raise APIError(str(detail))


def _request(method: str, path: str, **kwargs):
    url = f"{BACKEND_URL}{path}"
    try:
        response = requests.request(method, url, **kwargs)
    except requests.exceptions.ConnectionError:
        raise APIError(
            f"Can't reach the backend at {BACKEND_URL}. Is the FastAPI server running?"
        )
    except requests.exceptions.Timeout:
        raise APIError("The backend took too long to respond. Please try again.")
    except requests.exceptions.RequestException as e:
        raise APIError(f"Something went wrong talking to the backend: {e}")

    return _handle_response(response)


def get_sets():
    return _request("GET", "/sets", timeout=QUICK_TIMEOUT)

def get_messages(set_id:int):
    return _request("GET",f"/sets/{set_id}/messages",timeout=QUICK_TIMEOUT)

def create_set(name: str):
    return _request("POST", "/sets", json={"name": name}, timeout=QUICK_TIMEOUT)


def get_status(set_id: int):
    return _request("GET", f"/sets/{set_id}/status", timeout=QUICK_TIMEOUT)


def get_documents(set_id: int):
    return _request("GET", f"/sets/{set_id}/documents", timeout=QUICK_TIMEOUT)


def upload_document(set_id: int, filename: str, file_bytes: bytes):
    files = {"file": (filename, file_bytes, "application/pdf")}
    return _request(
        "POST", f"/sets/{set_id}/documents", files=files, timeout=UPLOAD_TIMEOUT
    )


def send_chat(set_id: int, message: str):
    return _request(
        "POST", f"/sets/{set_id}/chat", json={"message": message}, timeout=CHAT_TIMEOUT
    )

def delete_set_completely(set_id:int):
    return _request("DELETE",f"/sets/{set_id}",timeout=DELETE_TIMEOUT)