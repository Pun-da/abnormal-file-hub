/**
 * Semantic Search Component
 * 
 * Allows users to search file contents using natural language queries.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ragService } from '../services/ragService';
import { SemanticSearchParams } from '../types/rag';
import {
  MagnifyingGlassIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  SparklesIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';

export const SemanticSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [searchParams, setSearchParams] = useState<SemanticSearchParams>({
    q: '',
    top_k: 10,
    threshold: 0.3,
    aggregation: 'max',
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  // Fetch search results - automatically refetches when searchParams change
  const { data: searchResults, isLoading, error, refetch } = useQuery({
    queryKey: ['semantic-search', searchParams],
    queryFn: () => ragService.semanticSearch(searchParams),
    enabled: hasSearched && searchParams.q.length >= 3,
  });

  // Fetch RAG stats
  const { data: stats } = useQuery({
    queryKey: ['rag-stats'],
    queryFn: ragService.getStats,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length < 3) {
      return;
    }
    setSearchParams({ ...searchParams, q: query.trim() });
    setHasSearched(true);
    refetch();
  };

  const handleClearSearch = () => {
    setQuery('');
    setSearchParams({ ...searchParams, q: '' });
    setHasSearched(false);
  };

  const formatScore = (score: number): string => {
    return (score * 100).toFixed(1);
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600 bg-green-50';
    if (score >= 0.6) return 'text-blue-600 bg-blue-50';
    if (score >= 0.4) return 'text-yellow-600 bg-yellow-50';
    return 'text-gray-600 bg-gray-50';
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
      <div className="flex items-center gap-2 mb-2">
        <SparklesIcon className="w-6 h-6 text-purple-600" />
        <h2 className="text-2xl font-bold text-gray-900">Semantic Search</h2>
      </div>
      <p className="text-gray-600">
        Search file contents using natural language queries
      </p>
      {stats && stats.total_chunks !== undefined && (
        <div className="mt-2 text-sm text-gray-500">
          {stats.total_chunks.toLocaleString()} chunks indexed • Model: {stats.model_name}
        </div>
      )}
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          {/* Main Search Input */}
          <div className="flex gap-2 mb-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="E.g., 'quarterly earnings report' or 'machine learning algorithms'"
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                minLength={3}
              />
            </div>
            <button
              type="submit"
              disabled={query.trim().length < 3}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              Search
            </button>
            {hasSearched && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          {/* Advanced Options Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <Cog6ToothIcon className="w-4 h-4" />
            Advanced Options
            {showAdvanced ? (
              <ChevronUpIcon className="w-4 h-4" />
            ) : (
              <ChevronDownIcon className="w-4 h-4" />
            )}
          </button>

          {/* Advanced Options */}
          {showAdvanced && (
            <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Results
                </label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={searchParams.top_k}
                  onChange={(e) => {
                    const newValue = parseInt(e.target.value) || 10;
                    setSearchParams({
                      ...searchParams,
                      top_k: newValue,
                    });
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Current: {searchParams.top_k}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Threshold (0-1)
                </label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={searchParams.threshold}
                  onChange={(e) => {
                    const newValue = parseFloat(e.target.value) || 0.3;
                    setSearchParams({
                      ...searchParams,
                      threshold: Math.max(0, Math.min(1, newValue)),
                    });
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Current: {searchParams.threshold} (lower = more results)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Aggregation
                </label>
                <select
                  value={searchParams.aggregation}
                  onChange={(e) => {
                    setSearchParams({
                      ...searchParams,
                      aggregation: e.target.value as 'max' | 'mean' | 'weighted',
                    });
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                >
                  <option value="max">Max Score</option>
                  <option value="mean">Mean Score</option>
                  <option value="weighted">Weighted</option>
                </select>
              </div>
            </div>
          )}

          {/* Help Text */}
          {query.trim().length > 0 && query.trim().length < 3 && (
            <div className="mt-2 flex items-start gap-2 text-sm text-amber-600">
              <InformationCircleIcon className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>Query must be at least 3 characters long</span>
            </div>
          )}
        </div>
      </form>

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
          <p className="mt-2 text-gray-600">Searching...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">Search failed</p>
          <p className="text-red-600 text-sm mt-1">
            {error instanceof Error ? error.message : 'An error occurred'}
          </p>
        </div>
      )}

      {/* Results */}
      {hasSearched && !isLoading && searchResults && (
        <div>
          {/* Results Header */}
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {searchResults.total_results === 0
                  ? 'No results found'
                  : `Found ${searchResults.total_results} file${
                      searchResults.total_results === 1 ? '' : 's'
                    }`}
              </h3>
              <p className="text-sm text-gray-500">
                Query: "{searchResults.query}"
              </p>
            </div>
          </div>

          {/* Empty State */}
          {searchResults.results.length === 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
              <DocumentTextIcon className="w-12 h-12 text-yellow-600 mx-auto mb-3" />
              <p className="text-gray-900 font-medium mb-2">No files match your query</p>
              <p className="text-sm text-gray-600 mb-3">
                Current threshold: <span className="font-mono font-bold">{searchParams.threshold}</span>
              </p>
              <div className="space-y-2 text-sm text-gray-700">
                <p className="font-medium">Try these solutions:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Lower the threshold in Advanced Options (try 0.2 or 0.3)</li>
                  <li>Use different search terms or simpler words</li>
                  <li>Upload more files to increase the search corpus</li>
                  <li>Check if files are indexed (see stats above)</li>
                </ul>
              </div>
              <button
                onClick={() => {
                  setSearchParams({ ...searchParams, threshold: 0.2 });
                  setShowAdvanced(true);
                }}
                className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Lower Threshold to 0.2 and Retry
              </button>
            </div>
          )}

          {/* Results List */}
          {searchResults.results.length > 0 && (
            <div className="space-y-3">
              {searchResults.results.map((result, index) => (
                <div
                  key={result.file_id}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:border-purple-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* File Name */}
                      <div className="flex items-center gap-2 mb-2">
                        <DocumentTextIcon className="w-5 h-5 text-gray-400 flex-shrink-0" />
                        <h4 className="font-medium text-gray-900 truncate">
                          {result.file_name}
                        </h4>
                      </div>

                      {/* Preview */}
                      <p className="text-sm text-gray-600 mb-3 line-clamp-3">
                        {result.preview}
                      </p>

                      {/* Metadata */}
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>{result.file_type}</span>
                        <span>•</span>
                        <span>{result.matched_chunks} chunks matched</span>
                      </div>
                    </div>

                    {/* Score Badge */}
                    <div className="flex-shrink-0">
                      <div
                        className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(
                          result.score
                        )}`}
                      >
                        {formatScore(result.score)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Info Banner */}
      {!hasSearched && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-3">
            <InformationCircleIcon className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">How to use Semantic Search:</p>
              <ul className="list-disc list-inside space-y-1 text-blue-700">
                <li>Use natural language queries (e.g., "Q4 earnings report")</li>
                <li>Searches through PDF and text file contents</li>
                <li>Results ranked by relevance score</li>
                <li>Adjust threshold to control result quality</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
