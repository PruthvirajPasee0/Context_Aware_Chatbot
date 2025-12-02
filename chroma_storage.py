"""
ChromaDB storage module for chat persistence
Handles saving and loading user-specific chat sessions
"""

import os
import json
from typing import Dict, Tuple, Optional
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ChromaDB client (initialized lazily)
_chroma_client = None
_collection = None

def init_chromadb_client():
    """Initialize ChromaDB client with credentials from environment"""
    global _chroma_client, _collection
    
    if _chroma_client is not None:
        return _chroma_client, _collection
    
    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    database = os.getenv("CHROMA_DATABASE")
    host = os.getenv("CHROMA_HOST")
    
    if not all([api_key, tenant, database]):
        error_msg = "ChromaDB credentials missing:"
        if not api_key:
            error_msg += " CHROMA_API_KEY"
        if not tenant:
            error_msg += " CHROMA_TENANT"
        if not database:
            error_msg += " CHROMA_DATABASE"
        raise ValueError(error_msg)
    
    print(f"[ChromaDB] Connecting to tenant: {tenant}, database: {database}")
    
    try:
        # Initialize ChromaDB client with correct settings
        _chroma_client = chromadb.CloudClient(
            api_key='ck-6B7Drqjo1AsP8pCLdnt7vGFEC1soT3RrBTTCPKdepWcF',
            tenant='ff246904-802d-4ad6-9bd8-f131482eb998',
            database='MemoryBot'
            )
        
        # Test connection by getting heartbeat
        try:
            heartbeat = _chroma_client.heartbeat()
            print(f"[ChromaDB] Connection successful! Heartbeat: {heartbeat}")
        except Exception as hb_error:
            print(f"[ChromaDB] Warning: Heartbeat failed: {hb_error}")
        
        # Get or create collection for user chats
        _collection = _chroma_client.get_or_create_collection(
            name="user_chats",
            metadata={"description": "User chat sessions"}
        )
        
        print(f"[ChromaDB] Collection 'user_chats' ready")
        
        return _chroma_client, _collection
        
    except Exception as e:
        print(f"[ChromaDB] CRITICAL ERROR during initialization: {str(e)}")
        print(f"[ChromaDB] Error type: {type(e).__name__}")
        raise

def save_user_chats(user_id: int, chat_sessions: Dict, current_chat_id: str) -> bool:
    """
    Save all chat sessions for a user to ChromaDB
    
    Args:
        user_id: User ID
        chat_sessions: Dictionary of chat sessions
        current_chat_id: Currently active chat ID
    
    Returns:
        bool: Success status
    """
    try:
        print(f"[ChromaDB] Saving chats for user {user_id}...")
        client, collection = init_chromadb_client()
        
        # Delete existing chats for this user
        try:
            existing_ids = collection.get(
                where={"user_id": str(user_id)}
            )
            if existing_ids and existing_ids['ids']:
                print(f"[ChromaDB] Deleting {len(existing_ids['ids'])} existing chats for user {user_id}")
                collection.delete(ids=existing_ids['ids'])
        except Exception as del_error:
            print(f"[ChromaDB] Note: No existing chats to delete or error: {del_error}")
        
        # Prepare documents for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for chat_id, chat_data in chat_sessions.items():
            doc_id = f"user_{user_id}_chat_{chat_id}"
            ids.append(doc_id)
            
            # Serialize messages to JSON string
            documents.append(json.dumps(chat_data['messages']))
            
            # Metadata
            metadatas.append({
                "user_id": str(user_id),
                "chat_id": chat_id,
                "title": chat_data.get('title', 'New Chat'),
                "created_at": chat_data.get('created_at', ''),
                "is_current": str(chat_id == current_chat_id)
            })
        
        # Add to collection if there are chats
        if ids:
            print(f"[ChromaDB] Adding {len(ids)} chats to collection...")
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            print(f"[ChromaDB] Successfully saved {len(ids)} chats for user {user_id}")
        else:
            print(f"[ChromaDB] No chats to save for user {user_id}")
        
        return True
        
    except Exception as e:
        print(f"[ChromaDB] ERROR saving chats for user {user_id}: {str(e)}")
        return False

def load_user_chats(user_id: int) -> Tuple[Dict, Optional[str]]:
    """
    Load all chat sessions for a user from ChromaDB
    
    Args:
        user_id: User ID
    
    Returns:
        Tuple of (chat_sessions dict, current_chat_id)
    """
    try:
        print(f"[ChromaDB] Loading chats for user {user_id}...")
        client, collection = init_chromadb_client()
        
        # Query all chats for this user
        results = collection.get(
            where={"user_id": str(user_id)}
        )
        
        if not results or not results['ids']:
            print(f"[ChromaDB] No existing chats found for user {user_id}")
            return {}, None
        
        print(f"[ChromaDB] Found {len(results['ids'])} chats for user {user_id}")
        
        # Reconstruct chat sessions
        chat_sessions = {}
        current_chat_id = None
        
        for i, doc_id in enumerate(results['ids']):
            metadata = results['metadatas'][i]
            messages_json = results['documents'][i]
            
            chat_id = metadata['chat_id']
            
            chat_sessions[chat_id] = {
                'messages': json.loads(messages_json),
                'title': metadata['title'],
                'created_at': metadata['created_at']
            }
            
            if metadata.get('is_current') == 'True':
                current_chat_id = chat_id
        
        print(f"[ChromaDB] Successfully loaded {len(chat_sessions)} chats for user {user_id}")
        return chat_sessions, current_chat_id
        
    except Exception as e:
        print(f"[ChromaDB] ERROR loading chats for user {user_id}: {str(e)}")
        print(f"[ChromaDB] Error type: {type(e).__name__}")
        return {}, None

def delete_user_chat(user_id: int, chat_id: str) -> bool:
    """
    Delete a specific chat for a user
    
    Args:
        user_id: User ID
        chat_id: Chat ID to delete
    
    Returns:
        bool: Success status
    """
    try:
        client, collection = init_chromadb_client()
        
        doc_id = f"user_{user_id}_chat_{chat_id}"
        collection.delete(ids=[doc_id])
        
        return True
        
    except Exception as e:
        print(f"Error deleting chat from ChromaDB: {e}")
        return False
