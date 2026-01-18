# Shared Data Contract

## Overview

This document defines the shared data contract for the Abnormal File Vault. The contract consists of two Django models that serve as the foundation for all features.

**Location:** `backend/contracts/`

**Modification Policy:** This folder is symlinked across worktrees. DO NOT MODIFY without explicit approval.

---

## Models

### FileContent

Represents unique physical file content using content-addressable storage.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `hash` | CharField(64) | **Primary Key** | SHA-256 hash of file content |
| `file` | FileField | Required | Path to physical file |
| `size` | BigIntegerField | Required | File size in bytes |
| `reference_count` | PositiveIntegerField | Default: 1 | Number of File records referencing this content |
| `created_at` | DateTimeField | Auto | When content was first uploaded |

**Storage Path:** `cas/{hash[0:2]}/{hash[2:4]}/{hash}.{ext}`

### File

Represents user-uploaded file metadata. Multiple Files can reference the same FileContent.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | **Primary Key**, Auto-generated | Unique file identifier |
| `original_filename` | CharField(255) | Required | Filename as uploaded by user |
| `file_type` | CharField(100) | Required | MIME type |
| `uploaded_at` | DateTimeField | Auto | When file was uploaded |
| `content` | ForeignKey | Required, PROTECT | Reference to FileContent |

**Properties:**
- `size` → Returns `content.size`
- `file` → Returns `content.file`

---

## Relationships

```
┌─────────────┐         ┌───────────────┐
│    File     │ N ──► 1 │  FileContent  │
├─────────────┤         ├───────────────┤
│ id (PK)     │         │ hash (PK)     │
│ filename    │         │ file          │
│ file_type   │         │ size          │
│ uploaded_at │         │ ref_count     │
│ content(FK) │────────►│ created_at    │
└─────────────┘         └───────────────┘
```

**Cardinality:** Many Files → One FileContent (deduplication)

**On Delete:** PROTECT — FileContent cannot be deleted while Files reference it

---

## Database Indexes

| Model | Index | Fields | Purpose |
|-------|-------|--------|---------|
| FileContent | `filecontent_size_idx` | `size` | Size-based duplicate detection |
| File | `file_filename_idx` | `original_filename` | Filename search |
| File | `file_type_idx` | `file_type` | Type filtering |
| File | `file_uploaded_idx` | `uploaded_at` | Date filtering/sorting |
| File | `file_type_date_idx` | `file_type`, `uploaded_at` | Combined filtering |

---

## API Response Format

The serializer maintains backward compatibility while exposing new fields:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `id` | UUID | File.id | Unique identifier |
| `file` | URL | FileContent.file | Download URL |
| `original_filename` | String | File.original_filename | User-provided name |
| `file_type` | String | File.file_type | MIME type |
| `size` | Integer | FileContent.size | Size in bytes |
| `uploaded_at` | DateTime | File.uploaded_at | Upload timestamp |
| `content_hash` | String | FileContent.hash | SHA-256 hash |
| `is_duplicate` | Boolean | Computed | True if reference_count > 1 |

---

## Usage by Features

### Deduplication Feature

**Reads:**
- FileContent.hash (check for existing content)
- FileContent.size (size-first optimization)

**Writes:**
- FileContent (create on new content)
- FileContent.reference_count (increment on duplicate)
- File (create metadata record)

### Search & Filtering Feature

**Reads:**
- File.original_filename (search)
- File.file_type (filter)
- File.uploaded_at (filter)
- FileContent.size via join (filter)

**Writes:** None (read-only)

### RAG Feature (Phase 2)

**Reads:**
- File.id (reference for ChromaDB)
- File.original_filename, file_type (metadata)
- FileContent.file (content extraction)

**Writes:** External only (ChromaDB)

---

## Invariants

1. **Hash Uniqueness:** FileContent.hash is unique (primary key)
2. **Reference Integrity:** File.content always points to valid FileContent
3. **Reference Count:** FileContent.reference_count equals count of referencing Files
4. **No Orphans:** FileContent with reference_count=0 should be deleted
5. **Immutable Content:** FileContent.file and FileContent.hash never change after creation

---

## Worktree Symlink Setup

After cloning to a new worktree:

```bash
# Remove the contracts folder (if copied)
rm -rf backend/contracts

# Symlink to main worktree
ln -s /path/to/main/backend/contracts backend/contracts
```

This ensures all worktrees share the same contract definition and migrations.
