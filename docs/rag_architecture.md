# RAG System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         File Vault RAG System                        │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │────────▶│   Django     │────────▶│   ChromaDB   │
│   (React)    │         │   Backend    │         │   (Vectors)  │
└──────────────┘         └──────────────┘         └──────────────┘
                                │
                                │
                         ┌──────▼──────┐
                         │    Redis    │
                         │  (Broker)   │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │   Celery    │
                         │   Worker    │
                         └─────────────┘
```

## Component Interaction

### 1. File Upload Flow

```
User Uploads File
       │
       ▼
┌─────────────────┐
│  File Upload    │
│  API Endpoint   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Deduplication   │◀──── Compute SHA-256 Hash
│    Service      │
└────────┬────────┘
         │
         ├─────────────────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│  Store File     │      │  Check File     │
│  (CAS Path)     │      │  Size           │
└─────────────────┘      └────────┬────────┘
                                  │
                         ┌────────┴────────┐
                         │                 │
                    < 1MB                ≥ 1MB
                         │                 │
                         ▼                 ▼
                ┌─────────────────┐  ┌─────────────────┐
                │  Sync Indexing  │  │ Queue Celery    │
                │  (Immediate)    │  │ Task (Async)    │
                └────────┬────────┘  └────────┬────────┘
                         │                    │
                         └────────┬───────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  RAG Indexing   │
                         │  Pipeline       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   ChromaDB      │
                         │  (Vector Store) │
                         └─────────────────┘
```

### 2. RAG Indexing Pipeline

```
File Content
     │
     ▼
┌─────────────────┐
│ Text Extraction │
│  - PDF: PyPDF2  │
│  - Text: UTF-8  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Text Chunking  │
│  - 500 tokens   │
│  - 50 overlap   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Embedding     │
│  Generation     │
│  (MiniLM-L6)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Store Vectors  │
│  + Metadata     │
│  in ChromaDB    │
└─────────────────┘
```

### 3. Semantic Search Flow

```
User Query: "machine learning algorithms"
              │
              ▼
     ┌─────────────────┐
     │  Validate Query │
     │  (3-500 chars)  │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Generate Query │
     │   Embedding     │
     │  (384-dim)      │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  ChromaDB       │
     │  Similarity     │
     │  Search         │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Get Top-K      │
     │  Chunks         │
     │  (with scores)  │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Group by       │
     │  File ID        │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Aggregate      │
     │  Scores         │
     │  (max/mean/wgt) │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Return Ranked  │
     │  File List      │
     │  + Previews     │
     └─────────────────┘
```

### 4. File Deletion Flow

```
User Deletes File
       │
       ▼
┌─────────────────┐
│  Delete File    │
│  API Endpoint   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Deduplication   │
│    Service      │
└────────┬────────┘
         │
         ├─────────────────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│  Delete File    │      │  Queue Celery   │
│  Metadata       │      │  Deletion Task  │
└─────────────────┘      └────────┬────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│  Decrement      │      │  Delete Vectors │
│  Ref Count      │      │  from ChromaDB  │
└────────┬────────┘      └─────────────────┘
         │
    ref_count = 0?
         │
         ▼
┌─────────────────┐
│  Delete         │
│  Physical File  │
└─────────────────┘
```

## Data Models

### File Record (SQLite)
```
┌─────────────────────────────┐
│          File               │
├─────────────────────────────┤
│ id: UUID                    │
│ original_filename: String   │
│ file_type: String           │
│ uploaded_at: DateTime       │
│ content_id: FK              │
└─────────────────────────────┘
         │
         │ Many-to-One
         ▼
┌─────────────────────────────┐
│       FileContent           │
├─────────────────────────────┤
│ id: UUID                    │
│ hash: String (SHA-256)      │
│ size: Integer               │
│ file: FileField             │
│ reference_count: Integer    │
└─────────────────────────────┘
```

### Vector Record (ChromaDB)
```
┌─────────────────────────────┐
│      Chunk Embedding        │
├─────────────────────────────┤
│ id: "file_id_chunk_index"   │
│ embedding: [384 floats]     │
│ document: String (text)     │
│ metadata:                   │
│   - file_id: UUID           │
│   - chunk_index: Integer    │
│   - file_name: String       │
│   - file_type: String       │
└─────────────────────────────┘
```

## Service Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Deduplication    │  │ Text Extraction  │               │
│  │ Service          │  │ Service          │               │
│  │ - Hash compute   │  │ - PDF extract    │               │
│  │ - Ref counting   │  │ - Text extract   │               │
│  │ - RAG triggers   │  │ - Encoding detect│               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Chunking         │  │ Embedding        │               │
│  │ Service          │  │ Service          │               │
│  │ - Token split    │  │ - Model load     │               │
│  │ - Overlap        │  │ - Batch encode   │               │
│  │ - Boundaries     │  │ - 384-dim output │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  ┌──────────────────┐                                      │
│  │ Vector Store     │                                      │
│  │ Service          │                                      │
│  │ - ChromaDB init  │                                      │
│  │ - CRUD ops       │                                      │
│  │ - Similarity     │                                      │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Task Queue Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Celery Tasks                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  index_file_for_rag                          │          │
│  │  - Extract text                              │          │
│  │  - Chunk text                                │          │
│  │  - Generate embeddings                       │          │
│  │  - Store in ChromaDB                         │          │
│  │  - Auto-retry on failure (max 3)             │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  delete_file_from_rag                        │          │
│  │  - Query ChromaDB by file_id                 │          │
│  │  - Delete all chunks                         │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  reindex_all_files                           │          │
│  │  - Get all files from DB                     │          │
│  │  - Queue indexing for each                   │          │
│  │  - Return statistics                         │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ Uses
                           ▼
                  ┌─────────────────┐
                  │     Redis       │
                  │  Message Broker │
                  │  Result Backend │
                  └─────────────────┘
```

