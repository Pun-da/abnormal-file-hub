export interface File {
  id: string;
  original_filename: string;
  file_type: string;
  size: number;
  uploaded_at: string;
  file: string;
  content_hash: string;
  is_duplicate: boolean;
}

// Paginated response from API
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Filter parameters for search
export interface FileFilterParams {
  search?: string;
  file_type?: string;
  type_category?: string;
  size_min?: number;
  size_max?: number;
  date_from?: string;
  date_to?: string;
  ordering?: string;
  limit?: number;
  offset?: number;
}

// Common MIME type categories for filtering
export const FILE_TYPE_CATEGORIES = [
  { value: '', label: 'All Types' },
  { value: 'image', label: 'Images' },
  { value: 'application', label: 'Documents' },
  { value: 'text', label: 'Text Files' },
  { value: 'audio', label: 'Audio' },
  { value: 'video', label: 'Video' },
] as const;

// Sort options
export const SORT_OPTIONS = [
  { value: '-uploaded_at', label: 'Newest First' },
  { value: 'uploaded_at', label: 'Oldest First' },
  { value: 'original_filename', label: 'Name (A-Z)' },
  { value: '-original_filename', label: 'Name (Z-A)' },
  { value: 'content__size', label: 'Size (Smallest)' },
  { value: '-content__size', label: 'Size (Largest)' },
] as const;
