"""
Vector store module for PDF processing and RAG
Optimized for production deployment
"""

import os
import tempfile
from typing import List, Dict, Tuple
from datetime import datetime
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Global variables
_chroma_client = None
_files_collection = None
_embedding_model = None

def init_vector_store():
    """Initialize ChromaDB client and files collection"""
    global _chroma_client, _files_collection
    
    if _chroma_client is not None:
        return _chroma_client, _files_collection
    
    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    database = os.getenv("CHROMA_DATABASE")
    
    if not all([api_key, tenant, database]):
        raise ValueError("ChromaDB credentials missing in .env file")
    
    try:
        _chroma_client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )
        
        _files_collection = _chroma_client.get_or_create_collection(
            name="userFiles",
            metadata={"description": "User uploaded file chunks"}
        )
        
        return _chroma_client, _files_collection
        
    except Exception as e:
        print(f"[VectorStore] Init error: {str(e)}")
        raise

def get_embedding_model():
    """Get or initialize embedding model"""
    global _embedding_model
    
    if _embedding_model is None:
        _embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    return _embedding_model

def process_and_store_pdf(user_id: int, uploaded_file, filename: str) -> Tuple[bool, str]:
    """Process and store PDF chunks"""
    try:
        client, collection = init_vector_store()
        embedding_model = get_embedding_model()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
            
            if not pages:
                return False, "PDF appears to be empty or corrupt"
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
            )
            
            chunks = text_splitter.split_documents(pages)
            
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for idx, chunk in enumerate(chunks):
                doc_id = f"user_{user_id}_file_{filename}_chunk_{idx}"
                ids.append(doc_id)
                documents.append(chunk.page_content)
                embeddings.append(embedding_model.encode(chunk.page_content).tolist())
                
                metadatas.append({
                    "user_id": str(user_id),
                    "filename": filename,
                    "chunk_index": str(idx),
                    "total_chunks": str(len(chunks)),
                    "uploaded_at": datetime.now().isoformat(),
                    "page_number": str(chunk.metadata.get('page', 0) + 1)
                })
            
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            return True, f"Successfully processed {len(pages)} pages into {len(chunks)} chunks"
            
        finally:
            os.unlink(tmp_path)
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def retrieve_relevant_context(user_id: int, query: str, top_k: int = 3) -> Tuple[bool, List[Dict]]:
    """Retrieve relevant context from uploaded files"""
    try:
        client, collection = init_vector_store()
        embedding_model = get_embedding_model()
        
        query_embedding = embedding_model.encode(query).tolist()
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": str(user_id)}
        )
        
        if not results or not results['ids'] or not results['ids'][0]:
            return False, []
        
        contexts = []
        for i, doc_id in enumerate(results['ids'][0]):
            distance = results['distances'][0][i]
            similarity = 1 / (1 + distance)
            
            if similarity > 0.4:
                contexts.append({
                    'text': results['documents'][0][i],
                    'filename': results['metadatas'][0][i]['filename'],
                    'page': results['metadatas'][0][i]['page_number'],
                    'similarity': similarity
                })
        
        return (True, contexts) if contexts else (False, [])
            
    except Exception as e:
        return False, []

def get_user_files(user_id: int) -> List[str]:
    """Get list of all files uploaded by a user"""
    try:
        client, collection = init_vector_store()
        
        results = collection.get(
            where={"user_id": str(user_id)}
        )
        
        if not results or not results['metadatas']:
            return []
        
        filenames = set()
        for metadata in results['metadatas']:
            filenames.add(metadata['filename'])
        
        return sorted(list(filenames))
        
    except Exception as e:
        return []

def delete_user_file(user_id: int, filename: str) -> Tuple[bool, str]:
    """Delete all chunks of a specific file"""
    try:
        client, collection = init_vector_store()
        
        results = collection.get(
            where={
                "$and": [
                    {"user_id": {"$eq": str(user_id)}},
                    {"filename": {"$eq": filename}}
                ]
            }
        )
        
        if not results or not results['ids']:
            return False, "File not found"
        
        num_chunks = len(results['ids'])
        collection.delete(ids=results['ids'])
        
        return True, f"Successfully deleted {filename}"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def format_context_for_llm(contexts: List[Dict]) -> str:
    """Format retrieved contexts for LLM prompt"""
    if not contexts:
        return ""
    
    formatted = "**Relevant information from your uploaded documents:**\n\n"
    
    for i, ctx in enumerate(contexts, 1):
        formatted += f"**Source {i}** (from {ctx['filename']}, page {ctx['page']}):\n"
        formatted += f"{ctx['text']}\n\n"
    
    return formatted
