/**
 * Types for RAG Semantic Search
 */

export interface SemanticSearchResult {
  file_id: string;
  file_name: string;
  file_type: string;
  score: number;
  matched_chunks: number;
  preview: string;
}

export interface SemanticSearchResponse {
  query: string;
  results: SemanticSearchResult[];
  total_results: number;
  parameters: {
    top_k: number;
    threshold: number;
    aggregation: string;
  };
}

export interface SemanticSearchParams {
  q: string;
  top_k?: number;
  threshold?: number;
  aggregation?: 'max' | 'mean' | 'weighted';
}

export interface RAGStats {
  total_chunks: number;
  collection_name: string;
  embedding_dimension: number;
  model_name: string;
}

export const AGGREGATION_OPTIONS = [
  { value: 'max', label: 'Max Score', description: 'Use highest chunk score' },
  { value: 'mean', label: 'Mean Score', description: 'Average all chunk scores' },
  { value: 'weighted', label: 'Weighted', description: 'Weight by chunk rank' },
] as const;
