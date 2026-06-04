/* ShipMate AI — Repositories + Analysis pages */

/* =================== REPOSITORIES =================== */
function RepoStat({ icon, tone, value, label }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="row gap-3">
        <div style={{ width: 38, height: 38, borderRadius: 11, display: "grid", placeItems: "center", background: `var(--${tone})18`, border: "1px solid var(--line-2)", color: `var(--${tone})` }}>
          <Icon name={icon} size={18} />
        </div>
        <div>
          <div style={{ fontSize: 22, fontWeight: 820, color: "#fff", lineHeight: 1 }}>{value}</div>
          <div className="muted" style={{ fontSize: 11.5, marginTop: 3 }}>{label}</div>
        </div>
      </div>
    </div>
  );
}

function RepositoriesPage({ repos, onAnalyze, onReport, onConnect }) {
  const [q, setQ] = useState("");
  const [lang, setLang] = useState("All");
  const [sort, setSort] = useState("score");

  if (!repos || repos.length === 0) {
    return <PageWrap><EmptyState onConnect={onConnect} /></PageWrap>;
  }

  const analyzed = repos.filter((r) => r.score != null);
  const avg = Math.round(analyzed.reduce((s, r) => s + r.score, 0) / (analyzed.length || 1));
  const openRisks = repos.reduce((s, r) => s + r.risks.critical + r.risks.high, 0);

  let list = repos.filter((r) =>
    (lang === "All" || r.language === lang) &&
    (r.name.toLowerCase().includes(q.toLowerCase()) || r.desc.toLowerCase().includes(q.toLowerCase())));
  list = [...list].sort((a, b) => {
    if (sort === "score") return (b.score ?? -1) - (a.score ?? -1);
    if (sort === "risk") return (b.risks.critical + b.risks.high) - (a.risks.critical + a.risks.high);
    if (sort === "stars") return b.stars - a.stars;
    return a.name.localeCompare(b.name);
  });
  const langs = ["All", ...Array.from(new Set(repos.map((r) => r.language)))];

  return (
    <PageWrap>
      <div className="row between wrap" style={{ marginBottom: 22, gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 25, fontWeight: 840, margin: 0, letterSpacing: "-0.025em" }}>Repositories</h1>
          <p className="muted" style={{ fontSize: 14, margin: "5px 0 0" }}>
            <span className="row gap-2" style={{ display: "inline-flex" }}><Icon name="github" size={14} /> {GH_USER.org} · {repos.length} connected</span>
          </p>
        </div>
        <button className="btn btn-light" onClick={onConnect}><Icon name="plus" size={15} /> Connect Repository</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 18 }}>
        <RepoStat icon="repo" tone="blue" value={repos.length} label="Repositories" />
        <RepoStat icon="checkCircle" tone="emerald" value={analyzed.length} label="Analyzed" />
        <RepoStat icon="gauge" tone="purple" value={avg} label="Avg readiness" />
        <RepoStat icon="alert" tone="red" value={openRisks} label="Open risks" />
      </div>

      <div className="card row gap-3 wrap" style={{ padding: 12, marginBottom: 18 }}>
        <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
          <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--ink-4)" }}><Icon name="search" size={16} /></span>
          <input className="input" style={{ paddingLeft: 36 }} placeholder="Search repositories…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select className="input" style={{ width: "auto", minWidth: 130 }} value={lang} onChange={(e) => setLang(e.target.value)}>
          {langs.map((l) => <option key={l} value={l}>{l === "All" ? "All languages" : l}</option>)}
        </select>
        <select className="input" style={{ width: "auto", minWidth: 150 }} value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="score">Sort: Readiness</option>
          <option value="risk">Sort: Risk</option>
          <option value="stars">Sort: Stars</option>
          <option value="name">Sort: Name</option>
        </select>
      </div>

      <div className="col gap-3">
        {list.map((r, i) => <RepoRiskCard key={r.id} repo={r} onAnalyze={onAnalyze} onReport={onReport} delay={i * 50} />)}
        {list.length === 0 && <div className="card" style={{ padding: 40, textAlign: "center" }} ><span className="muted">No repositories match your filters.</span></div>}
      </div>
    </PageWrap>
  );
}

