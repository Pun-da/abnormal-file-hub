# Monitoring Feature Specification

## Overview

The monitoring feature provides visibility into system performance and storage efficiency through REST API endpoints. It covers two domains:

1. **Storage Monitoring** — Track deduplication savings
2. **Query Monitoring** — Track search/filter performance and failures

**Development:** `feature/monitoring` worktree

---

## Storage Monitoring (Deduplication)

### Endpoint

```
GET /api/stats/storage/
```

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `total_files` | Integer | Total number of File records |
| `unique_contents` | Integer | Total number of FileContent records |
| `duplicate_count` | Integer | Files sharing content with others |
| `logical_size_bytes` | Integer | Total size if no deduplication |
| `physical_size_bytes` | Integer | Actual storage consumed |
| `bytes_saved` | Integer | Storage saved by deduplication |
| `savings_percent` | Float | Percentage of storage saved |
| `deduplication_ratio` | Float | Ratio of unique to total files |

### Calculation

```
total_files       = COUNT(File)
unique_contents   = COUNT(FileContent)
duplicate_count   = total_files - unique_contents

logical_size      = SUM(File → content.size)  # Counts duplicates
physical_size     = SUM(FileContent.size)     # Unique content only

bytes_saved       = logical_size - physical_size
savings_percent   = (bytes_saved / logical_size) × 100
dedup_ratio       = unique_contents / total_files
```

### Response Format

```json
{
  "total_files": 150,
  "unique_contents": 120,
  "duplicate_count": 30,
  "logical_size_bytes": 1073741824,
  "physical_size_bytes": 858993459,
  "bytes_saved": 214748365,
  "savings_percent": 20.0,
  "deduplication_ratio": 0.8,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| No files uploaded | Return all zeros, savings_percent = 0 |
| All files unique | duplicate_count = 0, savings_percent = 0 |
| All files duplicates | Extreme case, savings approaches 100% |

---

## Query Monitoring (Search & Filter)

### QueryLog Model

Located in `files` app (not in shared contracts).

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `endpoint` | CharField(255) | API path called |
| `method` | CharField(10) | HTTP method (GET, POST, etc.) |
| `query_params` | JSONField | Filter/search parameters |
| `duration_ms` | PositiveIntegerField | Response time in milliseconds |
| `status_code` | PositiveSmallIntegerField | HTTP response status |
| `result_count` | IntegerField | Number of results returned (-1 if N/A) |
| `error_message` | TextField | Error details if failed (nullable) |
| `user_agent` | CharField(255) | Client user agent (nullable) |
| `ip_address` | GenericIPAddressField | Client IP (nullable) |
| `timestamp` | DateTimeField | When request occurred |

### Indexes

| Field(s) | Purpose |
|----------|---------|
| `timestamp` | Time-based queries |
| `status_code` | Filter by success/failure |
| `duration_ms` | Find slow queries |
| `endpoint` | Filter by API endpoint |

---

## Query Monitoring Endpoints

### List Query Logs

```
GET /api/stats/queries/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | Integer | Results per page (default: 50, max: 200) |
| `offset` | Integer | Pagination offset |
| `endpoint` | String | Filter by endpoint |
| `status_code` | Integer | Filter by status |
| `date_from` | ISO Date | Filter from date |
| `date_to` | ISO Date | Filter to date |

### Slow Queries

```
GET /api/stats/queries/slow/
```

Returns queries exceeding threshold (default: 500ms).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `threshold_ms` | Integer | 500 | Minimum duration to include |
| `limit` | Integer | 50 | Results to return |

### Failed Queries

```
GET /api/stats/queries/failed/
```

Returns queries with status_code >= 400.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | Integer | Results to return |
| `status_code` | Integer | Filter specific error code |

### Query Statistics Summary

```
GET /api/stats/queries/summary/
```

**Response:**

```json
{
  "period": "last_24_hours",
  "total_queries": 1523,
  "successful_queries": 1498,
  "failed_queries": 25,
  "success_rate_percent": 98.36,
  "avg_duration_ms": 45.2,
  "p50_duration_ms": 32,
  "p95_duration_ms": 156,
  "p99_duration_ms": 423,
  "slowest_query_ms": 1250,
  "most_common_endpoint": "/api/files/",
  "most_common_error": "400 Bad Request"
}
```

---

## Middleware Design

### Request Logging Flow

```
Request Received
      ↓
Record start time
      ↓
Process request (views, filters, DB queries)
      ↓
Record end time
      ↓
Calculate duration
      ↓
Create QueryLog entry (async if possible)
      ↓
Return response
```

### What to Log

| Log | Don't Log |
|-----|-----------|
| `/api/files/` queries | `/api/stats/` endpoints (avoid recursion) |
| Search/filter requests | Health check endpoints |
| Failed requests with errors | Static file requests |

### Async Logging

To avoid impacting response time:
- Queue log entries for background processing
- Or use database write-behind with batching
- Fallback: synchronous write (acceptable for SQLite)

---

## Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **Logging middleware fails** | Log error, don't fail the request |
| **QueryLog table full** | Implement rotation (delete entries > 30 days) |
| **Request with no query params** | Store empty dict `{}` |
| **Request timeout** | Log with duration = -1 or timeout value |
| **Recursive logging** | Exclude `/api/stats/` endpoints from logging |
| **Binary/file responses** | Log result_count = -1 (not applicable) |
| **Pagination requests** | Log the page parameters, result_count = page size |

---

## Log Retention

| Policy | Value |
|--------|-------|
| Default retention | 30 days |
| Cleanup method | Periodic task or on-demand |
| Archive option | Export to file before deletion |

### Cleanup Endpoint

```
DELETE /api/stats/queries/cleanup/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `older_than_days` | Integer | Delete logs older than N days |
| `dry_run` | Boolean | Preview count without deleting |

---

## Response Codes

| Endpoint | Success | Errors |
|----------|---------|--------|
| `GET /api/stats/storage/` | 200 | 500 (calculation error) |
| `GET /api/stats/queries/` | 200 | 400 (invalid params) |
| `GET /api/stats/queries/slow/` | 200 | 400 (invalid threshold) |
| `GET /api/stats/queries/failed/` | 200 | - |
| `GET /api/stats/queries/summary/` | 200 | - |
| `DELETE /api/stats/queries/cleanup/` | 200 | 400, 403 |

---

## Integration Points

| Feature | How Monitoring Uses It |
|---------|------------------------|
| **Deduplication** | Reads `File` and `FileContent` counts/sizes |
| **Search/Filter** | Middleware logs all search queries |
| **Shared Contract** | Read-only access to compute storage stats |

---

## Summary

The monitoring feature provides:

1. **Storage visibility** — Know how much deduplication is saving
2. **Performance tracking** — Identify slow queries before they become problems
3. **Error visibility** — See failed queries for debugging
4. **Manual review** — Data exposed via API for dashboard integration

No automated alerting — data is available for external tools or manual review.
