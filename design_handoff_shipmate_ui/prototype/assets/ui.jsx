/* ShipMate AI — UI primitives, icons, logo, shared data */
const { useState, useEffect, useRef, useMemo, useCallback } = React;

/* ----------------------------------------------------------------
   ICONS  (lucide-style, 24 viewBox, stroke=currentColor)
----------------------------------------------------------------- */
const ICONS = {
  github: "M12 2C6.48 2 2 6.58 2 12.26c0 4.5 2.87 8.32 6.84 9.67.5.1.68-.22.68-.49v-1.7c-2.78.62-3.37-1.36-3.37-1.36-.45-1.18-1.11-1.5-1.11-1.5-.91-.63.07-.62.07-.62 1 .07 1.53 1.05 1.53 1.05.9 1.57 2.36 1.12 2.94.86.09-.66.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.7 0 0 .84-.27 2.75 1.05a9.34 9.34 0 0 1 5 0c1.91-1.32 2.75-1.05 2.75-1.05.55 1.4.2 2.44.1 2.7.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.8-4.57 5.06.36.32.68.94.68 1.9v2.82c0 .27.18.6.69.49A10.02 10.02 0 0 0 22 12.26C22 6.58 17.52 2 12 2z",
  play: "M7 4.5v15l13-7.5z",
  arrowRight: "M5 12h14M13 5l7 7-7 7",
  arrowUpRight: "M7 17 17 7M7 7h10v10",
  check: "M20 6 9 17l-5-5",
  checkCircle: "M9 12l2 2 4-4M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  shield: "M12 3l8 3v6c0 5-3.4 7.7-8 9-4.6-1.3-8-4-8-9V6l8-3z",
  shieldCheck: "M12 3l8 3v6c0 5-3.4 7.7-8 9-4.6-1.3-8-4-8-9V6l8-3zM9 12l2 2 4-4",
  flask: "M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3M7.5 14h9",
  compass: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM16.2 7.8l-2.5 6.4-6.4 2.5 2.5-6.4 6.4-2.5z",
  radar: "M12 12 19 5M4.9 19.1A10 10 0 1 1 22 12M12 12a4 4 0 1 0 4 4",
  repo: "M4 19.5V5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM19 19H6a2 2 0 0 0-2 2",
  folder: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z",
  lock: "M6 11V8a6 6 0 0 1 12 0v3M5 11h14v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9z",
  globe: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z",
  star: "M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.8 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z",
  branch: "M6 3v12M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 6a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 6a9 9 0 0 1-9 9",
  zap: "M13 2 4 14h7l-1 8 9-12h-7l1-8z",
  alert: "M12 9v4M12 17h.01M10.3 3.2 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.2a2 2 0 0 0-3.4 0z",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
  chevDown: "M6 9l6 6 6-6",
  chevRight: "M9 6l6 6-6 6",
  x: "M6 6l12 12M18 6 6 18",
  plus: "M12 5v14M5 12h14",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
  trendUp: "M3 17l6-6 4 4 8-8M21 7h-6m6 0v6",
  trendDown: "M3 7l6 6 4-4 8 8M21 17h-6m6 0v-6",
  layers: "M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM14 2v6h6",
  terminal: "M4 17l6-6-6-6M12 19h8",
  cpu: "M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3M6 6h12v12H6zM10 10h4v4h-4z",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  sparkles: "M12 3l1.6 4.6L18 9l-4.4 1.4L12 15l-1.6-4.6L6 9l4.4-1.4L12 3zM5 14l.8 2.2L8 17l-2.2.8L5 20l-.8-2.2L2 17l2.2-.8L5 14zM19 13l.7 1.9 1.9.7-1.9.7-.7 1.9-.7-1.9-1.9-.7 1.9-.7.7-1.9z",
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  gauge: "M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM13.4 11.6 17 8M5.5 18a9 9 0 1 1 13 0",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  bell: "M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0",
  code: "M16 18l6-6-6-6M8 6l-6 6 6 6",
  dot: "M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
  refresh: "M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5",
  download: "M12 3v12M7 10l5 5 5-5M5 21h14",
  share: "M4 12v8a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8M16 6l-4-4-4 4M12 2v13",
  filter: "M3 5h18l-7 8v6l-4 2v-8L3 5z",
  pkg: "M21 16V8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  flag: "M4 22V4M4 4h13l-2 4 2 4H4",
  target: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
  rocket: "M12 2c3 1.5 5 5 5 9l-2.5 2.5L12 16l-2.5-2.5L7 11c0-4 2-7.5 5-9zM12 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM9.5 14.5 7 17M14.5 14.5 17 17M9 18l-1 3 3-1",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  key: "M14 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM21 2l-7.5 7.5M16 7l3 3",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  menu: "M3 6h18M3 12h18M3 18h18",
};

