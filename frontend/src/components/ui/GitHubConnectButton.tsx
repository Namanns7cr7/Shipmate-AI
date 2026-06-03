import { GitHubIcon } from './GitHubIcon';

export function Spinner({ size = 18, dark = false }: { size?: number; dark?: boolean }) {
  return (
    <span style={{
      width: size, height: size, display: 'inline-block', borderRadius: '50%',
      border: `2px solid ${dark ? 'rgba(10,19,38,0.2)' : 'rgba(255,255,255,0.2)'}`,
      borderTopColor: dark ? '#0a1326' : 'currentColor',
      animation: 'spin .7s linear infinite',
    }} />
  );
}

interface GitHubConnectButtonProps {
  onClick: () => void;
  label?: string;
  size?: 'sm' | 'lg' | '';
  variant?: 'light' | 'primary';
  loading?: boolean;
  disabled?: boolean;
}

export function GitHubConnectButton({
  onClick, label = 'Connect GitHub',
  size = '', variant = 'light', loading = false, disabled = false,
}: GitHubConnectButtonProps) {
  const sizeClass    = size === 'lg' ? 'btn-lg' : size === 'sm' ? 'btn-sm' : '';
  const variantClass = variant === 'light' ? 'btn-light' : 'btn-primary';
  return (
    <button className={`btn ${variantClass} ${sizeClass}`} onClick={onClick} disabled={loading || disabled}>
      {loading
        ? <><Spinner size={16} dark={variant === 'light'} /> Authorizing…</>
        : <><GitHubIcon size={size === 'lg' ? 20 : 18} /> {label}</>
      }
    </button>
  );
}
