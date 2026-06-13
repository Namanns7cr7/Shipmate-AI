import { useEffect, useRef, useState } from 'react';
import { Loader, AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../lib/api';

export default function GitHubCallback() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  // Guard against React StrictMode double-invoking the effect in development.
  // OAuth codes are single-use — a second exchange attempt always returns 400.
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const handleCallback = async () => {
      try {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        const errorParam = params.get('error');
        const errorDesc = params.get('error_description');

        if (errorParam) {
          setStatus('error');
          setError(errorDesc || errorParam);
          setTimeout(() => { window.location.href = '/'; }, 3000);
          return;
        }

        if (!code || !state) {
          setStatus('error');
          setError('Missing authorization code. Please try again.');
          setTimeout(() => { window.location.href = '/'; }, 3000);
          return;
        }

        const response = await api.handleCallback(code, state);

        if (!response.success) throw new Error(response.detail || 'Authentication failed');

        setStatus('success');

        // The backend now returns an opaque session id (session_id) that
        // references the vaulted token — the raw token never reaches the
        // browser. Prefer session_id; fall back to access_token only for an
        // older backend that hasn't shipped the vault yet.
        const credential = response.session_id ?? response.access_token;

        if (window.opener && !window.opener.closed) {
          window.opener.postMessage(
            { type: 'GITHUB_AUTH_SUCCESS', access_token: credential, user: response.user },
            window.location.origin,
          );
          setTimeout(() => window.close(), 800);
        } else {
          localStorage.setItem('github_access_token', credential);
          localStorage.setItem('github_user', JSON.stringify(response.user));
          setTimeout(() => { window.location.href = '/'; }, 1000);
        }
      } catch (err) {
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Failed to authenticate. Please try again.');
        setTimeout(() => { window.location.href = '/'; }, 3000);
      }
    };

    handleCallback();
  }, []);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
      <div className="card" style={{ padding: '40px 48px', textAlign: 'center', maxWidth: 400, width: '100%' }}>
        {status === 'loading' && (
          <>
            <Loader size={48} style={{ color: 'var(--blue-2)', margin: '0 auto 16px', animation: 'spin .7s linear infinite' }} />
            <h1 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 8px' }}>Connecting to GitHub…</h1>
            <p className="muted" style={{ fontSize: 14 }}>Please wait while we complete your authentication.</p>
          </>
        )}
        {status === 'success' && (
          <>
            <CheckCircle size={48} style={{ color: 'var(--emerald)', margin: '0 auto 16px' }} />
            <h1 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 8px' }}>Authentication Successful!</h1>
            <p className="muted" style={{ fontSize: 14 }}>Redirecting to your command center…</p>
          </>
        )}
        {status === 'error' && (
          <>
            <AlertCircle size={48} style={{ color: 'var(--red)', margin: '0 auto 16px' }} />
            <h1 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 8px' }}>Authentication Failed</h1>
            <p style={{ fontSize: 13, color: 'var(--red)', margin: '0 0 12px' }}>{error}</p>
            <p className="muted" style={{ fontSize: 13 }}>Redirecting to home page…</p>
          </>
        )}
      </div>
    </div>
  );
}
