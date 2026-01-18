# Search & Filtering Algorithm

## Overview

The search and filtering system enables efficient retrieval of files through structured filters and text search. All filters use AND logic when combined.

---

## Filter Types

| Filter | Type | Operation | Description |
|--------|------|-----------|-------------|
| **Filename Search** | Text | Case-insensitive substring match | Matches files containing the search term anywhere in the filename |
| **File Type** | Exact/Prefix | Exact match or MIME prefix | Filter by specific type (`application/pdf`) or category (`image/`) |
| **Size Min** | Numeric | Greater than or equal | Files at least N bytes |
| **Size Max** | Numeric | Less than or equal | Files at most N bytes |
| **Date From** | Date | Greater than or equal | Files uploaded on or after date |
| **Date To** | Date | Less than or equal | Files uploaded on or before date |

---

## Combined Filter Logic

All filters are combined using **AND** semantics:

```
Result = (filename MATCHES search)
     AND (file_type MATCHES type filter)
     AND (size >= min_size)
     AND (size <= max_size)
     AND (uploaded_at >= date_from)
     AND (uploaded_at <= date_to)
```

**Absent filters are ignored** — they do not constrain results.

---

## Query Parameters

| Parameter | Format | Example |
|-----------|--------|---------|
| `search` | String | `?search=report` |
| `file_type` | MIME type | `?file_type=application/pdf` |
| `type_category` | MIME prefix | `?type_category=image` |
| `size_min` | Bytes (integer) | `?size_min=1024` |
| `size_max` | Bytes (integer) | `?size_max=10485760` |
| `date_from` | ISO 8601 date | `?date_from=2024-01-01` |
| `date_to` | ISO 8601 date | `?date_to=2024-12-31` |
| `ordering` | Field name | `?ordering=-uploaded_at` |

---

## Recommended Database Indexes

| Field(s) | Index Type | Rationale |
|----------|------------|-----------|
| `original_filename` | B-tree | Accelerates substring search when combined with query patterns |
| `file_type` | B-tree | Fast exact match filtering |
| `size` | B-tree | Efficient range queries |
| `uploaded_at` | B-tree | Date range filtering and default sort |
| `(file_type, uploaded_at)` | Composite B-tree | Common filter combination: "all PDFs from last month" |
| `(file_type, size)` | Composite B-tree | Common filter combination: "large images" |

**Note:** Add indexes based on observed query patterns. Start without indexes to establish baseline, then add targeted indexes based on actual usage.

---

## Sorting

| Option | Description |
|--------|-------------|
| `uploaded_at` (default) | Newest first (`-uploaded_at`) |
| `original_filename` | Alphabetical |
| `size` | Smallest or largest first |
| `file_type` | Grouped by type |

Prefix with `-` for descending order.

---

## Pagination

| Parameter | Description |
|-----------|-------------|
| `limit` | Maximum results per page (default: 20, max: 100) |
| `offset` | Number of results to skip |

**Large result sets:** Always paginate. Never return unbounded results.

---

## Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **Empty search string** | Ignore filter, return all files |
| **No filters provided** | Return all files (paginated) |
| **Invalid size values** | Return 400 Bad Request with validation error |
| **Negative size** | Return 400 Bad Request |
| **size_min > size_max** | Return empty result set |
| **Invalid date format** | Return 400 Bad Request with validation error |
| **date_from > date_to** | Return empty result set |
| **Unknown file_type** | Return empty result set (no error) |
| **No results match** | Return empty list with 200 OK |
| **Special characters in search** | Escape for safe database query |
| **Very long search string** | Truncate to reasonable limit (255 chars) |
| **SQL injection attempts** | ORM parameterization prevents injection |

---

## Response Format

| Field | Description |
|-------|-------------|
| `count` | Total matching files (before pagination) |
| `next` | URL for next page (null if last page) |
| `previous` | URL for previous page (null if first page) |
| `results` | Array of file objects |

---

## Performance Considerations

| Scenario | Recommendation |
|----------|----------------|
| Substring search (`%term%`) | Cannot use index prefix; consider full-text search for large datasets |
| Large offset values | Use cursor-based pagination for deep pages |
| Frequent filter combinations | Add composite indexes for hot paths |
| Count queries on large tables | Consider approximate counts or caching |
