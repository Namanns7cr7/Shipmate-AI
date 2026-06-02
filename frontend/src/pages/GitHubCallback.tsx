import { useEffect, useState } from 'react';
import { Loader, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../lib/api';

export default function GitHubCallback() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get code and state from URL
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        const errorParam = params.get('error');
        const errorDesc = params.get('error_description');

        // Check for OAuth error
        if (errorParam) {
          setStatus('error');
          setError(errorDesc || errorParam);
          // Redirect to home after 3 seconds
          setTimeout(() => {
            window.location.href = '/';
          }, 3000);
          return;
        }

        // Validate code
        if (!code || !state) {
          setStatus('error');
          setError('Missing authorization code. Please try again.');
          setTimeout(() => {
            window.location.href = '/';
          }, 3000);
          return;
        }

        // Exchange code for token
        const response = await api.handleGitHubCallback(code, state);

        if (!response.success) {
          throw new Error(response.detail || 'Authentication failed');
        }

        // Store token and user info in localStorage
        localStorage.setItem('github_access_token', response.access_token);
        localStorage.setItem('github_user', JSON.stringify(response.user));

        setStatus('success');

        // Redirect to dashboard after 1 second
        setTimeout(() => {
          window.location.href = '/';
        }, 1000);
      } catch (err) {
        setStatus('error');
        setError(
          err instanceof Error
            ? err.message
            : 'Failed to authenticate. Please try again.'
        );

        // Redirect to home on error after 3 seconds
        setTimeout(() => {
          window.location.href = '/';
        }, 3000);
      }
    };

    handleCallback();
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <div className="text-center">
        {status === 'loading' && (
          <>
            <div className="mb-4 flex justify-center">
              <Loader size={48} className="animate-spin text-blue-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">
              Connecting to GitHub...
            </h1>
            <p className="mt-2 text-slate-400">
              Please wait while we complete your authentication.
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="mb-4 flex justify-center">
              <CheckCircle size={48} className="text-green-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">
              Authentication Successful!
            </h1>
            <p className="mt-2 text-slate-400">
              Redirecting to dashboard...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="mb-4 flex justify-center">
              <AlertCircle size={48} className="text-red-400" />
            </div>
            <h1 className="text-2xl font-bold text-white">
              Authentication Failed
            </h1>
            <p className="mt-2 text-red-400">{error}</p>
            <p className="mt-4 text-slate-400">
              Redirecting to home page...
            </p>
          </>
        )}
      </div>
    </div>
  );
}

