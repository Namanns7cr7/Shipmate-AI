import axios from 'axios';
import type {
  AnalyzeResponse, GitHubRepo, GitHubBranch, GitHubPR,
  ActuateResponse, FindingPayload, RepoLensSummary,
} from '../types';

const BASE = '/api';

const gh = axios.create({ baseURL: BASE });

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export const api = {
  // ── Auth ────────────────────────────────────────────────────────────────

  async getAuthUrl(): Promise<string> {
    const { data } = await gh.get<{ auth_url: string }>('/auth/github/login');
    return data.auth_url;
  },

  async handleCallback(code: string, state: string) {
    const { data } = await gh.get('/auth/github/callback', { params: { code, state } });
    return data;
  },

  async getMe(token: string) {
    const { data } = await gh.get('/auth/github/me', {
      headers: authHeader(token),
    });
    return data.user;
  },

  async logout(token: string) {
    await gh.post('/auth/github/logout', null, {
      headers: authHeader(token),
    });
  },

  // ── Repos / Branches ────────────────────────────────────────────────────

  async getRepos(token: string): Promise<GitHubRepo[]> {
    const { data } = await gh.get<{ repos: GitHubRepo[] }>('/auth/github/repos', {
      headers: authHeader(token),
    });
    return data.repos;
  },

  async getBranches(owner: string, repo: string, token: string): Promise<GitHubBranch[]> {
    const { data } = await gh.get<{ branches: GitHubBranch[] }>(
      `/auth/github/repos/${owner}/${repo}/branches`,
      { headers: authHeader(token) }
    );
    return data.branches;
  },

  async getPulls(owner: string, repo: string, token: string): Promise<GitHubPR[]> {
    const { data } = await gh.get<{ pulls: GitHubPR[] }>(
      `/auth/github/repos/${owner}/${repo}/pulls`,
      { headers: authHeader(token) }
    );
    return data.pulls;
  },

  // ── Analysis ────────────────────────────────────────────────────────────

  async analyze(params: {
    owner: string;
    repo: string;
    branch: string;
    access_token: string;
    pr_number?: number;
    feature_context?: string;
  }): Promise<AnalyzeResponse> {
    const { data } = await gh.post<AnalyzeResponse>('/analyze', params);
    return data;
  },

  // ── Actuate (Coder → branch + PR) ───────────────────────────────────────

  async actuate(params: {
    owner: string;
    repo: string;
    branch: string;
    access_token: string;
    finding: FindingPayload;
    context?: RepoLensSummary;
    open_pr?: boolean;
  }): Promise<ActuateResponse> {
    const { data } = await gh.post<ActuateResponse>('/actuate', params, {
      timeout: 120_000,
    });
    return data;
  },
};
