# Monitoring Feature - User Guide

## Overview

The monitoring feature provides real-time visibility into system performance, storage efficiency, and API query analytics through a comprehensive web-based dashboard.

## Features

### 1. Storage Statistics
- **Total Files**: Number of files uploaded to the system
- **Unique Contents**: Number of unique file contents (after deduplication)
- **Duplicates**: Number of duplicate files detected
- **Storage Saved**: Percentage and bytes saved through deduplication
- **Deduplication Ratio**: Ratio of unique contents to total files

### 2. Query Performance Metrics (Last 24 Hours)
- **Success Rate**: Percentage of successful API requests
- **Response Times**: Average, P50, P95, P99, and slowest query durations
- **Most Common Endpoint**: The API endpoint receiving the most traffic
- **Most Common Error**: The most frequent error message (if any)

### 3. Query Logs
View detailed logs of all API requests with:
- Timestamp
- HTTP method (GET, POST, DELETE, etc.)
- Endpoint path
- Status code
- Response duration
- Result count
- Query parameters
- Error messages (for failed requests)
- User agent and IP address

### 4. Query Categories
- **Recent Queries**: Last 20 API requests
- **Slow Queries**: Requests taking >500ms
- **Failed Queries**: Requests with status code ≥400

## Accessing the Dashboard

### Web UI

1. **Start the Backend**:
   ```bash
   cd backend
   source venv/bin/activate
   python manage.py runserver 0.0.0.0:8000
   ```

2. **Start the Frontend**:
   ```bash
   cd frontend
   npm start
   ```

3. **Open the Dashboard**:
   - Navigate to http://localhost:3000
   - Click the **"Monitoring"** button in the header

### API Endpoints

All monitoring endpoints are available at `http://localhost:8000/api/stats/`

#### Storage Statistics
```bash
GET /api/stats/storage/
```

**Response:**
```json
{
  "total_files": 7,
  "unique_contents": 4,
  "duplicate_count": 3,
  "logical_size_bytes": 120,
  "physical_size_bytes": 66,
  "bytes_saved": 54,
  "savings_percent": 45.0,
  "deduplication_ratio": 0.5714,
  "timestamp": "2026-01-18T11:32:08.709850Z"
}
```

#### Query Summary
```bash
GET /api/stats/queries/summary/
```

**Response:**
```json
{
  "period": "last_24_hours",
  "total_queries": 28,
  "successful_queries": 27,
  "failed_queries": 1,
  "success_rate_percent": 96.43,
  "avg_duration_ms": 3.6,
  "p50_duration_ms": 2,
  "p95_duration_ms": 12,
  "p99_duration_ms": 14,
  "slowest_query_ms": 14,
  "most_common_endpoint": "/api/files/",
  "most_common_error": "400 - No file provided"
}
```

#### List Query Logs
```bash
GET /api/stats/queries/
GET /api/stats/queries/?limit=10&offset=0
GET /api/stats/queries/?endpoint=/api/files/
GET /api/stats/queries/?status_code=400
```

**Parameters:**
- `limit`: Results per page (default: 50, max: 200)
- `offset`: Pagination offset
- `endpoint`: Filter by endpoint
- `status_code`: Filter by status code
- `date_from`: Filter from date (ISO format)
- `date_to`: Filter to date (ISO format)

#### Slow Queries
```bash
GET /api/stats/queries/slow/
GET /api/stats/queries/slow/?threshold_ms=1000
```

**Parameters:**
- `threshold_ms`: Minimum duration in milliseconds (default: 500)
- `limit`: Results to return (default: 50)

#### Failed Queries
```bash
GET /api/stats/queries/failed/
GET /api/stats/queries/failed/?status_code=500
```

**Parameters:**
- `limit`: Results to return (default: 50)
- `status_code`: Filter by specific error code

#### Cleanup Old Logs
```bash
# Preview cleanup (dry run)
DELETE /api/stats/queries/cleanup/?older_than_days=30&dry_run=true

# Actually delete logs
DELETE /api/stats/queries/cleanup/?older_than_days=30
```

**Parameters:**
- `older_than_days`: Delete logs older than N days (default: 30)
- `dry_run`: If true, preview count without deleting