/* =================== ANALYSIS =================== */
function PipelineRadar({ statuses, active }) {
  const size = 300, c = size / 2, R = 110;
  const positions = AGENTS.map((_, i) => {
    const ang = (-90 + i * 90) * Math.PI / 180;
    return { x: c + R * Math.cos(ang), y: c + R * Math.sin(ang) };
  });
  return (
    <div style={{ position: "relative", width: size, height: size, margin: "0 auto" }}>
      {/* radar rings */}
      {[1, 0.66, 0.33].map((f, i) => (
        <div key={i} className="compass-ring" style={{ width: R * 2 * f, height: R * 2 * f, top: c - R * f, left: c - R * f, borderColor: "rgba(96,165,250,0.14)" }} />
      ))}
      <div style={{ position: "absolute", inset: c - R, width: R * 2, height: R * 2 }}>
        <div className="radar-sweep" style={{ opacity: 0.5 }} />
      </div>
      {/* connector lines */}
      <svg width={size} height={size} style={{ position: "absolute", inset: 0 }}>
        {positions.map((p, i) => (
          <line key={i} x1={c} y1={c} x2={p.x} y2={p.y}
            stroke={statuses[i] !== "pending" ? AGENTS[i].hex : "rgba(255,255,255,0.08)"} strokeWidth="1.5"
            strokeDasharray="3 4" style={{ transition: "stroke .4s", opacity: statuses[i] === "complete" ? 0.8 : statuses[i] === "running" ? 0.6 : 0.3 }} />
        ))}
      </svg>
      {/* center ship report */}
      <div style={{ position: "absolute", left: c - 30, top: c - 30, width: 60, height: 60, borderRadius: 16, display: "grid", placeItems: "center",
        background: "linear-gradient(135deg,#2563eb,#0e7490)", border: "1px solid rgba(255,255,255,0.25)", boxShadow: "0 0 30px rgba(37,99,235,0.6)", animation: "float 3s ease-in-out infinite" }}>
        <Icon name="rocket" size={28} style={{ color: "#fff" }} />
      </div>
      {/* agent nodes */}
      {AGENTS.map((a, i) => {
        const p = positions[i]; const st = statuses[i];
        return (
          <div key={a.key} style={{ position: "absolute", left: p.x - 27, top: p.y - 27, width: 54, height: 54, borderRadius: 15, display: "grid", placeItems: "center",
            background: st === "pending" ? "rgba(255,255,255,0.03)" : `${a.hex}1f`,
            border: `1.5px solid ${st === "pending" ? "var(--line-2)" : a.hex}`,
            color: st === "pending" ? "var(--ink-4)" : a.hex,
            boxShadow: st === "running" ? `0 0 22px ${a.hex}88` : "none",
            transition: "all .4s ease", transform: st === "running" ? "scale(1.12)" : "scale(1)" }}>
            {st === "running" ? <Spinner size={20} color={a.hex} /> : st === "complete" ? <Icon name="check" size={22} /> : <Icon name={a.icon} size={20} />}
          </div>
        );
      })}
    </div>
  );
}

