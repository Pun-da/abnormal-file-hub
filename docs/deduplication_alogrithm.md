# File Deduplication Algorithm

## Core Concept

Files are identified by their **content hash** (SHA-256), not their filename. Identical content is stored only once on disk, regardless of how many times it is uploaded or under what name.

---

## Data Model

| Entity | Purpose |
|--------|---------|
| **FileContent** | Represents unique physical content. Primary key is the SHA-256 hash. Tracks `reference_count` of how many File records point to it. |
| **File** | Represents user-uploaded file metadata. Multiple File records can reference the same FileContent. |

**Relationship:** Many Files → One FileContent

---

## Upload Algorithm

1. **Extract file size** from the upload
2. **Query for existing content** with matching size (performance optimization)
3. **Compute SHA-256 hash** of the uploaded file
4. **If hash exists:** Create File record pointing to existing FileContent; increment `reference_count`; discard uploaded bytes
5. **If hash is new:** Store file to disk; create FileContent record; create File record

**Key Optimization:** Size is checked first. Hash computation (expensive) only occurs when potential duplicates by size exist, or when storing new content.

---

## Deletion Algorithm

1. Delete the File metadata record
2. Decrement `reference_count` on the associated FileContent
3. **If `reference_count` reaches 0:** Delete the physical file from disk and remove the FileContent record

---

## Scenario Matrix

| Upload Condition | Physical File Stored? | New FileContent? |
|------------------|----------------------|------------------|
| New content | Yes | Yes |
| Duplicate content (any filename) | No | No (reuse existing) |

**Filenames are irrelevant for deduplication.** Only content determines uniqueness.

---

## Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **Concurrent uploads of same content** | Database transaction ensures only one FileContent is created; second upload increments reference count |
| **Delete while upload in progress** | Transaction isolation prevents race conditions |
| **Zero-byte files** | All empty files share the same hash and single FileContent record |
| **Hash collision** | SHA-256 collision probability is negligible (~1 in 2^256); treated as same content |
| **File with same name, different content** | Creates new FileContent; both File records coexist with different content references |
| **Last reference deleted** | Physical file is removed from disk only when `reference_count` = 0 |

---

## Storage Metrics

| Metric | Definition |
|--------|------------|
| **Storage Saved** | (Total logical size of all Files) − (Physical size of all FileContent) |
| **Deduplication Ratio** | Unique FileContent count ÷ Total File count |