## Dashboard Features

### Auto-Refresh
- Enable the **"Auto-refresh (10s)"** checkbox to automatically update metrics every 10 seconds
- Useful for real-time monitoring

### Manual Refresh
- Click the **"Refresh"** button to manually update all metrics

### Log Cleanup
- **Preview Cleanup**: Shows how many logs would be deleted (>30 days old)
- **Run Cleanup**: Actually deletes old logs after confirmation

### Query Details
- Click **"Details"** on any query log row to expand and view:
  - Query parameters
  - User agent
  - IP address
  - Error messages (if failed)

## Generating Test Data

Use the provided script to generate sample data for testing:

```bash
./generate_test_data.sh
```

This will:
- Upload 5 files (3 duplicates)
- Make ~20+ API requests
- Generate at least 1 failed request
- Create query logs with various patterns

## Color Coding

### Status Codes
- 🟢 **Green**: 2xx (Success)
- 🟡 **Yellow**: 4xx (Client Error)
- 🔴 **Red**: 5xx (Server Error)

### Response Times
- 🟢 **Green**: <100ms (Fast)
- 🟡 **Yellow**: 100-500ms (Moderate)
- 🔴 **Red**: >500ms (Slow)

### Success Rate
- 🟢 **Excellent**: ≥95%
- 🟡 **Good**: 90-95%
- 🔴 **Poor**: <90%

## Architecture

### Backend Components

1. **QueryLog Model** (`files/models.py`)
   - Stores all query log entries
   - Indexed on timestamp, status_code, duration_ms, endpoint

2. **QueryLoggingMiddleware** (`files/middleware.py`)
   - Automatically captures all API requests
   - Excludes `/api/stats/`, `/admin/`, `/health/`, `/static/` paths
   - Non-blocking (logging failures don't affect requests)

3. **Stats Views** (`files/stats/views.py`)
   - `StorageStatsView`: Calculates deduplication metrics
   - `QueryLogViewSet`: Provides query log endpoints

### Frontend Components

1. **StorageStatsCard**: Displays storage metrics with visual cards
2. **QuerySummaryCard**: Shows 24-hour performance summary
3. **QueryLogsTable**: Interactive table with expandable rows
4. **MonitoringDashboard**: Main dashboard component with tabs

## Performance Considerations

### Middleware Impact
- Minimal overhead (~1-2ms per request)
- Logging is non-blocking
- Failed logging doesn't affect request processing

### Database Indexes
- Optimized queries with indexes on key fields
- Efficient percentile calculations for SQLite compatibility

### Log Retention
- Default retention: 30 days
- Automatic cleanup available via API or UI
- Recommended: Set up periodic cleanup (e.g., weekly cron job)

## Testing

Run the monitoring tests:

```bash
cd backend
source venv/bin/activate
python manage.py test files.tests_monitoring -v 2
```

**Test Coverage:**
- 51 tests covering all monitoring features
- Model creation and validation
- Middleware logging behavior
- API endpoints and responses
- Integration tests

## Troubleshooting

### No Query Logs Appearing
1. Verify middleware is registered in `settings.py`
2. Check that requests are not to excluded paths
3. Ensure database migrations are applied: `python manage.py migrate`

### Frontend Not Loading
1. Check backend is running on port 8000
2. Verify CORS is enabled in backend settings
3. Check browser console for errors

### Slow Dashboard Performance
1. Run log cleanup to reduce database size
2. Reduce auto-refresh frequency
3. Use pagination and filters to limit results

## Best Practices

1. **Regular Cleanup**: Run cleanup weekly to maintain performance
2. **Monitor Slow Queries**: Investigate queries >500ms
3. **Track Success Rate**: Alert if success rate drops below 95%
4. **Review Failed Queries**: Check error patterns regularly
5. **Storage Monitoring**: Track deduplication effectiveness

## Future Enhancements

Potential improvements:
- Export logs to CSV/JSON
- Custom date range filters
- Real-time alerts (email/Slack)
- Query performance trends over time
- Grafana/Prometheus integration
- Advanced analytics and visualizations