function AnalysisPage({ repo, onComplete, onCancel, live }) {
  const total = LOG_SCRIPT.length;
  const [idx, setIdx] = useState(-1);
  const [logs, setLogs] = useState([]);
  const baseT = useRef(Date.now());

  useEffect(() => {
    if (!live) return;
    setIdx(-1); setLogs([]); baseT.current = Date.now();
    let i = 0;
    const tick = () => {
      const line = LOG_SCRIPT[i];
      const secs = 8 + i * 1; const mm = String(8 + Math.floor((31 + i * 4) / 60)).padStart(2, "0");
      const ss = String((31 + i * 4) % 60).padStart(2, "0");
      setLogs((L) => [...L, { ...line, time: `14:${mm}:${ss}` }]);
      setIdx(i);
      i++;
      if (i >= total) { clearInterval(id); setTimeout(onComplete, 1400); }
    };
    const id = setInterval(tick, 760);
    tick();
    return () => clearInterval(id);
  }, [live]);

  const agentRange = (name) => {
    let first = -1, last = -1;
    LOG_SCRIPT.forEach((l, i) => { if (l.agent === name) { if (first < 0) first = i; last = i; } });
    return [first, last];
  };
  const statusOf = (name) => {
    const [f, l] = agentRange(name);
    if (idx < f) return "pending";
    if (idx > l) return "complete";
    return "running";
  };
  const progressOf = (name) => {
    const [f, l] = agentRange(name);
    if (idx < f) return 0;
    if (idx > l) return 100;
    return Math.round(((idx - f + 1) / (l - f + 1)) * 100);
  };
  const statuses = AGENTS.map((a) => statusOf(a.name));
  const overall = Math.min(100, Math.round(((idx + 1) / total) * 100));
  const activeAgent = AGENTS.find((a) => statusOf(a.name) === "running");

  return (
    <PageWrap>
      <div className="row between wrap" style={{ marginBottom: 22, gap: 12 }}>
        <div>
          <div className="row gap-3">
            <h1 style={{ fontSize: 25, fontWeight: 840, margin: 0, letterSpacing: "-0.025em" }}>{overall >= 100 ? "Analysis Complete" : "Analysis in Progress"}</h1>
            {overall < 100 && <span className="chip tone-blue"><Spinner size={11} /> running</span>}
          </div>
          <p className="muted mono" style={{ fontSize: 13, margin: "6px 0 0" }}>{repo.owner}/{repo.name} · {repo.branch}</p>
        </div>
        <button className="btn btn-danger" onClick={onCancel}><Icon name="x" size={14} /> Cancel Analysis</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 340px", gap: 20 }}>
        {/* center cinematic column */}
        <div className="col gap-4">
          <div className="card glow-border" style={{ position: "relative", overflow: "hidden", padding: "30px 20px" }}>
            <RadarBg sweep={false} rings={false} blobs style={{ opacity: 0.5 }} />
            <div style={{ position: "relative" }}>
              <div className="row center" style={{ marginBottom: 8 }}>
                <span className="pill"><span className="dot dot-pulse" style={{ background: activeAgent ? activeAgent.hex : "#34d399" }} />
                  {activeAgent ? `${activeAgent.name} working…` : overall >= 100 ? "Ship Report ready" : "Initializing crew"}</span>
              </div>
              <PipelineRadar statuses={statuses} />
              <div style={{ marginTop: 20 }}>
                <div className="row between" style={{ marginBottom: 8 }}>
                  <span className="eyebrow">Overall progress</span>
                  <span style={{ fontWeight: 800, fontSize: 16, color: "#fff" }}><CountUp to={overall} dur={400} suffix="%" /></span>
                </div>
                <div className="track" style={{ height: 8 }}><i style={{ width: `${overall}%`, background: "linear-gradient(90deg,#10b981,#3b82f6,#8b5cf6)" }} /></div>
              </div>
            </div>
          </div>

          <LiveActivityLog lines={logs} height={200} title="Agent Activity Log" />
        </div>

        {/* per-agent column */}
        <div className="col gap-3">
          {AGENTS.map((a) => (
            <AgentStatusCard key={a.key} agent={a} status={statusOf(a.name)} progress={progressOf(a.name)} compact
              stats={statusOf(a.name) === "complete" ? [
                { k: a.key === "repolens" ? "deps" : a.key === "guardrail" ? "findings" : a.key === "testpilot" ? "tests" : "steps", v: a.key === "repolens" ? "1.1k" : a.key === "guardrail" ? "6" : a.key === "testpilot" ? "4" : "4" },
                { k: a.key === "guardrail" ? "critical" : "score", v: a.key === "guardrail" ? "1" : String(REPORT.breakdown.find((b) => b.key === a.key)?.score || "—"), color: a.hex },
              ] : null} />
          ))}
        </div>
      </div>
    </PageWrap>
  );
}

Object.assign(window, { RepositoriesPage, AnalysisPage, PipelineRadar });
