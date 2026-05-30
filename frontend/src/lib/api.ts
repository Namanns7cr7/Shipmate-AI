import axios from 'axios';
import type { AnalyzeResponse, RepoSummary } from '../types';

const API_BASE = '/api';

export const api = {
  async analyze(featureRequest: string, repoContext?: string): Promise<AnalyzeResponse> {
    const { data } = await axios.post<AnalyzeResponse>(`${API_BASE}/analyze`, {
      feature_request: featureRequest,
      repo_context: repoContext,
    });
    return data;
  },

  async uploadRepo(file: File): Promise<RepoSummary> {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await axios.post<RepoSummary>(`${API_BASE}/upload-repo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async getSampleRepo(): Promise<RepoSummary> {
    const { data } = await axios.get<RepoSummary>(`${API_BASE}/sample`);
    return data;
  },
};
