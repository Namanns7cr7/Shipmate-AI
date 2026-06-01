import axios from 'axios';
import type {
  AnalyzeResponse,
  RepoSummary,
  GitHubRepository,
  GitHubBranch,
  GitHubConnection,
} from '../types';

const API_BASE = '/api';

export const api = {
  // ============================================================================
  // Real GitHub OAuth Integration
  // ============================================================================

  async getGitHubAuthUrl(): Promise<{ auth_url: string }> {
    const { data } = await axios.get(`${API_BASE}/github/auth-url`);
    return data;
  },

  async handleGitHubCallback(code: string, state: string): Promise<any> {
    const { data } = await axios.get(`${API_BASE}/github/callback`, {
      params: { code, state },
    });
    return data;
  },

  async getCurrentUser(accessToken: string): Promise<any> {
    const { data } = await axios.get(`${API_BASE}/github/me`, {
      params: { access_token: accessToken },
    });
    return data;
  },

  // ============================================================================
  // Real GitHub API - User Repositories
  // ============================================================================

  async getUserRepositories(accessToken: string): Promise<GitHubRepository[]> {
    const { data } = await axios.get<GitHubRepository[]>(
      `${API_BASE}/github/user-repos`,
      { params: { access_token: accessToken } }
    );
    return data;
  },

  // ============================================================================
  // Real GitHub API - Repository Data
  // ============================================================================

  async getRepositoryBranches(
    owner: string,
    repoName: string,
    accessToken: string
  ): Promise<GitHubBranch[]> {
    const { data } = await axios.get<GitHubBranch[]>(
      `${API_BASE}/github/repos/${owner}/${repoName}/branches`,
      { params: { access_token: accessToken } }
    );
    return data;
  },

  async getRepositoryPulls(
    owner: string,
    repoName: string,
    accessToken: string,
    state: string = 'open'
  ): Promise<any[]> {
    const { data } = await axios.get<any[]>(
      `${API_BASE}/github/repos/${owner}/${repoName}/pulls`,
      { params: { access_token: accessToken, state } }
    );
    return data;
  },

  async getRepositoryIssues(
    owner: string,
    repoName: string,
    accessToken: string,
    state: string = 'open'
  ): Promise<any[]> {
    const { data } = await axios.get<any[]>(
      `${API_BASE}/github/repos/${owner}/${repoName}/issues`,
      { params: { access_token: accessToken, state } }
    );
    return data;
  },

  async getRepositoryContents(
    owner: string,
    repoName: string,
    accessToken: string,
    path: string = ''
  ): Promise<any[]> {
    const { data } = await axios.get<any[]>(
      `${API_BASE}/github/repos/${owner}/${repoName}/contents`,
      { params: { access_token: accessToken, path } }
    );
    return data;
  },

  // ============================================================================
  // Analysis
  // ============================================================================

  async analyzeDeliveryReadiness(
    owner: string,
    repoName: string,
    branch: string,
    featureRequest: string,
    pullNumber?: number,
    issueNumber?: number,
    accessToken?: string
  ): Promise<AnalyzeResponse> {
    const { data } = await axios.post<AnalyzeResponse>(`${API_BASE}/analyze`, {
      repo_id: `${owner}/${repoName}`,
      branch,
      feature_request: featureRequest,
      pull_number: pullNumber,
      issue_number: issueNumber,
      github_token: accessToken,
    });
    return data;
  },

  async analyze(
    repoId: string,
    branch: string,
    featureRequest: string,
    githubToken?: string
  ): Promise<AnalyzeResponse> {
    const { data } = await axios.post<AnalyzeResponse>(`${API_BASE}/analyze`, {
      repo_id: repoId,
      branch,
      feature_request: featureRequest,
      github_token: githubToken,
    });
    return data;
  },

  // ============================================================================
  // Mock/Demo Endpoints (Legacy - for fallback)
  // ============================================================================

  async getGitHubAppInstallUrl(): Promise<{ install_url: string; permissions: string[] }> {
    const { data } = await axios.get(`${API_BASE}/github/app-install-url`);
    return data;
  },

  async getRepositories(githubToken?: string): Promise<GitHubRepository[]> {
    const { data } = await axios.get<GitHubRepository[]>(`${API_BASE}/github/repos`, {
      params: { github_token: githubToken },
    });
    return data;
  },

  async getBranches(repoId: string, githubToken?: string): Promise<GitHubBranch[]> {
    const { data } = await axios.get<GitHubBranch[]>(
      `${API_BASE}/github/repos/${repoId}/branches`,
      { params: { github_token: githubToken } }
    );
    return data;
  },

  async getRepository(repoId: string, githubToken?: string): Promise<GitHubRepository> {
    const { data } = await axios.get<GitHubRepository>(
      `${API_BASE}/github/repos/${repoId}`,
      { params: { github_token: githubToken } }
    );
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

  // ============================================================================
  // Reports
  // ============================================================================

  async exportReport(analysisId: string): Promise<{ download_url: string; expires_in_hours: number }> {
    const { data } = await axios.post(`${API_BASE}/reports/export`, {}, {
      params: { analysis_id: analysisId },
    });
    return data;
  },

  async downloadReport(analysisId: string): Promise<Blob> {
    const { data } = await axios.get(`${API_BASE}/reports/${analysisId}/download`, {
      responseType: 'blob',
    });
    return data;
  },
};
