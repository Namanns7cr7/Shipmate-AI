/* ShipMate AI — App shell: Sidebar, Topbar, Connect modal */

const NAV = [
  { key: "dashboard", label: "Dashboard", icon: "grid" },
  { key: "repositories", label: "Repositories", icon: "repo" },
  { key: "analysis", label: "Analysis", icon: "activity" },
  { key: "reports", label: "Reports", icon: "file" },
];

/* ---------------- Repo switcher ---------------- */
function RepoSwitcher({ repos, current, onSelect }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h);
  }, []);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button onClick={() => setOpen((o) => !o)} className="row between" style={{
        width: "100%", padding: "10px 12px", borderRadius: 12, border: "1px solid var(--line)",
        background: "rgba(255,255,255,0.025)", transition: "border-color .2s",
      }} onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--line-2)"} onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--line)"}>
        <div className="row gap-2" style={{ minWidth: 0 }}>
          <div style={{ width: 26, height: 26, borderRadius: 8, background: "linear-gradient(135deg,#2563eb,#0e7490)", display: "grid", placeItems: "center", flexShrink: 0 }}>
            <Icon name={current.private ? "lock" : "repo"} size={13} style={{ color: "#fff" }} />
          </div>
          <div style={{ minWidth: 0, textAlign: "left" }}>
            <div className="mono" style={{ fontSize: 12.5, fontWeight: 650, color: "#fff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{current.name}</div>
            <div style={{ fontSize: 10, color: "var(--ink-3)" }}>{current.owner}</div>
          </div>
        </div>
        <Icon name="chevDown" size={14} style={{ color: "var(--ink-3)", flexShrink: 0, transform: open ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
      </button>
      {open && (
        <div className="card anim-scale" style={{ position: "absolute", top: "calc(100% + 6px)", left: 0, right: 0, zIndex: 60, padding: 6, boxShadow: "var(--shadow)" }}>
          <div className="eyebrow" style={{ padding: "8px 10px 6px" }}>Switch repository</div>
          {repos.map((r) => (
            <button key={r.id} onClick={() => { onSelect(r); setOpen(false); }} className="row between nav-item" style={{ width: "100%", padding: "8px 10px" }}>
              <div className="row gap-2" style={{ minWidth: 0 }}>
                <span className="dot" style={{ background: LANGS[r.language] || "#888" }} />
                <span className="mono" style={{ fontSize: 12.5, color: r.id === current.id ? "#fff" : "var(--ink-2)" }}>{r.name}</span>
              </div>
              {r.id === current.id && <Icon name="check" size={14} style={{ color: "var(--blue-2)" }} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------- Sidebar ---------------- */
function Sidebar({ active, onNav, repos, current, onSelectRepo, hasReport }) {
  return (
    <aside style={{
      width: 248, flexShrink: 0, height: "100vh", position: "sticky", top: 0,
      background: "linear-gradient(180deg, var(--sidebar-top), var(--sidebar-bot))",
      borderRight: "1px solid var(--line)", display: "flex", flexDirection: "column", padding: 16,
    }}>
      <div style={{ padding: "6px 6px 14px" }}><Wordmark size={16.5} mark={32} /></div>

      <RepoSwitcher repos={repos} current={current} onSelect={onSelectRepo} />

      <div className="row gap-2" style={{ margin: "12px 2px 16px", padding: "8px 10px", borderRadius: 10, background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)" }}>
        <Icon name="github" size={15} style={{ color: "#fff" }} />
        <span style={{ fontSize: 11.5, color: "#a7f3d0", fontWeight: 600 }}>Connected to GitHub</span>
        <span className="dot dot-pulse" style={{ background: "#34d399", marginLeft: "auto" }} />
      </div>

      <div className="eyebrow" style={{ padding: "0 8px 8px" }}>Navigate</div>
      <nav className="col gap-1">
        {NAV.map((n) => {
          const disabled = n.key === "reports" && !hasReport;
          return (
            <button key={n.key} className={`nav-item ${active === n.key ? "active" : ""} ${disabled ? "disabled" : ""}`}
              onClick={() => !disabled && onNav(n.key)} aria-disabled={disabled}>
              <Icon name={n.icon} size={17} className="nav-ico" />
              {n.label}
              {n.key === "reports" && !hasReport && <span className="kbd" style={{ marginLeft: "auto", fontSize: 9 }}>locked</span>}
              {active === n.key && <span className="dot" style={{ background: "var(--blue-2)", marginLeft: "auto", boxShadow: "0 0 8px var(--blue-2)" }} />}
            </button>
          );
        })}
      </nav>

      <div style={{ marginTop: "auto" }}>
        <div className="row gap-2" style={{ padding: "9px 11px", borderRadius: 11, background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.18)", marginBottom: 12 }}>
          <span className="dot dot-pulse" style={{ background: "#34d399" }} />
          <span style={{ fontSize: 11.5, fontWeight: 600, color: "#a7f3d0" }}>All Systems Operational</span>
        </div>
        <div className="row between" style={{ padding: "8px 6px" }}>
          <div className="row gap-2">
            <div style={{ width: 32, height: 32, borderRadius: 9, background: "linear-gradient(135deg,#8b5cf6,#3b82f6)", display: "grid", placeItems: "center", fontSize: 12, fontWeight: 700, color: "#fff" }}>{GH_USER.initials}</div>
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 650, color: "#fff" }}>{GH_USER.name}</div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>@{GH_USER.login}</div>
            </div>
          </div>
          <button className="nav-item" style={{ padding: 7 }} title="Sign out"><Icon name="logout" size={15} /></button>
        </div>
      </div>
    </aside>
  );
}

/* ---------------- Topbar ---------------- */
function Topbar({ page, current, onRun, running }) {
  const titles = { dashboard: "Dashboard", repositories: "Repositories", analysis: "Analysis", reports: "Report" };
  return (
    <div style={{
      position: "sticky", top: 0, zIndex: 40, height: 60,
      background: "rgba(7,12,24,0.82)", backdropFilter: "blur(16px)", borderBottom: "1px solid var(--line)",
      display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 28px",
    }}>
      <div className="row gap-3">
        <div className="row gap-2" style={{ fontSize: 13 }}>
          <span className="muted">ShipMate</span>
          <Icon name="chevRight" size={13} style={{ color: "var(--ink-4)" }} />
          <span style={{ color: "#fff", fontWeight: 600 }}>{titles[page]}</span>
        </div>
        <span style={{ width: 1, height: 18, background: "var(--line-2)" }} />
        <div className="row gap-2">
          <span className="mono chip tone-slate"><Icon name="repo" size={12} /> {current.name}</span>
          <span className="mono chip tone-slate"><Icon name="branch" size={12} /> {current.branch}</span>
          <span className="chip tone-slate" style={{ }}><Icon name="clock" size={12} /> {current.lastScan ? `scanned ${current.lastScan}` : "never scanned"}</span>
        </div>
      </div>
      <div className="row gap-3">
        <button className="btn btn-primary btn-sm" onClick={onRun} disabled={running}>
          {running ? <><Spinner size={13} /> Running…</> : <><Icon name="zap" size={14} /> Run Analysis</>}
        </button>
        <button className="nav-item" style={{ padding: 8 }}><Icon name="bell" size={16} /></button>
        <div className="row gap-2 pill" style={{ padding: "5px 5px 5px 11px" }}>
          <span className="dot dot-pulse" style={{ background: "#34d399" }} />
          <span className="mono" style={{ fontSize: 11.5, color: "var(--ink-2)" }}>@{GH_USER.login}</span>
          <div style={{ width: 24, height: 24, borderRadius: 7, background: "linear-gradient(135deg,#8b5cf6,#3b82f6)", display: "grid", placeItems: "center", fontSize: 10, fontWeight: 700, color: "#fff" }}>{GH_USER.initials}</div>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Connect GitHub modal (simulated OAuth) ---------------- */
function ConnectModal({ onClose, onConnected }) {
  const [stage, setStage] = useState("authorize"); // authorize -> authorizing -> fetching -> done
  const authorize = () => {
    setStage("authorizing");
    setTimeout(() => setStage("fetching"), 1100);
    setTimeout(() => { setStage("done"); }, 2600);
    setTimeout(() => onConnected(), 3300);
  };
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(3,6,14,0.72)", backdropFilter: "blur(8px)", display: "grid", placeItems: "center", padding: 20 }} className="anim-in">
      <div onClick={(e) => e.stopPropagation()} className="card glow-border anim-scale" style={{ width: 440, maxWidth: "100%", overflow: "hidden", boxShadow: "var(--shadow)" }}>
        <div className="row between" style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)" }}>
          <div className="row gap-2"><Icon name="github" size={20} style={{ color: "#fff" }} /><span style={{ fontWeight: 700 }}>Authorize ShipMate AI</span></div>
          <button className="nav-item" style={{ padding: 6 }} onClick={onClose}><Icon name="x" size={16} /></button>
        </div>
        <div style={{ padding: 24 }}>
          {stage === "authorize" && (
            <div className="anim-in">
              <div className="row center gap-3" style={{ marginBottom: 22 }}>
                <div style={{ width: 46, height: 46, borderRadius: 13, background: "#0d1117", border: "1px solid var(--line-2)", display: "grid", placeItems: "center" }}><Icon name="github" size={24} style={{ color: "#fff" }} /></div>
                <Icon name="arrowRight" size={18} style={{ color: "var(--ink-3)" }} />
                <LogoMark size={46} />
              </div>
              <p style={{ textAlign: "center", fontSize: 14, color: "var(--ink-2)", margin: "0 0 18px", lineHeight: 1.55 }}>
                ShipMate AI is requesting <b style={{ color: "#fff" }}>read-only</b> access to analyze your repositories.
              </p>
              <div className="col gap-2" style={{ marginBottom: 22 }}>
                {[["repo", "Read code, metadata & commits"], ["shieldCheck", "Scan for secrets & vulnerabilities"], ["eye", "No write access · revoke anytime"]].map(([ic, t]) => (
                  <div key={t} className="row gap-2" style={{ fontSize: 13, color: "var(--ink-2)" }}>
                    <span style={{ color: "#34d399" }}><Icon name="check" size={15} /></span>
                    <Icon name={ic} size={14} style={{ color: "var(--ink-3)" }} /> {t}
                  </div>
                ))}
              </div>
              <button className="btn btn-light" style={{ width: "100%" }} onClick={authorize}><Icon name="github" size={18} /> Authorize &amp; continue</button>
            </div>
          )}
          {stage !== "authorize" && (
            <div className="col center anim-in" style={{ padding: "20px 0", gap: 18 }}>
              {stage === "done" ? <span style={{ color: "#34d399" }}><Icon name="checkCircle" size={48} /></span> : <Spinner size={44} />}
              <div style={{ textAlign: "center" }}>
                <div style={{ fontWeight: 700, fontSize: 16, color: "#fff" }}>
                  {stage === "authorizing" && "Authorizing with GitHub…"}
                  {stage === "fetching" && "Fetching your repositories…"}
                  {stage === "done" && "Connected!"}
                </div>
                <div className="mono muted" style={{ fontSize: 12, marginTop: 6 }}>
                  {stage === "authorizing" && "exchanging oauth token"}
                  {stage === "fetching" && `found ${REPOS.length} repositories in ${GH_USER.org}`}
                  {stage === "done" && "redirecting to your command center"}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { NAV, Sidebar, Topbar, RepoSwitcher, ConnectModal });
