/* ShipMate AI — composite components */

/* ---------------- Radar / compass backdrop ---------------- */
function RadarBg({ sweep = false, rings = true, blobs = true, style }) {
  return (
    <div className="grid-bg" style={{ position: "absolute", inset: 0, overflow: "hidden", ...style }} aria-hidden="true">
      {blobs && <>
        <div className="aurora" style={{ width: 520, height: 520, top: -160, left: -120, background: "radial-gradient(circle, rgba(37,99,235,0.5), transparent 70%)" }} />
        <div className="aurora" style={{ width: 460, height: 460, top: -80, right: -140, background: "radial-gradient(circle, rgba(139,92,246,0.4), transparent 70%)" }} />
        <div className="aurora" style={{ width: 420, height: 420, bottom: -180, left: "38%", background: "radial-gradient(circle, rgba(14,116,144,0.4), transparent 70%)" }} />
      </>}
      {rings && (
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", opacity: 0.5 }}>
          {[260, 460, 680, 920].map((s) => (
            <div key={s} className="compass-ring" style={{ width: s, height: s, top: -s / 2, left: -s / 2 }} />
          ))}
          {sweep && <div style={{ position: "absolute", width: 680, height: 680, top: -340, left: -340 }}>
            <div className="radar-sweep" />
          </div>}
        </div>
      )}
    </div>
  );
}

/* ---------------- GitHub connect button ---------------- */
function GitHubConnectButton({ onClick, label = "Connect GitHub", size = "", loading = false, variant = "light" }) {
  return (
    <button className={`btn ${variant === "light" ? "btn-light" : "btn-primary"} ${size}`} onClick={onClick} disabled={loading}>
      {loading
        ? <span className="row gap-2"><Spinner size={16} dark={variant === "light"} /> Authorizing…</span>
        : <><Icon name="github" size={size === "btn-lg" ? 20 : 18} /> {label}</>}
    </button>
  );
}

function Spinner({ size = 18, color = "currentColor", dark = false }) {
  return (
    <span style={{ width: size, height: size, display: "inline-block", borderRadius: "50%",
      border: `2px solid ${dark ? "rgba(10,19,38,0.2)" : "rgba(255,255,255,0.2)"}`,
      borderTopColor: dark ? "#0a1326" : color, animation: "spin .7s linear infinite" }} />
  );
}

/* ---------------- Workflow pipeline ---------------- */
const PIPE = [
  { key: "repo", name: "GitHub Repo", icon: "github", hex: "#cbd5e1", tone: "slate" },
  ...AGENTS.map(a => ({ key: a.key, name: a.name, icon: a.icon, hex: a.hex, tone: a.tone })),
  { key: "ship", name: "Ship Report", icon: "rocket", hex: "#60a5fa", tone: "blue" },
];

