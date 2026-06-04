/* ShipMate AI — Reports page (executive) */

function ExecutiveReportHeader({ repo, report, onRerun }) {
  const v = report.verdict;
  const vmap = { "Ready": "#10b981", "Needs Fixes": "#f59e0b", "Blocked": "#ef4444" };
  return (
    <div className="card glow-border" style={{ position: "relative", overflow: "hidden" }}>
      <RadarBg sweep rings blobs={false} style={{ opacity: 0.3 }} />
      <div style={{ position: "relative", display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 28, padding: 26, alignItems: "center" }}>
        <ScoreRing value={report.score} size={130} stroke={10} label={v.toUpperCase()} />
        <div>
          <div className="row gap-2 wrap" style={{ marginBottom: 8 }}>
            <span className="eyebrow">Ship Report</span>
            <span className="mono muted" style={{ fontSize: 11 }}>· {report.scannedAt}</span>
          </div>
          <h1 className="row gap-3 wrap" style={{ fontSize: 26, fontWeight: 840, margin: "0 0 10px", letterSpacing: "-0.025em", alignItems: "center" }}>
            <span className="mono">{repo.owner}/{repo.name}</span>
            <VerdictPill verdict={v} />
          </h1>
          <div className="row gap-3" style={{ padding: "11px 14px", borderRadius: 11, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.22)", maxWidth: 620 }}>
            <span style={{ color: "#f87171", flexShrink: 0 }}><Icon name="alert" size={16} /></span>
            <div><span style={{ fontSize: 11, fontWeight: 700, color: "#fca5a5", marginRight: 8 }}>TOP BLOCKER</span>
              <span style={{ fontSize: 13, color: "var(--ink-2)" }}>{report.topBlocker}</span></div>
          </div>
        </div>
        <div className="col gap-2" style={{ alignSelf: "flex-start" }}>
          <button className="btn btn-secondary btn-sm"><Icon name="download" size={14} /> Download PDF</button>
          <button className="btn btn-secondary btn-sm"><Icon name="share" size={14} /> Share</button>
          <button className="btn btn-primary btn-sm" onClick={onRerun}><Icon name="refresh" size={14} /> Re-run</button>
        </div>
      </div>
    </div>
  );
}

function pTone(p) { return p === "high" || p === "critical" ? "red" : p === "medium" ? "amber" : "blue"; }
const sevTone = { critical: "red", high: "orange", medium: "amber", low: "blue" };

/* ---- Overview ---- */
function OverviewTab({ report }) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  report.guardrail.findings.forEach((f) => counts[f.sev]++);
  return (
    <div className="col gap-4">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
        <div className="card row gap-4" style={{ padding: 20, alignItems: "center" }}>
          <ScoreRing value={report.score} size={92} stroke={8} />
          <div>
            <div className="eyebrow">Readiness</div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#fff", margin: "4px 0" }}>{report.verdict}</div>
            <div className="muted" style={{ fontSize: 12 }}>Synthesized by Ship Report</div>
          </div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <div className="eyebrow" style={{ marginBottom: 12 }}>Verdict</div>
          <VerdictPill verdict={report.verdict} />
          <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.5, margin: "12px 0 0" }}>
            Two security blockers and a coverage gap are holding back deployment. Clear them to reach <b style={{ color: "#34d399" }}>Ready</b>.
          </p>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <div className="eyebrow" style={{ marginBottom: 14 }}>Issues by severity</div>
          <div className="col gap-2">
            {Object.entries(counts).map(([k, n]) => (
              <div key={k} className="row between">
                <span className="row gap-2" style={{ fontSize: 12.5, color: "var(--ink-2)", textTransform: "capitalize" }}>
                  <span className="dot" style={{ background: `var(--${k === "critical" ? "red" : k === "high" ? "orange" : k === "medium" ? "amber" : "blue"})` }} /> {k}
                </span>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: "#fff" }}>{n}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 20 }}>
        <div className="eyebrow" style={{ marginBottom: 18 }}>Score breakdown</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 20 }}>
          {report.breakdown.map((b) => {
            const a = AGENTS.find((x) => x.key === b.key);
            return (
              <div key={b.key} className="col center" style={{ gap: 10 }}>
                <ScoreRing value={b.score} size={84} stroke={7} />
                <div className="row gap-2"><span style={{ color: a.hex }}><Icon name={a.icon} size={14} /></span><span style={{ fontSize: 12.5, fontWeight: 650, color: "var(--ink-2)" }}>{b.label}</span></div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card" style={{ padding: 20 }}>
        <div className="eyebrow" style={{ marginBottom: 16 }}>Recommended actions</div>
        <div className="col gap-2">
          {report.actions.map((a, i) => (
            <div key={i} className="row gap-3" style={{ padding: "12px 14px", borderRadius: 12, background: "rgba(255,255,255,0.02)", border: "1px solid var(--line)" }}>
              <div style={{ width: 26, height: 26, borderRadius: 8, background: "rgba(255,255,255,0.05)", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 12.5, color: "var(--ink-2)", flexShrink: 0 }}>{i + 1}</div>
              <div className="grow" style={{ fontSize: 13.5, color: "var(--ink-2)", lineHeight: 1.45 }}>{a.text}</div>
              <span className={`chip tone-${a.agent === "GuardRail" ? "amber" : a.agent === "TestPilot" ? "cyan" : a.agent === "RepoLens" ? "emerald" : "purple"}`}>{a.agent}</span>
              <span className={`chip tone-${pTone(a.p)}`} style={{ textTransform: "capitalize" }}>{a.p}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---- RepoLens ---- */
function RepoLensTab({ report }) {
  const d = report.repolens;
  return (
    <div className="col gap-4">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div className="card" style={{ padding: 20 }}>
          <div className="eyebrow" style={{ marginBottom: 14 }}>Tech stack</div>
          <div className="row gap-2 wrap">{d.stack.map((s) => <span key={s} className="chip tone-emerald mono">{s}</span>)}</div>
          <div className="eyebrow" style={{ margin: "20px 0 12px" }}>Architecture</div>
          <div className="row gap-2 wrap">
            {d.arch.map((x) => (
              <span key={x.label} className={`chip ${x.on ? "tone-emerald" : "tone-slate"}`}>
                <Icon name={x.on ? "check" : "x"} size={12} /> {x.label}
              </span>
            ))}
          </div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <div className="eyebrow" style={{ marginBottom: 14 }}>Dependencies</div>
          <div className="row" style={{ gap: 12 }}>
            {[["Total", d.deps.total, "blue"], ["Outdated", d.deps.outdated, "amber"], ["Vulnerable", d.deps.vulnerable, "red"]].map(([k, v, t]) => (
              <div key={k} style={{ flex: 1, padding: 14, borderRadius: 12, background: "rgba(255,255,255,0.02)", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: 22, fontWeight: 820, color: `var(--${t})` }}>{v}</div>
                <div className="muted" style={{ fontSize: 11.5, marginTop: 2 }}>{k}</div>
              </div>
            ))}
          </div>
          <div className="eyebrow" style={{ margin: "20px 0 12px" }}>Architecture risks</div>
          <div className="col gap-2">
            {d.risks.map((r, i) => (
              <div key={i} className="row gap-2" style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.5 }}>
                <span style={{ color: "var(--amber)", flexShrink: 0, marginTop: 1 }}><Icon name="alert" size={14} /></span> {r}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- PlanForge ---- */
function PlanForgeTab({ report }) {
  const d = report.planforge;
  return (
    <div className="col gap-4">
      <div className="card row gap-3" style={{ padding: 18, background: "rgba(139,92,246,0.07)", borderColor: "rgba(139,92,246,0.25)" }}>
        <span style={{ color: "var(--purple)", flexShrink: 0 }}><Icon name="compass" size={20} /></span>
        <div><div style={{ fontSize: 11, fontWeight: 700, color: "#c4b5fd", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>Next best action</div>
          <div style={{ fontSize: 14, color: "var(--ink-2)", lineHeight: 1.5 }}>{d.next}</div></div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 14 }}>
        {d.milestones.map((m, i) => (
          <div key={i} className="card card-hover" style={{ padding: 18 }}>
            <div className="row between" style={{ marginBottom: 10 }}>
              <span className="chip tone-purple">{m.cat}</span>
              <span className={`chip tone-${pTone(m.p)}`} style={{ textTransform: "capitalize" }}>{m.p}</span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#fff", lineHeight: 1.35 }}>{m.title}</div>
            <div className="row gap-2 muted" style={{ fontSize: 12, marginTop: 12 }}><Icon name="clock" size={13} /> ~{m.days} days · est.</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- GuardRail ---- */
function GuardRailTab({ report }) {
  return (
    <div className="col gap-3">
      {report.guardrail.findings.map((f, i) => (
        <div key={i} className="card" style={{ padding: 18, borderColor: `var(--${sevTone[f.sev]})44`, background: `linear-gradient(180deg, var(--${sevTone[f.sev]})0a, var(--panel))` }}>
          <div className="row between" style={{ marginBottom: 8 }}>
            <div className="row gap-2">
              <span className={`chip tone-${sevTone[f.sev]}`} style={{ textTransform: "uppercase", fontWeight: 700 }}><Icon name="shield" size={12} /> {f.sev}</span>
              <span style={{ fontSize: 15, fontWeight: 700, color: "#fff" }}>{f.title}</span>
            </div>
            <span className="mono muted" style={{ fontSize: 11.5 }}>{f.file}</span>
          </div>
          <p className="muted" style={{ fontSize: 13, lineHeight: 1.55, margin: "0 0 10px" }}>{f.desc}</p>
          <div className="row gap-2" style={{ fontSize: 13, color: "#6ee7b7" }}>
            <Icon name="arrowRight" size={14} style={{ flexShrink: 0, marginTop: 2 }} />
            <span><b style={{ color: "#a7f3d0" }}>Fix: </b>{f.rec}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- TestPilot ---- */
function TestPilotTab({ report }) {
  const d = report.testpilot;
  return (
    <div className="col gap-4">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
        {[["Tests", d.tests, "cyan", "flask"], ["Coverage", `${d.coverage}%`, "blue", "gauge"], ["QA Status", d.qa, "amber", "alert"]].map(([k, v, t, ic]) => (
          <div key={k} className="card" style={{ padding: 20 }}>
            <div className="row between">
              <div style={{ width: 36, height: 36, borderRadius: 10, background: `var(--${t})18`, border: "1px solid var(--line-2)", color: `var(--${t})`, display: "grid", placeItems: "center" }}><Icon name={ic} size={18} /></div>
              {k === "Coverage" && <span className="chip tone-emerald"><Icon name="trendUp" size={11} /> +{d.delta}%</span>}
            </div>
            <div style={{ fontSize: 24, fontWeight: 820, color: "#fff", marginTop: 14 }}>{v}</div>
            <div className="muted" style={{ fontSize: 11.5, marginTop: 2 }}>{k}</div>
          </div>
        ))}
      </div>
      <div className="card" style={{ padding: 20 }}>
        <div className="eyebrow" style={{ marginBottom: 16 }}>Suggested tests · {d.suggested.length} suites</div>
        <div className="col gap-2">
          {d.suggested.map((t, i) => (
            <div key={i} className="row between wrap" style={{ gap: 10, padding: "13px 14px", borderRadius: 12, background: "rgba(255,255,255,0.02)", border: "1px solid var(--line)" }}>
              <div style={{ minWidth: 0 }}>
                <div className="mono" style={{ fontSize: 13.5, fontWeight: 650, color: "#fff" }}>{t.name}</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 3 }}>{t.desc}</div>
              </div>
              <div className="row gap-2">
                <span className="chip tone-cyan" style={{ textTransform: "uppercase" }}>{t.type}</span>
                <span className={`chip tone-${pTone(t.p)}`} style={{ textTransform: "capitalize" }}>{t.p}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReportsPage({ repo, report, onRerun }) {
  const [tab, setTab] = useState("overview");
  const tabs = [
    { key: "overview", label: "Overview", icon: "grid" },
    { key: "repolens", label: "RepoLens", icon: "radar" },
    { key: "planforge", label: "PlanForge", icon: "compass" },
    { key: "guardrail", label: "GuardRail", icon: "shieldCheck" },
    { key: "testpilot", label: "TestPilot", icon: "flask" },
  ];
  return (
    <PageWrap>
      <ExecutiveReportHeader repo={repo} report={report} onRerun={onRerun} />
      <div className="row gap-4" style={{ borderBottom: "1px solid var(--line)", margin: "22px 0 22px", overflowX: "auto" }}>
        {tabs.map((t) => (
          <button key={t.key} className={`tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
            <span className="row gap-2"><Icon name={t.icon} size={15} /> {t.label}</span>
          </button>
        ))}
      </div>
      <div key={tab} className="anim-up">
        {tab === "overview" && <OverviewTab report={report} />}
        {tab === "repolens" && <RepoLensTab report={report} />}
        {tab === "planforge" && <PlanForgeTab report={report} />}
        {tab === "guardrail" && <GuardRailTab report={report} />}
        {tab === "testpilot" && <TestPilotTab report={report} />}
      </div>
    </PageWrap>
  );
}

Object.assign(window, { ReportsPage, ExecutiveReportHeader });
