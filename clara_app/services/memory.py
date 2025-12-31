import streamlit as st
import os
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import datetime
import uuid
import time

from clara_app.constants import API_KEY, PINECONE_API_KEY

# Configuration
INDEX_NAME = "clara-memory"

_pinecone = None
_index = None

@st.cache_resource
def _get_client():
    if not PINECONE_API_KEY:
        return None
    return Pinecone(api_key=PINECONE_API_KEY)

def _get_index():
    global _index
    if _index is not None:
        return _index

    pc = _get_client()
    if not pc:
        return None
        
    # Check if index exists, create if not
    existing_indexes = pc.list_indexes().names()
    if INDEX_NAME not in existing_indexes:
        try:
            pc.create_index(
                name=INDEX_NAME,
                dimension=768, # Gemini embedding-001 dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # Wait for availability
            while not pc.describe_index(INDEX_NAME).status['ready']:
                time.sleep(1)
        except Exception as e:
            print(f"Index creation error: {e}")
            return None

    _index = pc.Index(INDEX_NAME)
    return _index

def get_embedding(text: str) -> Optional[List[float]]:
    """
    Generate an embedding using Google Gemini models/embedding-001.
    """
    if not API_KEY:
        return None
    
    try:
        # Use the 'embedding-001' model optimized for texts
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document",
            title="Clara Memory"
        )
        return result['embedding']
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def store_memory(username: str, text: str, metadata: Dict[str, Any]):
    """
    Store a text memory with associated metadata in Pinecone.
    """
    if not text or not username:
        return

    embedding = get_embedding(text)
    if not embedding:
        return

    index = _get_index()
    if not index:
        return
    
    # Ensure standard metadata fields
    # Pinecone metadata values can be strings, numbers, booleans, or lists of strings
    safe_metadata = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)):
            safe_metadata[k] = v
        else:
            safe_metadata[k] = str(v)
            
    safe_metadata["username"] = username
    safe_metadata["timestamp"] = datetime.datetime.now().isoformat()
    safe_metadata["text"] = text # Store text in metadata for retrieval
    
    memory_id = str(uuid.uuid4())
    
    try:
        index.upsert(
            vectors=[
                {
                    "id": memory_id,
                    "values": embedding,
                    "metadata": safe_metadata
                }
            ]
        )
    except Exception as e:
        print(f"Pinecone Store Error: {e}")

def search_memories(username: str, query_text: str, n_results: int = 5, min_relevance: float = 0.0) -> List[Dict[str, Any]]:
    """
    Search for similar memories for a specific user.
    """
    if not query_text or not username:
        return []

    # specific embedding for query
    try:
         query_embedding = genai.embed_content(
            model="models/embedding-001",
            content=query_text,
            task_type="retrieval_query"
        )['embedding']
    except Exception:
        return []

    index = _get_index()
    if not index:
        return []
    
    try:
        results = index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True,
            filter={"username": {"$eq": username}}
        )
        
        # Format results
        memories = []
        for match in results.matches:
            if match.score < min_relevance:
                continue
                
            memories.append({
                "id": match.id,
                "content": match.metadata.get("text", ""),
                "metadata": match.metadata,
                "distance": 1 - match.score # Convert similarity to distance if needed (0=close) or just keep consistency
            })
                
        return memories
    except Exception as e:
        print(f"Pinecone Search Error: {e}")
        return []

def search_patterns(username: str, tone: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Specific search to find memories with a matching emotional tone.
    Used for the 'Integrity Mirror' functionality.
    """
    index = _get_index()
    if not index:
        return []

    # Pinecone doesn't allow query without vector, so we use a "dummy" vector 
    # OR we really should be doing vector search + filter.
    # Ideally, we want "semantically relevant things that ALSO match the tone"
    # But the Integrity Mirror concept is "What other times did I feel THIS way?"
    # So actually, we want to find *recent* or *random* memories with this tone?
    
    # For now, let's just query for the MOST RECENT items with this tone.
    # Since Pinecone is vector-first, pure metadata filtering is a bit tricky without a vector.
    # We will use a zero vector or a generic "emotion" vector.
    # Better yet: We just search for the *current situation* vector, but strongly filter by tone.
    # This means: "Find me memories about THIS topic where I ALSO felt THIS way."
    
    # But if we want *pure* pattern matching (e.g. Anxiety about X matches Anxiety about Y),
    # the vector similarity of X and Y might be low.
    
    # Workaround: Use a generic query like "My feelings" to get memories, filtered by tone.
    try:
         query_embedding = genai.embed_content(
            model="models/embedding-001",
            content=f"My feelings of {tone}",
            task_type="retrieval_query"
        )['embedding']
    except:
        return []
        
    try:
        results = index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True,
            filter={
                "username": {"$eq": username},
                "tone": {"$eq": tone}
            }
        )
        
        memories = []
        for match in results.matches:
            memories.append({
                "id": match.id,
                "content": match.metadata.get("text", ""),
                "metadata": match.metadata
            })
            
        return memories
    except Exception as e:
        print(f"Pinecone Pattern Error: {e}")
        return []