function Icon({ name, size = 18, sw = 2, fill = false, style, className }) {
  const d = ICONS[name] || ICONS.dot;
  const solid = name === "github" || name === "play" || name === "star";
  return (
    <svg width={size} height={size} viewBox="0 0 24 24"
      fill={solid || fill ? "currentColor" : "none"}
      stroke={solid ? "none" : "currentColor"} strokeWidth={sw}
      strokeLinecap="round" strokeLinejoin="round"
      style={style} className={className} aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

/* ----------------------------------------------------------------
   LOGO — geometric ShipMate compass mark
----------------------------------------------------------------- */
function LogoMark({ size = 34, glow = true }) {
  const id = useMemo(() => "lg" + Math.random().toString(36).slice(2, 7), []);
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-label="ShipMate"
      style={{ filter: glow ? "drop-shadow(0 6px 16px rgba(37,99,235,0.45))" : "none" }}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3b82f6" /><stop offset="0.55" stopColor="#2563eb" /><stop offset="1" stopColor="#0e7490" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="44" height="44" rx="13" fill={`url(#${id})`} />
      <rect x="2.5" y="2.5" width="43" height="43" rx="12.5" fill="none" stroke="rgba(255,255,255,0.22)" />
      {/* compass ring */}
      <circle cx="24" cy="24" r="13" fill="none" stroke="rgba(255,255,255,0.32)" strokeWidth="1.4" />
      {/* tick marks */}
      {[0, 90, 180, 270].map((a) => (
        <line key={a} x1="24" y1="9.5" x2="24" y2="12.5"
          stroke="rgba(255,255,255,0.7)" strokeWidth="1.6" strokeLinecap="round"
          transform={`rotate(${a} 24 24)`} />
      ))}
      {/* compass needle — north bright, south dim (also reads as a sail/hull) */}
      <polygon points="24,12 28,24 24,21 20,24" fill="#ffffff" />
      <polygon points="24,36 20,24 24,27 28,24" fill="rgba(255,255,255,0.45)" />
      <circle cx="24" cy="24" r="2.1" fill="#0a1326" stroke="#fff" strokeWidth="1.1" />
    </svg>
  );
}

function Wordmark({ size = 18, mark = 34, glow = true }) {
  return (
    <div className="row gap-3" style={{ alignItems: "center" }}>
      <LogoMark size={mark} glow={glow} />
      <span style={{ fontSize: size, fontWeight: 800, letterSpacing: "-0.02em", color: "#fff" }}>
        ShipMate<span style={{ color: "var(--blue-2)" }}> AI</span>
      </span>
    </div>
  );
}

/* ----------------------------------------------------------------
   Shared agent + repo data
----------------------------------------------------------------- */
const AGENTS = [
  { key: "repolens", name: "RepoLens", tone: "emerald", hex: "#10b981", icon: "radar", tag: "Repo Intelligence", sub: "Maps stack, architecture & dependency health" },
  { key: "planforge", name: "PlanForge", tone: "purple", hex: "#8b5cf6", icon: "compass", tag: "Delivery Planning", sub: "Sequences milestones & next best actions" },
  { key: "guardrail", name: "GuardRail", tone: "amber", hex: "#f59e0b", icon: "shieldCheck", tag: "Security Guardrails", sub: "Hunts secrets, CVEs & risky changes" },
  { key: "testpilot", name: "TestPilot", tone: "cyan", hex: "#22d3ee", icon: "flask", tag: "Test Generation", sub: "Generates missing tests & raises coverage" },
];

function scoreColor(s) {
  if (s >= 80) return "#10b981";
  if (s >= 60) return "#3b82f6";
  if (s >= 40) return "#f59e0b";
  return "#ef4444";
}
function scoreTone(s) {
  if (s >= 80) return "emerald";
  if (s >= 60) return "blue";
  if (s >= 40) return "amber";
  return "red";
}

/* ----------------------------------------------------------------
   ScoreRing — animated SVG gauge
----------------------------------------------------------------- */
function ScoreRing({ value = 0, size = 120, stroke = 9, label, sub, animate = true, delay = 200 }) {
  const [v, setV] = useState(animate ? 0 : value);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = scoreColor(value);
  useEffect(() => {
    if (!animate) { setV(value); return; }
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, animate, delay]);
  const off = c - (v / 100) * c;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", filter: `drop-shadow(0 0 10px ${color}55)` }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 1.3s cubic-bezier(.2,.7,.2,1)" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <CountUp to={value} className="" style={{ fontSize: size * 0.3, fontWeight: 800, color: "#fff", lineHeight: 1 }} />
        {label && <div style={{ fontSize: size * 0.1, fontWeight: 700, color, marginTop: 3 }}>{label}</div>}
        {sub && <div style={{ fontSize: 10, color: "var(--ink-3)", marginTop: 1 }}>{sub}</div>}
      </div>
    </div>
  );
}

function CountUp({ to = 0, dur = 1300, className, style, suffix = "" }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf, start;
    const step = (t) => {
      if (!start) start = t;
      const p = Math.min((t - start) / dur, 1);
      const e = 1 - Math.pow(1 - p, 3);
      setN(Math.round(e * to));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [to, dur]);
  return <span className={className} style={style}>{n}{suffix}</span>;
}

/* small generic helpers */
function Badge({ tone = "slate", children, dot, icon }) {
  return (
    <span className={`chip tone-${tone}`}>
      {dot && <span className="dot" style={{ background: "currentColor" }} />}
      {icon && <Icon name={icon} size={12} sw={2.2} />}
      {children}
    </span>
  );
}

function Reveal({ children, delay = 0, style, className = "" }) {
  const ref = useRef(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    let done = false;
    const show = () => { if (!done) { done = true; setSeen(true); } };
    // immediate in-viewport check (scroll container or window)
    const r = el.getBoundingClientRect();
    if (r.top < (window.innerHeight || 900) + 40) { requestAnimationFrame(show); }
    let io;
    try {
      io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { show(); io && io.disconnect(); } }, { threshold: 0.12 });
      io.observe(el);
    } catch (_) {}
    // hard fallback — never leave content invisible
    const t = setTimeout(show, 700 + delay);
    return () => { io && io.disconnect(); clearTimeout(t); };
  }, [delay]);
  return <div ref={ref} className={`reveal ${seen ? "in" : ""} ${className}`} style={{ transitionDelay: `${delay}ms`, ...style }}>{children}</div>;
}

Object.assign(window, { Icon, ICONS, LogoMark, Wordmark, AGENTS, ScoreRing, CountUp, Badge, Reveal, scoreColor, scoreTone });
