# # How Person 2 consumes Person 1's output:
# import json
# import chromadb
# from sentence_transformers import SentenceTransformer

# client = chromadb.PersistentClient(path="./chroma_db")
# collection = client.get_or_create_collection(name="multi_hop_rag")
# embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# with open("chunks_for_person2.jsonl", "r", encoding="utf-8") as f:
#     for line in f:
#         chunk = json.loads(line)
        
#         # 1. Person 2 passes chunk["text"] to LLM for AQ generation
#         # aqs = generate_answerable_questions(chunk["text"], hierarchy=chunk["metadata"]["section_hierarchy"])
        
#         # 2. Compute embeddings
#         embedding = embed_model.encode(chunk["text"]).tolist()
        
#         # 3. Upsert into Vector DB using Person 1's deterministic chunk ID and hash
#         collection.upsert(
#             ids=[chunk["id"]],
#             documents=[chunk["text"]],
#             embeddings=[embedding],
#             metadatas=[{
#                 "doc_name": chunk["metadata"]["doc_name"],
#                 "section": chunk["metadata"]["current_header"],
#                 "hash": chunk["metadata"]["content_hash_sha256"],
#                 "tokens": chunk["metadata"]["token_estimate"]
#             }]
#         )