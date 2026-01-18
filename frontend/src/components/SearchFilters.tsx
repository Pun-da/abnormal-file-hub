import React, { useState, useEffect, useCallback } from 'react';
import { FileFilterParams, FILE_TYPE_CATEGORIES, SORT_OPTIONS } from '../types/file';
import { MagnifyingGlassIcon, XMarkIcon, FunnelIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface SearchFiltersProps {
  filters: FileFilterParams;
  onFiltersChange: (filters: FileFilterParams) => void;
  totalCount: number;
}

export const SearchFilters: React.FC<SearchFiltersProps> = ({
  filters,
  onFiltersChange,
  totalCount,
}) => {
  const [searchInput, setSearchInput] = useState(filters.search || '');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== filters.search) {
        onFiltersChange({ ...filters, search: searchInput, offset: 0 });
      }
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const handleFilterChange = useCallback(
    (key: keyof FileFilterParams, value: string | number | undefined) => {
      onFiltersChange({ ...filters, [key]: value, offset: 0 });
    },
    [filters, onFiltersChange]
  );

  const clearAllFilters = useCallback(() => {
    setSearchInput('');
    onFiltersChange({
      ordering: '-uploaded_at',
      limit: 20,
      offset: 0,
    });
  }, [onFiltersChange]);

  const activeFilterCount = [
    filters.search,
    filters.type_category,
    filters.size_min,
    filters.size_max,
    filters.date_from,
    filters.date_to,
  ].filter(Boolean).length;

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <div className="bg-white border-b border-gray-200 p-4 space-y-4">
      {/* Main Search Bar */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search files by name..."
            className="block w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
            >
              <XMarkIcon className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            </button>
          )}
        </div>

        {/* Sort Dropdown */}
        <select
          value={filters.ordering || '-uploaded_at'}
          onChange={(e) => handleFilterChange('ordering', e.target.value)}
          className="block py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm bg-white"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={`inline-flex items-center px-3 py-2 border rounded-lg text-sm font-medium transition-colors ${
            activeFilterCount > 0
              ? 'border-primary-500 text-primary-700 bg-primary-50'
              : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
          }`}
        >
          <FunnelIcon className="h-4 w-4 mr-2" />
          Filters
          {activeFilterCount > 0 && (
            <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-600 text-white">
              {activeFilterCount}
            </span>
          )}
          {showAdvanced ? (
            <ChevronUpIcon className="h-4 w-4 ml-2" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 ml-2" />
          )}
        </button>

        {/* Clear Filters */}
        {activeFilterCount > 0 && (
          <button
            onClick={clearAllFilters}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <XMarkIcon className="h-4 w-4 mr-1" />
            Clear
          </button>
        )}
      </div>

      {/* Advanced Filters Panel */}
      {showAdvanced && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-gray-200">
          {/* File Type Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              File Type
            </label>
            <select
              value={filters.type_category || ''}
              onChange={(e) => handleFilterChange('type_category', e.target.value)}
              className="block w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm bg-white"
            >
              {FILE_TYPE_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          {/* Size Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Size Range
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={filters.size_min || ''}
                onChange={(e) =>
                  handleFilterChange(
                    'size_min',
                    e.target.value ? parseInt(e.target.value) : undefined
                  )
                }
                placeholder="Min (bytes)"
                min={0}
                className="block w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              />
              <span className="text-gray-500">-</span>
              <input
                type="number"
                value={filters.size_max || ''}
                onChange={(e) =>
                  handleFilterChange(
                    'size_max',
                    e.target.value ? parseInt(e.target.value) : undefined
                  )
                }
                placeholder="Max (bytes)"
                min={0}
                className="block w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              />
            </div>
          </div>

          {/* Date From */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Uploaded After
            </label>
            <input
              type="date"
              value={filters.date_from || ''}
              onChange={(e) => handleFilterChange('date_from', e.target.value)}
              className="block w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
            />
          </div>

          {/* Date To */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Uploaded Before
            </label>
            <input
              type="date"
              value={filters.date_to || ''}
              onChange={(e) => handleFilterChange('date_to', e.target.value)}
              className="block w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
            />
          </div>
        </div>
      )}

      {/* Results Count */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>
          {totalCount === 0
            ? 'No files found'
            : totalCount === 1
            ? '1 file found'
            : `${totalCount.toLocaleString()} files found`}
        </span>
        {(filters.size_min || filters.size_max) && (
          <span className="text-xs">
            Size filter: {filters.size_min ? formatBytes(filters.size_min) : '0'} -{' '}
            {filters.size_max ? formatBytes(filters.size_max) : '∞'}
          </span>
        )}
      </div>
    </div>
  );
};
