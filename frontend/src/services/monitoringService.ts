import axios from 'axios';
import {
  StorageStats,
  QueryLogListResponse,
  SlowQueriesResponse,
  FailedQueriesResponse,
  QuerySummary,
  CleanupResponse,
} from '../types/monitoring';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const monitoringService = {
  async getStorageStats(): Promise<StorageStats> {
    const response = await axios.get(`${API_URL}/stats/storage/`);
    return response.data;
  },

  async getQueryLogs(params?: {
    limit?: number;
    offset?: number;
    endpoint?: string;
    status_code?: number;
    date_from?: string;
    date_to?: string;
  }): Promise<QueryLogListResponse> {
    const response = await axios.get(`${API_URL}/stats/queries/`, { params });
    return response.data;
  },

  async getSlowQueries(params?: {
    threshold_ms?: number;
    limit?: number;
  }): Promise<SlowQueriesResponse> {
    const response = await axios.get(`${API_URL}/stats/queries/slow/`, { params });
    return response.data;
  },

  async getFailedQueries(params?: {
    limit?: number;
    status_code?: number;
  }): Promise<FailedQueriesResponse> {
    const response = await axios.get(`${API_URL}/stats/queries/failed/`, { params });
    return response.data;
  },

  async getQuerySummary(): Promise<QuerySummary> {
    const response = await axios.get(`${API_URL}/stats/queries/summary/`);
    return response.data;
  },

  async cleanupLogs(params: {
    older_than_days?: number;
    dry_run?: boolean;
  }): Promise<CleanupResponse> {
    const queryParams = new URLSearchParams();
    if (params.older_than_days) {
      queryParams.append('older_than_days', params.older_than_days.toString());
    }
    if (params.dry_run !== undefined) {
      queryParams.append('dry_run', params.dry_run.toString());
    }
    
    const response = await axios.delete(
      `${API_URL}/stats/queries/cleanup/?${queryParams.toString()}`
    );
    return response.data;
  },
};
