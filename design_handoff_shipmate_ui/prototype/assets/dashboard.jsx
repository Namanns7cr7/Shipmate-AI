/* ShipMate AI — Dashboard page */

function PageWrap({ children }) {
  return <div className="anim-up" style={{ padding: "28px 32px", maxWidth: 1180, margin: "0 auto" }}>{children}</div>;
}

function DeploymentReadinessCard({ repo, report, onView }) {
  const verdict = report.verdict;
  const vmap = {
    "Ready": { tone: "emerald", hex: "#10b981", icon: "checkCircle", line: "Cleared for deployment." },
    "Needs Fixes": { tone: "amber", hex: "#f59e0b", icon: "alert", line: "Address blockers before you ship." },
    "Blocked": { tone: "red", hex: "#ef4444", icon: "x", line: "Critical issues must be resolved." },
  };
  const v = vmap[verdict];
  return (
    <div className="card glow-border" style={{ position: "relative", overflow: "hidden", padding: 0 }}>
      <RadarBg sweep rings blobs={false} style={{ opacity: 0.35 }} />
      <div style={{ position: "relative", display: "grid", gridTemplateColumns: "auto 1fr", gap: 32, padding: 28, alignItems: "center" }}>
        <div className="col center" style={{ gap: 14, paddingRight: 28, borderRight: "1px solid var(--line)" }}>
          <div className="eyebrow">Deployment Readiness</div>
          <ScoreRing value={report.score} size={158} stroke={11} label={verdict.toUpperCase()} />
          <div className="row gap-2 mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
            <Icon name="branch" size={12} /> {report.branch} · {report.commit}
          </div>
        </div>
        <div className="col gap-4">
          <div className="row between wrap" style={{ gap: 12 }}>
            <div>
              <div className="row gap-2" style={{ marginBottom: 6 }}>
                <span style={{ color: v.hex }}><Icon name={v.icon} size={22} /></span>
                <h2 style={{ fontSize: 26, fontWeight: 820, margin: 0, letterSpacing: "-0.02em" }}>{verdict}</h2>
              </div>
              <p className="muted" style={{ fontSize: 14, margin: 0 }}>{v.line} <span className="mono">{repo.owner}/{repo.name}</span></p>
            </div>
            <button className="btn btn-primary" onClick={onView}><Icon name="file" size={15} /> Open Ship Report</button>
          </div>

          {/* top blocker */}
          <div className="row gap-3" style={{ padding: "12px 14px", borderRadius: 12, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.22)" }}>
            <span style={{ color: "#f87171", flexShrink: 0, marginTop: 1 }}><Icon name="alert" size={17} /></span>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#fca5a5", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>Top Blocker · GuardRail</div>
              <div style={{ fontSize: 13.5, color: "var(--ink-2)", lineHeight: 1.5 }}>{report.topBlocker}</div>
            </div>
          </div>

          {/* breakdown bars */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
            {report.breakdown.map((b) => {
              const a = AGENTS.find((x) => x.key === b.key);
              return (
                <div key={b.key}>
                  <div className="row between" style={{ marginBottom: 7 }}>
                    <span className="row gap-1" style={{ fontSize: 11.5, color: "var(--ink-2)", fontWeight: 600 }}>
                      <span style={{ color: a.hex }}><Icon name={a.icon} size={13} /></span> {b.label}
                    </span>
                    <span style={{ fontSize: 12.5, fontWeight: 700, color: scoreColor(b.score) }}>{b.score}</span>
                  </div>
                  <div className="track"><i style={{ width: `${b.score}%`, background: a.hex }} /></div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function AgentSummaryRow({ report }) {
  const data = {
    repolens: { stat: `${report.repolens.deps.vulnerable} vuln`, sub: `${report.repolens.deps.outdated} outdated deps`, score: 81 },
    planforge: { stat: `${report.planforge.milestones.length} milestones`, sub: "critical path mapped", score: 74 },
    guardrail: { stat: `${report.guardrail.findings.length} findings`, sub: "1 critical · 3 high", score: 58 },
    testpilot: { stat: `${report.testpilot.coverage}% cov`, sub: `+${report.testpilot.delta}% achievable`, score: 66 },
  };
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
      {AGENTS.map((a, i) => {
        const d = data[a.key];
        return (
          <Reveal key={a.key} delay={i * 60}>
            <div className="card card-hover" style={{ padding: 18, height: "100%" }}>
              <div className="row between">
                <div style={{ width: 38, height: 38, borderRadius: 11, display: "grid", placeItems: "center", background: `${a.hex}18`, border: `1px solid ${a.hex}44`, color: a.hex }}>
                  <Icon name={a.icon} size={19} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: scoreColor(d.score) }}>{d.score}<span className="muted" style={{ fontSize: 10 }}>/100</span></span>
              </div>
              <div style={{ fontSize: 14.5, fontWeight: 700, color: "#fff", marginTop: 14 }}>{a.name}</div>
              <div style={{ fontSize: 19, fontWeight: 820, color: a.hex, marginTop: 6 }}>{d.stat}</div>
              <div className="muted" style={{ fontSize: 11.5, marginTop: 2 }}>{d.sub}</div>
            </div>
          </Reveal>
        );
      })}
    </div>
  );
}

function RecentAnalysesTable({ repos, onAnalyze, onReport }) {
  const analyzed = repos.filter((r) => r.score != null);
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div className="row between" style={{ padding: "16px 18px", borderBottom: "1px solid var(--line)" }}>
        <div className="row gap-2"><Icon name="list" size={16} style={{ color: "var(--ink-2)" }} /><span style={{ fontWeight: 700, fontSize: 14.5 }}>Recent Analyses</span></div>
        <button className="btn btn-ghost btn-sm" onClick={() => onReport()}>View all</button>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="tbl">
          <thead><tr>
            <th>Repository</th><th>Score</th><th>Verdict</th><th>Risks</th><th>Coverage</th><th>Last scan</th><th></th>
          </tr></thead>
          <tbody>
            {analyzed.map((r) => (
              <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => onReport(r)}>
                <td>
                  <div className="row gap-2">
                    <Icon name={r.private ? "lock" : "repo"} size={14} style={{ color: "var(--ink-3)" }} />
                    <span className="mono" style={{ fontWeight: 600, color: "#fff" }}>{r.name}</span>
                  </div>
                </td>
                <td><span style={{ fontWeight: 800, color: scoreColor(r.score) }}>{r.score}</span></td>
                <td><VerdictPill verdict={r.verdict} small /></td>
                <td>
                  <div className="row gap-1">
                    {r.risks.critical > 0 && <span className="chip tone-red" style={{ padding: "2px 7px" }}>{r.risks.critical}C</span>}
                    {r.risks.high > 0 && <span className="chip tone-orange" style={{ padding: "2px 7px" }}>{r.risks.high}H</span>}
                    {r.risks.critical === 0 && r.risks.high === 0 && <span className="chip tone-emerald" style={{ padding: "2px 7px" }}>clean</span>}
                  </div>
                </td>
                <td><span className="mono" style={{ color: r.coverage >= 70 ? "#34d399" : "var(--ink-2)" }}>{r.coverage}%</span></td>
                <td><span className="muted mono" style={{ fontSize: 12 }}>{r.lastScan}</span></td>
                <td><button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); onAnalyze(r); }}><Icon name="refresh" size={13} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AIInsightsPanel({ repo, report, onView }) {
  const top = report.guardrail.findings[0];
  const days = [40, 62, 55, 71, 58, 66, 72];
  return (
    <div className="col gap-4">
      <div className="card" style={{ padding: 18 }}>
        <div className="row gap-2" style={{ marginBottom: 14 }}>
          <span style={{ color: "var(--purple)" }}><Icon name="sparkles" size={17} /></span>
          <span style={{ fontWeight: 700, fontSize: 14.5 }}>AI Insights</span>
        </div>
        <div style={{ padding: 14, borderRadius: 12, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.22)", marginBottom: 14 }}>
          <div className="row between" style={{ marginBottom: 8 }}>
            <span className="chip tone-red"><Icon name="alert" size={12} /> Highest risk</span>
            <span className="mono muted" style={{ fontSize: 11 }}>{top.file}</span>
          </div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", marginBottom: 5 }}>{top.title}</div>
          <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.5, margin: 0 }}>{top.desc}</p>
        </div>
        <div style={{ padding: 14, borderRadius: 12, background: "rgba(59,130,246,0.07)", border: "1px solid rgba(59,130,246,0.2)" }}>
          <div className="row gap-2" style={{ marginBottom: 6 }}>
            <span style={{ color: "var(--blue-2)" }}><Icon name="target" size={14} /></span>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#93c5fd", textTransform: "uppercase", letterSpacing: "0.05em" }}>Next action</span>
          </div>
          <p style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.5, margin: "0 0 12px" }}>{top.rec}</p>
          <button className="btn btn-primary btn-sm" style={{ width: "100%" }} onClick={onView}>View full analysis <Icon name="arrowRight" size={14} /></button>
        </div>
      </div>

      <div className="card" style={{ padding: 18 }}>
        <div className="row between" style={{ marginBottom: 14 }}>
          <span style={{ fontWeight: 700, fontSize: 13.5 }}>Readiness trend</span>
          <span className="chip tone-emerald"><Icon name="trendUp" size={12} /> +12 this week</span>
        </div>
        <div className="row" style={{ gap: 8, height: 70, alignItems: "flex-end" }}>
          {days.map((d, i) => (
            <div key={i} style={{ flex: 1, height: `${d}%`, borderRadius: "5px 5px 2px 2px",
              background: i === days.length - 1 ? "linear-gradient(180deg,#60a5fa,#2563eb)" : "rgba(59,130,246,0.22)",
              boxShadow: i === days.length - 1 ? "0 0 14px rgba(59,130,246,0.5)" : "none", transition: "height .6s ease" }} />
          ))}
        </div>
        <div className="row between mono" style={{ marginTop: 8, fontSize: 10, color: "var(--ink-4)" }}>
          {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => <span key={i}>{d}</span>)}
        </div>
      </div>
    </div>
  );
}

function DashboardPage({ repo, report, repos, onNav, onAnalyze, onReport }) {
  return (
    <PageWrap>
      <div className="row between wrap" style={{ marginBottom: 22, gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 25, fontWeight: 840, margin: 0, letterSpacing: "-0.025em" }}>Good afternoon, {GH_USER.name.split(" ")[0]}</h1>
          <p className="muted" style={{ fontSize: 14, margin: "5px 0 0" }}>Here's the readiness picture across your connected repositories.</p>
        </div>
        <button className="btn btn-secondary" onClick={() => onReport(repo)}><Icon name="file" size={15} /> View Reports</button>
      </div>

      <div className="col gap-5">
        <DeploymentReadinessCard repo={repo} report={report} onView={() => onReport(repo)} />
        <AgentSummaryRow report={report} />
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.7fr) minmax(0,1fr)", gap: 20 }}>
          <RecentAnalysesTable repos={repos} onAnalyze={onAnalyze} onReport={(r) => onReport(r || repo)} />
          <AIInsightsPanel repo={repo} report={report} onView={() => onReport(repo)} />
        </div>
      </div>
    </PageWrap>
  );
}

Object.assign(window, { DashboardPage, PageWrap, DeploymentReadinessCard, AIInsightsPanel });
