import { useState, useCallback, useEffect } from 'react';
import { api } from '../lib/api';

export interface GitHubUser {
  id: number;
  login: string;
  name: string;
  avatar_url: string;
  html_url: string;
  email?: string;
  bio?: string;
  company?: string;
  location?: string;
  public_repos: number;
  followers: number;
  following: number;
}

export interface GitHubAuthState {
  isAuthenticated: boolean;
  user: GitHubUser | null;
  accessToken: string | null;
  loading: boolean;
  error: string | null;
}

/**
 * Custom hook for managing GitHub authentication
 * 
 * Handles:
 * - Loading stored auth state from localStorage
 * - Initiating GitHub OAuth login
 * - Logging out
 * - Managing auth state
 */
export function useGithubAuth() {
  const [state, setState] = useState<GitHubAuthState>({
    isAuthenticated: false,
    user: null,
    accessToken: null,
    loading: true,
    error: null,
  });

  // Load stored auth state on mount
  useEffect(() => {
    const loadStoredAuth = () => {
      try {
        const storedToken = localStorage.getItem('github_access_token');
        const storedUser = localStorage.getItem('github_user');

        if (storedToken && storedUser) {
          setState({
            isAuthenticated: true,
            user: JSON.parse(storedUser),
            accessToken: storedToken,
            loading: false,
            error: null,
          });
        } else {
          setState(prev => ({ ...prev, loading: false }));
        }
      } catch (err) {
        console.error('Failed to load stored auth:', err);
        setState(prev => ({ ...prev, loading: false }));
      }
    };

    loadStoredAuth();
  }, []);

  const initiateLogin = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));

      // Get GitHub auth URL
      const { auth_url } = await api.getGitHubAuthUrl();

      // Open popup for GitHub OAuth
      const width = 500;
      const height = 600;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;

      const popup = window.open(
        auth_url,
        'GitHub Login',
        `width=${width},height=${height},left=${left},top=${top}`
      );

      if (!popup) {
        throw new Error('Popup blocked. Please allow popups for this site.');
      }

      // The callback page will handle the token exchange
      // and redirect will trigger a page reload or state update
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setState(prev => ({ ...prev, error: errorMessage, loading: false }));
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true }));

      if (state.accessToken) {
        await api.logoutGitHub(state.accessToken);
      }

      // Clear localStorage
      localStorage.removeItem('github_access_token');
      localStorage.removeItem('github_user');

      // Clear state
      setState({
        isAuthenticated: false,
        user: null,
        accessToken: null,
        loading: false,
        error: null,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Logout failed';
      setState(prev => ({ ...prev, error: errorMessage, loading: false }));
    }
  }, [state.accessToken]);

  // After callback page redirect, load auth from localStorage
  const refreshAuth = useCallback(() => {
    const storedToken = localStorage.getItem('github_access_token');
    const storedUser = localStorage.getItem('github_user');

    if (storedToken && storedUser) {
      setState({
        isAuthenticated: true,
        user: JSON.parse(storedUser),
        accessToken: storedToken,
        loading: false,
        error: null,
      });
    }
  }, []);

  return {
    ...state,
    initiateLogin,
    logout,
    refreshAuth,
  };
}
