/**
 * Service for RAG Semantic Search API calls
 */

import axios from 'axios';
import { SemanticSearchResponse, SemanticSearchParams, RAGStats } from '../types/rag';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const ragService = {
  /**
   * Perform semantic search on file contents
   */
  async semanticSearch(params: SemanticSearchParams): Promise<SemanticSearchResponse> {
    const response = await axios.get(`${API_URL}/search/semantic/`, {
      params: {
        q: params.q,
        top_k: params.top_k,
        threshold: params.threshold,
        aggregation: params.aggregation,
      },
    });
    return response.data;
  },

  /**
   * Get RAG indexing statistics
   */
  async getStats(): Promise<RAGStats> {
    const response = await axios.get(`${API_URL}/search/rag-stats/`);
    return response.data;
  },
};
