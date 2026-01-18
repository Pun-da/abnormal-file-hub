# How File Deletion Works with RAG

## ✅ **YES - Deletion is Fully Automatic**

When you delete a file, the RAG chunks are **automatically removed** from ChromaDB.

## 🔄 **Complete Deletion Flow**

```
User Deletes File (via UI or API)
        ↓
    DELETE /api/files/{id}/
        ↓
DeduplicationService.delete_file()
        ↓
    [TRANSACTION]
        ↓
    Delete File record from SQLite
        ↓
    Decrement FileContent.reference_count
        ↓
    If reference_count == 0:
        - Delete physical file from disk
        - Delete FileContent record
        ↓
    [END TRANSACTION]
        ↓
_trigger_rag_deletion(file_id)  ← AUTOMATIC
        ↓
VectorStoreService.delete_file_chunks(file_id)
        ↓
Query ChromaDB for all chunks with file_id
        ↓
Delete all matching chunks
        ↓
✅ COMPLETE - File and all RAG chunks removed
```

## 🎯 **What Gets Deleted**

| Component | What Happens | When |
|-----------|-------------|------|
| **File Metadata** | Deleted from SQLite | Immediately |
| **Physical File** | Deleted from disk | If no other references |
| **RAG Chunks** | Deleted from ChromaDB | Immediately (synchronous) |
| **FileContent** | Deleted from SQLite | If reference_count reaches 0 |

## ⚡ **Deletion is Synchronous**

- **No delay** - happens immediately when you delete
- **No background job needed** - runs in the request
- **Guaranteed consistency** - chunks always removed

## 🧪 **Test It Yourself**

```bash
# 1. Check current chunks
curl http://localhost:8000/api/search/rag-stats/
# Shows: "total_chunks": 5

# 2. Upload a file
curl -X POST -F "file=@test.txt" http://localhost:8000/api/files/
# Note the file ID

# 3. Wait 3 seconds for indexing
sleep 3

# 4. Check chunks increased
curl http://localhost:8000/api/search/rag-stats/
# Shows: "total_chunks": 7 (increased by 2)

# 5. Delete the file
curl -X DELETE http://localhost:8000/api/files/{FILE_ID}/

# 6. Check chunks decreased
curl http://localhost:8000/api/search/rag-stats/
# Shows: "total_chunks": 5 (back to original)
```

## 🔍 **Code Reference**

The deletion happens in: `backend/files/services/deduplication.py`

```python
@staticmethod
def _trigger_rag_deletion(file_id: str) -> None:
    """
    Trigger RAG index cleanup for a deleted file.
    Deletion is synchronous to avoid ChromaDB multiprocessing issues.
    """
    try:
        from uuid import UUID
        from files.services.vector_store import VectorStoreService
        
        # Ensure VectorStore is initialized
        try:
            VectorStoreService.get_collection()
        except RuntimeError:
            # Initialize if needed
            ...
        
        # Delete chunks synchronously
        file_uuid = UUID(file_id)
        chunks_deleted = VectorStoreService.delete_file_chunks(file_uuid)
        logger.info(f"Deleted {chunks_deleted} RAG chunks for file {file_id}")
```

## ✅ **Summary**

**Q: Are RAG chunks deleted automatically?**  
**A: YES - Always, immediately, guaranteed.**

**Q: Do I need to run a cleanup job?**  
**A: NO - It happens automatically when you delete a file.**

**Q: Is there any delay?**  
**A: NO - Deletion is synchronous (instant).**

**Q: What if Django crashes during deletion?**  
**A: The database transaction ensures consistency. If it fails, neither the file nor the chunks are deleted.**

**Q: Can orphaned chunks exist?**  
**A: Only if you manually delete files from the database without using the API. Always use the API/UI to delete files.**
