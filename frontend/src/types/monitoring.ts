export interface StorageStats {
  total_files: number;
  unique_contents: number;
  duplicate_count: number;
  logical_size_bytes: number;
  physical_size_bytes: number;
  bytes_saved: number;
  savings_percent: number;
  deduplication_ratio: number;
  timestamp: string;
}

export interface QueryLog {
  id: string;
  endpoint: string;
  method: string;
  query_params: Record<string, any>;
  duration_ms: number;
  status_code: number;
  result_count: number;
  error_message: string | null;
  user_agent: string | null;
  ip_address: string | null;
  timestamp: string;
}

export interface QueryLogListResponse {
  count: number;
  limit: number;
  offset: number;
  results: QueryLog[];
}

export interface SlowQueriesResponse {
  threshold_ms: number;
  count: number;
  results: QueryLog[];
}

export interface FailedQueriesResponse {
  count: number;
  results: QueryLog[];
}

export interface QuerySummary {
  period: string;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  success_rate_percent: number;
  avg_duration_ms: number;
  p50_duration_ms: number;
  p95_duration_ms: number;
  p99_duration_ms: number;
  slowest_query_ms: number;
  most_common_endpoint: string | null;
  most_common_error: string | null;
}

export interface CleanupResponse {
  dry_run: boolean;
  older_than_days: number;
  cutoff_date: string;
  logs_to_delete?: number;
  deleted_count?: number;
}
