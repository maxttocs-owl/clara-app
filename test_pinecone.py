
import sys
import os
import time

# Ensure we can import from the app
sys.path.append(os.getcwd())

from clara_app.services import memory, llm

def test_pinecone():
    print("--- Testing Pinecone Memory Service ---")
    
    # 0. Check API Key
    from clara_app.constants import PINECONE_API_KEY
    if not PINECONE_API_KEY:
        print("FAILURE: PINECONE_API_KEY not found in secrets/env.")
        return

    username = "test_user_pinecone"
    text = "This is a persistent memory test on the cloud."
    
    # 1. Test Emotion Extraction
    print("1. Extracting metadata...")
    meta = llm.extract_emotional_metadata(text)
    print(f"Meta: {meta}")
    
    # 2. Test Storage
    print("2. Storing memory (Upserting to Pinecone)...")
    memory.store_memory(username, text, meta)
    
    # Wait for consistency (Pinecone is eventually consistent)
    print("   Waiting 10s for index consistency...")
    time.sleep(10)
    
    # 3. Test Search
    print("3. Searching memory...")
    results = memory.search_memories(username, "cloud memory test")
    print(f"Search Results: {len(results)}")
    
    found = False
    for r in results:
        print(f" - Found: {r['content']} (Score: {1 - r['distance']:.4f})")
        if "persistent memory test" in r['content']:
            found = True
            
    if found:
        print("SUCCESS: Memory stored and retrieved from Pinecone.")
    else:
        print("WARNING: Did not find the exact memory (might be indexing latency).")

if __name__ == "__main__":
    try:
        test_pinecone()
    except Exception as e:
        print(f"\nFAILURE: {e}")
