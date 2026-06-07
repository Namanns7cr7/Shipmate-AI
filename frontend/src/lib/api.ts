import axios from 'axios';
import type {
  AnalyzeResponse, GitHubRepo, GitHubBranch, GitHubPR,
  ActuateResponse, FindingPayload, RepoLensSummary,
  WatcherState, WatcherLogLine, JournalResponse, AutoFixEvent,
  ScorePoint,
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

  // ── CI watcher ──────────────────────────────────────────────────────────

  async getWatcher(owner: string, repo: string, prNumber: number): Promise<WatcherState | null> {
    try {
      const { data } = await gh.get<WatcherState>(`/watcher/${owner}/${repo}/${prNumber}`);
      return data;
    } catch {
      // 404 = not watching this PR (yet). Treat as "no watcher".
      return null;
    }
  },

  async getWatcherLog(
    owner: string, repo: string, prNumber: number, sinceId = 0,
  ): Promise<{ lines: WatcherLogLine[]; next_id: number }> {
    const { data } = await gh.get<{ lines: WatcherLogLine[]; next_id: number }>(
      `/watcher/${owner}/${repo}/${prNumber}/log`,
      { params: { since_id: sinceId } },
    );
    return data;
  },

  // ── Finding journal ──────────────────────────────────────────────────────

  async getJournal(repoFullName: string): Promise<JournalResponse> {
    const { data } = await gh.get<JournalResponse>('/findings/journal', {
      params: { repo: repoFullName },
    });
    return data;
  },

  async dismissFinding(params: {
    kind: string; title: string; file?: string | null; repo_full_name: string; notes?: string;
  }): Promise<{ signature: string; state: string }> {
    const { data } = await gh.post('/findings/dismiss', params);
    return data;
  },

  async reopenFinding(params: {
    kind: string; title: string; file?: string | null; repo_full_name: string;
  }): Promise<{ signature: string; state: string }> {
    const { data } = await gh.post('/findings/reopen', params);
    return data;
  },

  // ── Score history ────────────────────────────────────────────────────────

  async getHistory(owner: string, repo: string, branch?: string, limit = 30): Promise<ScorePoint[]> {
    const { data } = await gh.get<ScorePoint[]>('/history', {
      params: { owner, repo, branch, limit },
    });
    return data;
  },

  // ── Auto-fix (server-side autonomous loop, SSE) ───────────────────────────
  //
  // EventSource can't send a POST body / Authorization, so we stream the
  // response with fetch + a ReadableStream reader and parse `data:` frames
  // ourselves. `onEvent` fires per parsed event; returns when the stream ends
  // or `signal` aborts.

  async startAutoFix(
    params: { owner: string; repo: string; branch: string; access_token: string; rounds?: number },
    onEvent: (e: AutoFixEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const resp = await fetch(`${BASE}/auto-fix/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      signal,
    });
    if (!resp.ok || !resp.body) {
      throw new Error(`auto-fix stream failed: HTTP ${resp.status}`);
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE frames are separated by a blank line.
      let sep: number;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        for (const line of frame.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              onEvent(JSON.parse(line.slice(6)) as AutoFixEvent);
            } catch {
              // ignore malformed frame
            }
          }
        }
      }
    }
  },
};
