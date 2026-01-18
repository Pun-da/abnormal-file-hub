# Abnormal File Vault - RAG Semantic Search System

A production-ready file management system with AI-powered semantic search capabilities.

## 🚀 Quick Start

### Start Everything
```bash
./start.sh
```

This starts:
- ✅ Redis (message broker)
- ✅ Django Backend (API + RAG)
- ✅ Celery Worker (background indexing)
- ✅ React Frontend (UI)

### Stop Everything
```bash
./stop.sh
```

### Access
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api

## 📦 Features

### Core Features
- **File Upload/Download** with automatic deduplication
- **Content-Addressable Storage** (CAS) - identical files stored once
- **Semantic Search** - natural language queries across file contents
- **Background Indexing** - async processing for large files
- **Monitoring Dashboard** - query stats and system metrics

### RAG Search Capabilities
- **Supported File Types**: PDF, TXT, MD, CSV, JSON, XML
- **Smart Chunking**: Token-aware with 500 token chunks, 50 token overlap
- **Vector Search**: ChromaDB with 384-dimensional embeddings
- **Similarity Scoring**: Cosine similarity with configurable threshold
- **Auto-Deletion**: RAG chunks automatically removed when files deleted

## 📝 How to Use

### 1. Upload Files
- Go to **Files** tab
- Drag & drop or click to upload
- Large files are indexed in the background (watch Celery logs)

### 2. Search with Natural Language
- Go to **Semantic Search** tab
- Enter your query: "machine learning algorithms" or "financial data for Q4"
- Adjust threshold (0.3 = broad results, 0.7 = exact matches)
- Adjust max results (1-10)

### 3. View Results
- Ranked by relevance (similarity score)
- See matched chunks with context
- Click to download source file

### 4. Monitor System
- Go to **Monitoring** tab
- View query stats, popular searches, system health
- Track indexed chunks and storage usage

## 🛠️ Technical Stack

- **Backend**: Django + DRF
- **Frontend**: React + TypeScript + TanStack Query
- **Vector DB**: ChromaDB
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Task Queue**: Celery + Redis
- **Storage**: Content-Addressable Storage (CAS)

## 📂 Project Structure

```
.
├── backend/
│   ├── files/               # Main app
│   │   ├── services/        # RAG services (embeddings, chunking, etc)
│   │   ├── tasks.py         # Celery tasks
│   │   └── rag_views.py     # RAG API endpoints
│   ├── core/                # Django config
│   ├── data/                # SQLite + ChromaDB
│   └── media/cas/           # File storage
├── frontend/
│   └── src/
│       ├── components/      # React components
│       └── services/        # API clients
├── docs/                    # Architecture docs
├── start.sh                 # Start all services
├── stop.sh                  # Stop all services
└── DELETION_FLOW.md         # How deletion works
```

## 🔧 Advanced

### Check RAG Stats
```bash
curl http://localhost:8000/api/search/rag-stats/
```

### Reindex All Files
```bash
cd backend
source venv/bin/activate
python manage.py init_rag --reindex
```

### Reset Vector Database (Delete All Chunks)
```bash
cd backend
source venv/bin/activate
python manage.py init_rag --reset
```

### View Logs
```bash
tail -f logs/django.log
tail -f logs/celery.log
tail -f logs/frontend.log
```

## 🧪 Testing

1. **Upload test files**:
   ```bash
   cd backend/test_files
   # Upload via UI or:
   curl -X POST -F "file=@machine_learning.txt" http://localhost:8000/api/files/
   ```

2. **Wait for indexing** (~3 seconds)

3. **Search**:
   - Query: "neural networks and deep learning"
   - Expected: Finds relevant chunks from ML files

4. **Delete file** via UI

5. **Verify chunks removed**:
   ```bash
   curl http://localhost:8000/api/search/rag-stats/
   # total_chunks should decrease
   ```

## ❓ FAQ

### Do RAG chunks get deleted when I delete files?
**YES** - Automatically and immediately. See `DELETION_FLOW.md` for details.

### Why is my search returning no results?
- Lower the threshold (try 0.3 instead of 0.5)
- Check if files are indexed: visit Stats in Semantic Search tab
- Wait a few seconds after upload for large files

### How do I know if indexing is done?
- Check Celery logs: `tail -f logs/celery.log`
- Or check stats: `/api/search/rag-stats/`

### Can I use this in production?
Yes! Use Docker Compose for deployment:
```bash
docker-compose up -d
```

## 📄 License

MIT

## 🤝 Contributing

PRs welcome! This system demonstrates:
- Production-grade RAG implementation
- Clean architecture with services layer
- Async background processing
- Content-addressable storage
- Comprehensive testing

---

**Need help?** Check `DELETION_FLOW.md` for deletion details, or read `docs/` for architecture diagrams.
