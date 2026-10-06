from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import EMBEDDING_MODEL,EMBEDDING_MODEL_URL,NVIDIA_API_KEY
from uuid import uuid4
from qdrant_client.models import PointStruct
from vectorstore.collections import get_collection_names
import requests
import time
import re

chunk_size=1000
chunk_overlap=200
max_tries=3

def extract_text(file_path)->str:
    loader=PyPDFLoader(file_path)
    pdf=loader.load()

    return ''.join(page.page_content for page in pdf)

def clean_text(text:str)->str:
    text=re.sub(r'-\n',' ',text)
    text=re.sub(r'\n+',' ',text)
    text=re.sub(r'\s+',' ',text)
    text=text.strip()
    return text

def chunk_text(text)->list[str]:
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )

    chunks=splitter.split_text(text)

    return chunks

def embed_chunks(chunks,input_type)->list[list[float]]:
    headers={
        "Authorization":f"Bearer {NVIDIA_API_KEY}",
        "Content-Type":"application/json"
    }

    body={
        "model":EMBEDDING_MODEL,
        "input":chunks,
        "encoding_format":"float",
        "input_type":input_type
    }

    for attempt in range(max_tries):
        try:
            response=requests.post(url=EMBEDDING_MODEL_URL,headers=headers,json=body)
            if response.status_code!=200:
                raise Exception(f"API Error {response.text} with code {response.status_code}")
            data=response.json()

            if "data" not in data:
                raise Exception(f"Unexpected response {data}")
            
            embds=[item["embedding"] for item in data["data"]]
            return embds
        
        except Exception as e:
            if attempt==max_tries-1:
                raise e
            wait=2**attempt
            time.sleep(wait)
            print(f"Attempt- {attempt+1} Failed, Retrying in {wait} Seconds...")

def prepare_chunks(file_path)->list[str]:
    text=extract_text(file_path=file_path)
    cleaned_text=clean_text(text=text)
    chunks=chunk_text(text=cleaned_text)
    return chunks

def embed_and_upsert_chunks(client,set_id,chunks,filename)->None:
    embeddings=embed_chunks(chunks=chunks,input_type="passage")
    docs_name,_=get_collection_names(set_id=set_id)

    points=[]

    for i,(chunk,embedding) in enumerate(zip(chunks,embeddings)):
        points.append(PointStruct(
            id=str(uuid4()),
            vector=embedding,
            payload={
                "text":chunk,
                "source":filename,
                "chunk_index":i
            }
        ))

    client.upsert(
        collection_name=docs_name,
        points=points
    )
