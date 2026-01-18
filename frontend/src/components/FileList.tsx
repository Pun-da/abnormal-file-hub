import React, { useState } from 'react';
import { fileService } from '../services/fileService';
import { FileFilterParams } from '../types/file';
import { SearchFilters } from './SearchFilters';
import { DocumentIcon, TrashIcon, ArrowDownTrayIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const DEFAULT_PAGE_SIZE = 20;

export const FileList: React.FC = () => {
  const queryClient = useQueryClient();
  
  // Filter state
  const [filters, setFilters] = useState<FileFilterParams>({
    ordering: '-uploaded_at',
    limit: DEFAULT_PAGE_SIZE,
    offset: 0,
  });

  // Query for fetching files with filters
  const { data, isLoading, error } = useQuery({
    queryKey: ['files', filters],
    queryFn: () => fileService.getFiles(filters),
  });

  // Mutation for deleting files
  const deleteMutation = useMutation({
    mutationFn: fileService.deleteFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
    },
  });

  // Mutation for downloading files
  const downloadMutation = useMutation({
    mutationFn: ({ fileUrl, filename }: { fileUrl: string; filename: string }) =>
      fileService.downloadFile(fileUrl, filename),
  });

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const handleDownload = async (fileUrl: string, filename: string) => {
    try {
      await downloadMutation.mutateAsync({ fileUrl, filename });
    } catch (err) {
      console.error('Download error:', err);
    }
  };

  const handleFiltersChange = (newFilters: FileFilterParams) => {
    setFilters(newFilters);
  };

  // Pagination helpers
  const totalCount = data?.count || 0;
  const currentPage = Math.floor((filters.offset || 0) / (filters.limit || DEFAULT_PAGE_SIZE)) + 1;
  const totalPages = Math.ceil(totalCount / (filters.limit || DEFAULT_PAGE_SIZE));

  const goToPage = (page: number) => {
    const newOffset = (page - 1) * (filters.limit || DEFAULT_PAGE_SIZE);
    setFilters({ ...filters, offset: newOffset });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const getFileTypeIcon = (fileType: string): string => {
    if (fileType.startsWith('image/')) return '🖼️';
    if (fileType.startsWith('video/')) return '🎬';
    if (fileType.startsWith('audio/')) return '🎵';
    if (fileType.includes('pdf')) return '📕';
    if (fileType.includes('spreadsheet') || fileType.includes('excel')) return '📊';
    if (fileType.includes('document') || fileType.includes('word')) return '📝';
    if (fileType.startsWith('text/')) return '📄';
    return '📁';
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">Failed to load files. Please try again.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const files = data?.results || [];

  return (
    <div>
      {/* Search Filters */}
      <SearchFilters
        filters={filters}
        onFiltersChange={handleFiltersChange}
        totalCount={totalCount}
      />

      <div className="p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Uploaded Files</h2>
        
        {isLoading ? (
          <div className="animate-pulse space-y-4">
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center space-x-4 py-4">
                  <div className="h-8 w-8 bg-gray-200 rounded"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                  </div>
                  <div className="h-8 w-20 bg-gray-200 rounded"></div>
                </div>
              ))}
            </div>
          </div>
        ) : files.length === 0 ? (
          <div className="text-center py-12">
            <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No files found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {filters.search || filters.type_category || filters.size_min || filters.size_max || filters.date_from || filters.date_to
                ? 'Try adjusting your search or filters'
                : 'Get started by uploading a file'}
            </p>
          </div>
        ) : (
          <>
            <div className="flow-root">
              <ul className="-my-5 divide-y divide-gray-200">
                {files.map((file) => (
                  <li key={file.id} className="py-4 hover:bg-gray-50 -mx-4 px-4 rounded-lg transition-colors">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0 text-2xl">
                        {getFileTypeIcon(file.file_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {file.original_filename}
                          </p>
                          {file.is_duplicate && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                              Duplicate
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-500">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 mr-2">
                            {file.file_type}
                          </span>
                          {formatFileSize(file.size)}
                        </p>
                        <p className="text-sm text-gray-500">
                          Uploaded {new Date(file.uploaded_at).toLocaleString()}
                        </p>
                        <p className="text-xs text-gray-400 font-mono truncate" title={file.content_hash}>
                          Hash: {file.content_hash?.substring(0, 16)}...
                        </p>
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleDownload(file.file, file.original_filename)}
                          disabled={downloadMutation.isPending}
                          className="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm leading-4 font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                        >
                          <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                          Download
                        </button>
                        <button
                          onClick={() => handleDelete(file.id)}
                          disabled={deleteMutation.isPending}
                          className="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                          <TrashIcon className="h-4 w-4 mr-1" />
                          Delete
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-6 flex items-center justify-between border-t border-gray-200 pt-4">
                <div className="flex items-center text-sm text-gray-500">
                  Showing {(filters.offset || 0) + 1} to{' '}
                  {Math.min((filters.offset || 0) + files.length, totalCount)} of{' '}
                  {totalCount.toLocaleString()} files
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => goToPage(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeftIcon className="h-4 w-4 mr-1" />
                    Previous
                  </button>
                  
                  {/* Page Numbers */}
                  <div className="flex items-center space-x-1">
                    {[...Array(Math.min(5, totalPages))].map((_, i) => {
                      let pageNum: number;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => goToPage(pageNum)}
                          className={`px-3 py-1 rounded-md text-sm font-medium ${
                            currentPage === pageNum
                              ? 'bg-primary-600 text-white'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => goToPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <ChevronRightIcon className="h-4 w-4 ml-1" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