function WorkflowPipeline({ active = -1, compact = false, autoplay = false }) {
  const [step, setStep] = useState(autoplay ? 0 : active);
  useEffect(() => {
    if (!autoplay) { setStep(active); return; }
    const id = setInterval(() => setStep((s) => (s + 1) % (PIPE.length + 2)), 1100);
    return () => clearInterval(id);
  }, [autoplay, active]);
  return (
    <div className="row wrap" style={{ gap: compact ? 6 : 10, justifyContent: "center" }}>
      {PIPE.map((n, i) => {
        const on = autoplay ? i <= step : i <= active;
        const now = autoplay ? i === step : i === active;
        return (
          <React.Fragment key={n.key}>
            <div className="col center" style={{ gap: 7, minWidth: compact ? 58 : 78, transition: "opacity .4s", opacity: on ? 1 : 0.4 }}>
              <div style={{
                width: compact ? 38 : 46, height: compact ? 38 : 46, borderRadius: 13, display: "grid", placeItems: "center",
                background: on ? `${n.hex}1f` : "rgba(255,255,255,0.03)",
                border: `1px solid ${on ? n.hex + "88" : "rgba(255,255,255,0.08)"}`,
                color: on ? n.hex : "var(--ink-4)",
                boxShadow: now ? `0 0 0 4px ${n.hex}22, 0 0 22px ${n.hex}55` : "none",
                transition: "all .4s ease", transform: now ? "scale(1.08)" : "scale(1)",
              }}>
                <Icon name={n.icon} size={compact ? 17 : 21} />
              </div>
              <span style={{ fontSize: compact ? 9.5 : 11, fontWeight: 650, color: on ? "var(--ink-2)" : "var(--ink-4)", textAlign: "center", whiteSpace: "nowrap" }}>{n.name}</span>
            </div>
            {i < PIPE.length - 1 && (
              <div style={{ width: compact ? 16 : 28, height: 2, borderRadius: 2, marginTop: compact ? -16 : -20,
                background: on ? `linear-gradient(90deg, ${n.hex}, ${PIPE[i + 1].hex})` : "rgba(255,255,255,0.08)",
                transition: "all .4s ease", boxShadow: on ? `0 0 8px ${n.hex}66` : "none" }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ---------------- Agent status card ---------------- */
function AgentStatusCard({ agent, status = "pending", progress = 0, stats, compact = false }) {
  const a = agent;
  const statusMap = {
    pending: { label: "Queued", tone: "slate", icon: "clock" },
    running: { label: "Running", tone: a.tone, icon: null },
    complete: { label: "Complete", tone: "emerald", icon: "check" },
  };
  const st = statusMap[status];
  return (
    <div className="card" style={{
      padding: compact ? 14 : 16, borderColor: status !== "pending" ? `${a.hex}40` : "var(--line)",
      background: status === "running" ? `linear-gradient(180deg, ${a.hex}12, var(--panel))` : "var(--panel)",
      transition: "all .4s ease",
    }}>
      <div className="row between" style={{ alignItems: "flex-start" }}>
        <div className="row gap-3">
          <div style={{ width: 38, height: 38, borderRadius: 11, display: "grid", placeItems: "center",
            background: `${a.hex}1c`, border: `1px solid ${a.hex}55`, color: a.hex,
            boxShadow: status === "running" ? `0 0 16px ${a.hex}55` : "none" }}>
            <Icon name={a.icon} size={19} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: "#fff" }}>{a.name}</div>
            <div style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{a.tag}</div>
          </div>
        </div>
        <span className={`chip tone-${st.tone}`}>
          {status === "running" ? <Spinner size={11} /> : st.icon && <Icon name={st.icon} size={12} sw={2.4} />}
          {st.label}
        </span>
      </div>
      {!compact && <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 10, lineHeight: 1.5 }}>{a.sub}</div>}
      {status !== "pending" && (
        <div style={{ marginTop: 12 }}>
          <div className="track"><i style={{ width: `${progress}%`, background: `linear-gradient(90deg, ${a.hex}, ${a.hex}aa)` }} /></div>
        </div>
      )}
      {status === "complete" && stats && (
        <div className="row" style={{ gap: 8, marginTop: 12 }}>
          {stats.map((s, i) => (
            <div key={i} style={{ flex: 1, background: "rgba(0,0,0,0.25)", borderRadius: 9, padding: "8px 10px" }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: s.color || "#fff" }}>{s.v}</div>
              <div style={{ fontSize: 9.5, color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>{s.k}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------- Live activity log ---------------- */
function LiveActivityLog({ lines, title = "Live Activity", height = 230 }) {
  const ref = useRef(null);
  useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [lines]);
  const toneHex = { slate: "#94a3b8", emerald: "#34d399", purple: "#a78bfa", amber: "#fbbf24", cyan: "#22d3ee", red: "#f87171" };
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div className="row between" style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
        <div className="row gap-2">
          <span className="dot dot-pulse" style={{ background: "#34d399" }} />
          <span style={{ fontSize: 12.5, fontWeight: 700, color: "#fff" }}>{title}</span>
        </div>
        <div className="row gap-1" style={{ opacity: 0.4 }}>
          <Icon name="terminal" size={13} /><span className="mono" style={{ fontSize: 11 }}>stream</span>
        </div>
      </div>
      <div ref={ref} className="mono" style={{ height, overflowY: "auto", padding: "12px 16px", fontSize: 12, lineHeight: 1.9, background: "rgba(0,0,0,0.22)" }}>
        {lines.map((l, i) => (
          <div key={i} className="row gap-2 anim-in" style={{ alignItems: "baseline" }}>
            <span style={{ color: "var(--ink-4)", flexShrink: 0 }}>{l.time}</span>
            <span style={{ color: toneHex[l.tone] || "#94a3b8", flexShrink: 0, fontWeight: 600 }}>
              {l.agent === "system" ? "›" : `[${l.agent}]`}
            </span>
            <span style={{ color: l.tone === "red" ? "#fca5a5" : "var(--ink-2)" }}>{l.text}</span>
          </div>
        ))}
        {lines.length === 0 && <div style={{ color: "var(--ink-4)" }}>awaiting agents…</div>}
        <span style={{ display: "inline-block", width: 8, height: 15, background: "#34d399", verticalAlign: "middle", animation: "blink 1s steps(1) infinite" }} />
      </div>
    </div>
  );
}

/* ---------------- Empty state ---------------- */
function EmptyState({ onConnect }) {
  return (
    <div className="card glow-border" style={{ padding: "56px 32px", textAlign: "center", position: "relative", overflow: "hidden" }}>
      <RadarBg sweep rings blobs={false} style={{ opacity: 0.5 }} />
      <div style={{ position: "relative" }}>
        <div style={{ width: 76, height: 76, borderRadius: 22, margin: "0 auto 22px", display: "grid", placeItems: "center",
          background: "rgba(255,255,255,0.04)", border: "1px solid var(--line-2)", boxShadow: "0 0 40px rgba(37,99,235,0.25)" }}>
          <Icon name="github" size={36} style={{ color: "#fff" }} />
        </div>
        <h3 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px", letterSpacing: "-0.02em" }}>Connect a repository to begin</h3>
        <p className="muted" style={{ maxWidth: 420, margin: "0 auto 24px", fontSize: 14, lineHeight: 1.6 }}>
          ShipMate reads your GitHub repos, then runs four agents to score readiness, surface PR risks and generate the tests you're missing.
        </p>
        <div className="row center gap-3 wrap">
          <GitHubConnectButton onClick={onConnect} label="Connect GitHub" size="btn-lg" />
          <span className="pill"><Icon name="lock" size={12} /> Read-only · revoke anytime</span>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Repo risk card ---------------- */
function RepoRiskCard({ repo, onAnalyze, onReport, delay = 0 }) {
  const r = repo;
  const riskTotal = r.risks.critical + r.risks.high;
  return (
    <Reveal delay={delay}>
      <div className="card card-hover" style={{ padding: 18 }}>
        <div className="row between" style={{ alignItems: "flex-start", gap: 16 }}>
          <div className="row gap-3" style={{ alignItems: "flex-start", minWidth: 0 }}>
            <div style={{ width: 42, height: 42, borderRadius: 12, display: "grid", placeItems: "center", flexShrink: 0,
              background: "rgba(255,255,255,0.04)", border: "1px solid var(--line-2)", color: "var(--ink-2)" }}>
              <Icon name={r.private ? "lock" : "repo"} size={18} />
            </div>
            <div style={{ minWidth: 0 }}>
              <div className="row gap-2" style={{ flexWrap: "wrap" }}>
                <span className="mono" style={{ fontWeight: 700, fontSize: 14.5, color: "#fff" }}>{r.name}</span>
                <span className={`chip ${r.private ? "tone-slate" : "tone-emerald"}`}>{r.private ? "Private" : "Public"}</span>
              </div>
              <p className="muted" style={{ fontSize: 12.5, margin: "5px 0 0", lineHeight: 1.5, maxWidth: 420 }}>{r.desc}</p>
              <div className="row gap-3 wrap" style={{ marginTop: 11 }}>
                <span className="row gap-1" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
                  <span className="dot" style={{ background: LANGS[r.language] }} /> {r.language}
                </span>
                <span className="row gap-1" style={{ fontSize: 11.5, color: "var(--ink-3)" }}><Icon name="star" size={12} /> {r.stars}</span>
                <span className="row gap-1 mono" style={{ fontSize: 11.5, color: "var(--ink-3)" }}><Icon name="branch" size={12} /> {r.branch}</span>
                {r.lastScan
                  ? <span className="row gap-1" style={{ fontSize: 11.5, color: "var(--ink-3)" }}><Icon name="clock" size={12} /> {r.lastScan}</span>
                  : <span className="chip tone-blue">Not analyzed</span>}
              </div>
            </div>
          </div>
          {r.score != null && (
            <div className="col center" style={{ flexShrink: 0 }}>
              <ScoreRing value={r.score} size={62} stroke={6} delay={delay + 200} />
              {riskTotal > 0 && <span className="chip tone-red" style={{ marginTop: 8 }}><Icon name="alert" size={11} /> {riskTotal} risks</span>}
            </div>
          )}
        </div>
        <div className="row between" style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid var(--line)" }}>
          <div className="row gap-2">
            {r.verdict && <VerdictPill verdict={r.verdict} small />}
            {r.prRisk && <span className="chip tone-slate"><Icon name="branch" size={11} /> PR risk: {r.prRisk}</span>}
          </div>
          <div className="row gap-2">
            {r.score != null && <button className="btn btn-ghost btn-sm" onClick={() => onReport(r)}>View Report</button>}
            <button className="btn btn-primary btn-sm" onClick={() => onAnalyze(r)}><Icon name="zap" size={14} /> {r.score != null ? "Re-analyze" : "Analyze"}</button>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

function VerdictPill({ verdict, small }) {
  const map = {
    "Ready": { tone: "emerald", icon: "checkCircle" },
    "Needs Fixes": { tone: "amber", icon: "alert" },
    "Blocked": { tone: "red", icon: "x" },
  };
  const m = map[verdict] || map["Needs Fixes"];
  return <span className={`chip tone-${m.tone}`} style={small ? {} : { fontSize: 12, padding: "5px 11px" }}><Icon name={m.icon} size={small ? 11 : 13} /> {verdict}</span>;
}

Object.assign(window, { RadarBg, GitHubConnectButton, Spinner, WorkflowPipeline, PIPE, AgentStatusCard, LiveActivityLog, EmptyState, RepoRiskCard, VerdictPill });