## API Layer

```
┌─────────────────────────────────────────────────────────────┐
│                      API Endpoints                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  File Management:                                           │
│  ┌─────────────────────────────────────────┐               │
│  │ GET    /api/files/                      │               │
│  │ POST   /api/files/                      │               │
│  │ GET    /api/files/{id}/                 │               │
│  │ DELETE /api/files/{id}/                 │               │
│  │ GET    /api/files/storage-metrics/      │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
│  RAG Semantic Search:                                       │
│  ┌─────────────────────────────────────────┐               │
│  │ GET    /api/search/semantic/            │               │
│  │        ?q=<query>                       │               │
│  │        &top_k=10                        │               │
│  │        &threshold=0.5                   │               │
│  │        &aggregation=max                 │               │
│  │                                         │               │
│  │ GET    /api/search/rag-stats/           │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
│  Monitoring:                                                │
│  ┌─────────────────────────────────────────┐               │
│  │ GET    /api/stats/storage/              │               │
│  │ GET    /api/stats/query-logs/           │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Development
```
┌──────────────┐
│  Terminal 1  │  python manage.py runserver
└──────────────┘
┌──────────────┐
│  Terminal 2  │  ./start_celery.sh
└──────────────┘
┌──────────────┐
│  Terminal 3  │  redis-server
└──────────────┘
```

### Docker Compose
```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Frontend   │  │   Backend    │  │    Redis     │     │
│  │   (React)    │  │   (Django)   │  │   (Broker)   │     │
│  │   Port 3000  │  │   Port 8000  │  │   Port 6379  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│                    ┌──────────────┐                        │
│                    │   Celery     │                        │
│                    │   Worker     │                        │
│                    └──────────────┘                        │
│                                                             │
│  Shared Volumes:                                            │
│  - media_data (file storage)                                │
│  - chromadb_data (vector store)                             │
│  - redis_data (persistence)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

### Indexing Performance
```
File Size     │ Processing Time │ Method
──────────────┼─────────────────┼──────────────
< 100KB       │ < 1 second      │ Synchronous
100KB - 1MB   │ 1-5 seconds     │ Synchronous
1MB - 10MB    │ 5-30 seconds    │ Asynchronous
> 10MB        │ 30+ seconds     │ Asynchronous
```

### Search Performance
```
Operation              │ Typical Time
───────────────────────┼──────────────
Query embedding        │ 50-100ms
Vector search (1K docs)│ 10-50ms
Vector search (10K docs)│ 50-200ms
Result aggregation     │ 5-10ms
Total search time      │ 100-300ms
```

### Storage Requirements
```
Component         │ Size per File
──────────────────┼──────────────
File content      │ Original size
Embeddings        │ ~1.5KB per chunk
Metadata          │ ~0.5KB per chunk
Total overhead    │ ~2KB per chunk
                  │ (~2MB per 1000 chunks)
```

## Security Considerations

1. **Input Validation**: Query length limits (3-500 chars)
2. **File Type Validation**: Only supported types indexed
3. **Size Limits**: 10MB max upload (configurable)
4. **Sandboxed Execution**: Celery tasks isolated
5. **No Code Execution**: Text extraction only, no eval()
6. **CORS Configuration**: Restrict in production
7. **Rate Limiting**: Consider adding for search endpoint

## Monitoring Points

1. **Celery Task Queue**: Monitor queue length
2. **Redis Memory**: Monitor memory usage
3. **ChromaDB Size**: Monitor disk usage
4. **Search Latency**: Monitor response times
5. **Indexing Success Rate**: Monitor task failures
6. **Model Loading Time**: Monitor cold start
7. **Chunk Count**: Monitor growth rate
