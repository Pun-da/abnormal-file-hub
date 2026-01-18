# RAG Semantic Search Algorithm

## Overview

The RAG (Retrieval-Augmented Generation) system enables natural language queries against file contents. Users can search semantically (e.g., "Q4 earnings attributed to AI") rather than by exact keywords.

---

## Supported File Types

| Type | Extensions | Extraction Method |
|------|------------|-------------------|
| Plain text | `.txt`, `.md`, `.csv`, `.json`, `.xml` | Direct read |
| PDF documents | `.pdf` | PDF text extraction library |

Unsupported file types are stored but not indexed for semantic search.

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Text extraction | PyPDF2 / pdfplumber | Extract text from PDFs |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) | Convert text to 384-dim vectors |
| Vector store | ChromaDB | Persistent local vector storage |
| Similarity | Cosine similarity | Rank results by relevance |

---

## Ingestion Pipeline

### Flow

```
File Upload
    ↓
Check file type supported?
    ↓ Yes                    ↓ No
Extract text content     Skip indexing (file still stored)
    ↓
Chunk text into segments (~500 tokens each)
    ↓
Generate embedding for each chunk
    ↓
Store in ChromaDB with metadata (file_id, chunk_index)
```

### Chunking Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Chunk size | ~500 tokens | Balance between context and specificity |
| Overlap | ~50 tokens | Preserve context across chunk boundaries |
| Minimum chunk | 50 tokens | Skip very short segments |

### Metadata Stored Per Chunk

| Field | Purpose |
|-------|---------|
| `file_id` | Reference back to File record |
| `chunk_index` | Position within document |
| `file_name` | Original filename for display |
| `file_type` | MIME type |

---

## Semantic Search Flow

### Flow

```
Natural Language Query
    ↓
Generate query embedding (same model as ingestion)
    ↓
ChromaDB similarity search (cosine distance)
    ↓
Retrieve top-K chunks with scores
    ↓
Group by file_id, aggregate scores
    ↓
Return ranked file list with relevance scores
```

### Result Ranking

| Method | Description |
|--------|-------------|
| **Max score** | File score = highest chunk score |
| **Mean score** | File score = average of all matching chunk scores |
| **Weighted** | Recent chunks or title chunks weighted higher |

Default: **Max score** — if any chunk matches well, the file is relevant.

---

## Query Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `q` | Natural language query | Required |
| `top_k` | Maximum results | 10 |
| `threshold` | Minimum similarity score (0-1) | 0.5 |

---

## Response Format

| Field | Description |
|-------|-------------|
| `query` | Original query text |
| `results` | Array of matching files |
| `results[].file_id` | File identifier |
| `results[].file_name` | Original filename |
| `results[].score` | Relevance score (0-1) |
| `results[].matched_chunks` | Number of matching chunks |
| `results[].preview` | Best matching text snippet |

---

## Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **Unsupported file type** | Store file normally; skip vector indexing; log skip reason |
| **Empty file content** | Skip indexing; file remains searchable by metadata filters |
| **PDF with images only (no text)** | Extract fails gracefully; file not indexed |
| **Very large file (>10MB text)** | Chunk normally; may produce many chunks |
| **File with non-UTF8 encoding** | Attempt detection; fallback to skip with warning |
| **Corrupt PDF** | Skip indexing; log error; file still accessible |
| **Query too short** | Require minimum 3 characters |
| **Query too long** | Truncate to 500 characters |
| **No results above threshold** | Return empty results with 200 OK |
| **File deleted** | Remove all associated chunks from ChromaDB |
| **File updated/replaced** | Delete old chunks; re-index new content |
| **ChromaDB unavailable** | Degrade gracefully; return error for semantic search only |
| **Duplicate file content** | Each File gets own chunks (different file_id); supports per-file search |

---

## Synchronization

### On File Upload
1. Store file in filesystem
2. Create File record in SQLite
3. If supported type: extract → chunk → embed → store vectors

### On File Delete
1. Delete chunks from ChromaDB (by file_id)
2. Delete File record from SQLite
3. Handle FileContent reference counting (deduplication)

### Consistency
- Vector indexing is **asynchronous** — file upload succeeds even if indexing fails
- Failed indexing is logged and can be retried
- Semantic search excludes files not yet indexed

---

## Performance Considerations

| Scenario | Recommendation |
|----------|----------------|
| Large PDF (100+ pages) | Process in background job |
| Many concurrent uploads | Queue indexing tasks |
| ChromaDB growth | Monitor collection size; consider sharding |
| Cold start | ChromaDB loads from disk; first query may be slower |
| Embedding computation | Batch multiple chunks for efficiency |

---

## Limitations

| Limitation | Impact |
|------------|--------|
| Text-only extraction | Images, charts, tables in PDFs not searchable |
| English-optimized model | Other languages may have lower accuracy |
| No OCR | Scanned PDFs without text layer not indexed |
| Local embeddings | Quality slightly lower than cloud models (acceptable trade-off) |
