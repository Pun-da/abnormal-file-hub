import React, { useState, useEffect } from 'react';
import { StorageStatsCard } from './StorageStatsCard';
import { QuerySummaryCard } from './QuerySummaryCard';
import { QueryLogsTable } from './QueryLogsTable';
import { monitoringService } from '../services/monitoringService';
import { 
  StorageStats, 
  QuerySummary, 
  QueryLog,
  SlowQueriesResponse,
  FailedQueriesResponse 
} from '../types/monitoring';

type TabType = 'overview' | 'recent' | 'slow' | 'failed';

export const MonitoringDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [querySummary, setQuerySummary] = useState<QuerySummary | null>(null);
  const [recentLogs, setRecentLogs] = useState<QueryLog[]>([]);
  const [slowQueries, setSlowQueries] = useState<QueryLog[]>([]);
  const [failedQueries, setFailedQueries] = useState<QueryLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Fetch storage stats
      const stats = await monitoringService.getStorageStats();
      setStorageStats(stats);

      // Fetch query summary
      const summary = await monitoringService.getQuerySummary();
      setQuerySummary(summary);

      // Fetch recent logs
      const recent = await monitoringService.getQueryLogs({ limit: 20 });
      setRecentLogs(recent.results);

      // Fetch slow queries
      const slow = await monitoringService.getSlowQueries({ threshold_ms: 500, limit: 20 });
      setSlowQueries(slow.results);

      // Fetch failed queries
      const failed = await monitoringService.getFailedQueries({ limit: 20 });
      setFailedQueries(failed.results);
    } catch (err) {
      console.error('Error fetching monitoring data:', err);
      setError('Failed to load monitoring data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchData();
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleCleanup = async (dryRun: boolean = true) => {
    try {
      const result = await monitoringService.cleanupLogs({
        older_than_days: 30,
        dry_run: dryRun,
      });

      if (dryRun) {
        alert(`Cleanup Preview:\n${result.logs_to_delete} logs would be deleted.\nCutoff date: ${new Date(result.cutoff_date).toLocaleString()}`);
      } else {
        alert(`Cleanup Complete:\n${result.deleted_count} logs deleted.`);
        fetchData(); // Refresh data
      }
    } catch (err) {
      console.error('Error cleaning up logs:', err);
      alert('Failed to cleanup logs. Please try again.');
    }
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <svg className="w-5 h-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span className="text-red-800">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Controls */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Monitoring</h1>
          <p className="text-sm text-gray-500 mt-1">Performance metrics and query analytics</p>
        </div>
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-gray-700">Auto-refresh (10s)</span>
          </label>
          <button
            onClick={() => fetchData()}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
          <button
            onClick={() => handleCleanup(true)}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
          >
            Preview Cleanup
          </button>
          <button
            onClick={() => {
              if (window.confirm('Are you sure you want to delete old logs (>30 days)?')) {
                handleCleanup(false);
              }
            }}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Run Cleanup
          </button>
        </div>
      </div>

      {/* Storage Stats */}
      {storageStats && (
        <StorageStatsCard stats={storageStats} isLoading={isLoading} />
      )}

      {/* Query Summary */}
      {querySummary && (
        <div className="mt-6">
          <QuerySummaryCard summary={querySummary} isLoading={isLoading} />
        </div>
      )}

      {/* Tabs */}
      <div className="mt-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('recent')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'recent'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Recent Queries ({recentLogs.length})
            </button>
            <button
              onClick={() => setActiveTab('slow')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'slow'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Slow Queries ({slowQueries.length})
            </button>
            <button
              onClick={() => setActiveTab('failed')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'failed'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Failed Queries ({failedQueries.length})
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">System Health</h3>
                <p className="text-sm text-blue-800">
                  All monitoring systems operational. 
                  {querySummary && querySummary.success_rate_percent >= 95 && ' API performance is excellent.'}
                  {querySummary && querySummary.success_rate_percent < 95 && querySummary.success_rate_percent >= 90 && ' API performance is good.'}
                  {querySummary && querySummary.success_rate_percent < 90 && ' API performance needs attention.'}
                </p>
              </div>
              <QueryLogsTable logs={recentLogs.slice(0, 10)} title="Recent Activity" />
            </div>
          )}
          {activeTab === 'recent' && (
            <QueryLogsTable logs={recentLogs} title="Recent Queries" />
          )}
          {activeTab === 'slow' && (
            <QueryLogsTable logs={slowQueries} title="Slow Queries (>500ms)" />
          )}
          {activeTab === 'failed' && (
            <QueryLogsTable logs={failedQueries} title="Failed Queries" />
          )}
        </div>
      </div>
    </div>
  );
};
