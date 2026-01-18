import React from 'react';
import { QuerySummary } from '../types/monitoring';

interface QuerySummaryCardProps {
  summary: QuerySummary;
  isLoading?: boolean;
}

export const QuerySummaryCard: React.FC<QuerySummaryCardProps> = ({ summary, isLoading }) => {
  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Query Performance (Last 24 Hours)</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Success Rate */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-600">Success Rate</h3>
            <div className={`px-2 py-1 rounded text-xs font-semibold ${
              summary.success_rate_percent >= 95 ? 'bg-green-100 text-green-800' :
              summary.success_rate_percent >= 90 ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
            }`}>
              {summary.success_rate_percent >= 95 ? 'Excellent' :
               summary.success_rate_percent >= 90 ? 'Good' : 'Poor'}
            </div>
          </div>
          <p className="text-3xl font-bold text-gray-900">{summary.success_rate_percent.toFixed(1)}%</p>
          <div className="mt-2 text-sm text-gray-500">
            <span className="text-green-600 font-semibold">{summary.successful_queries}</span> success / 
            <span className="text-red-600 font-semibold ml-1">{summary.failed_queries}</span> failed
          </div>
          <div className="mt-1 text-xs text-gray-400">
            Total: {summary.total_queries} queries
          </div>
        </div>

        {/* Response Times */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <h3 className="text-sm font-medium text-gray-600 mb-3">Response Times</h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">Average</span>
              <span className="text-sm font-semibold text-gray-900">{summary.avg_duration_ms.toFixed(1)} ms</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">P50 (Median)</span>
              <span className="text-sm font-semibold text-gray-900">{summary.p50_duration_ms} ms</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">P95</span>
              <span className="text-sm font-semibold text-gray-900">{summary.p95_duration_ms} ms</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">P99</span>
              <span className="text-sm font-semibold text-gray-900">{summary.p99_duration_ms} ms</span>
            </div>
            <div className="flex justify-between items-center pt-2 border-t border-gray-200">
              <span className="text-xs text-gray-500">Slowest</span>
              <span className={`text-sm font-semibold ${
                summary.slowest_query_ms > 1000 ? 'text-red-600' :
                summary.slowest_query_ms > 500 ? 'text-yellow-600' :
                'text-green-600'
              }`}>
                {summary.slowest_query_ms} ms
              </span>
            </div>
          </div>
        </div>

        {/* Common Info */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <h3 className="text-sm font-medium text-gray-600 mb-3">Most Common</h3>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-gray-500 mb-1">Endpoint</p>
              <p className="text-sm font-mono bg-gray-50 px-2 py-1 rounded break-all">
                {summary.most_common_endpoint || 'N/A'}
              </p>
            </div>
            {summary.most_common_error && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Error</p>
                <p className="text-sm font-mono bg-red-50 text-red-800 px-2 py-1 rounded break-all">
                  {summary.most_common_error}
                </p>
              </div>
            )}
            {!summary.most_common_error && (
              <div className="text-sm text-gray-400 italic">
                No errors in this period
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
