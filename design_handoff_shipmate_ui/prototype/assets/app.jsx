/* ShipMate AI — root app: routing + state */

function buildReport(repo) {
  if (!repo || repo.id === "atlas-checkout") return REPORT;
  const score = repo.score ?? 72;
  const verdict = repo.verdict ?? "Needs Fixes";
  const ratio = score / 72;
  const blockers = {
    "Ready": "No blockers — all guardrails passed. Cleared for deployment.",
    "Needs Fixes": REPORT.topBlocker,
    "Blocked": "Critical findings detected — deployment blocked until resolved.",
  };
  return {
    ...REPORT, repo: repo.name, branch: repo.branch, score, verdict,
    topBlocker: blockers[verdict] || REPORT.topBlocker,
    breakdown: REPORT.breakdown.map((b) => ({ ...b, score: Math.max(20, Math.min(98, Math.round(b.score * ratio))) })),
  };
}

function App() {
  const [view, setView] = useState("landing");          // landing | app
  const [showConnect, setShowConnect] = useState(false);
  const [page, setPage] = useState("dashboard");
  const [repos, setRepos] = useState(REPOS);
  const [currentRepo, setCurrentRepo] = useState(REPOS[0]);  // topbar / analysis target
  const [reportRepo, setReportRepo] = useState(REPOS[0]);    // dashboard + report focus
  const [analyzeRepo, setAnalyzeRepo] = useState(REPOS[0]);
  const [analyzing, setAnalyzing] = useState(false);
  const [hasReport, setHasReport] = useState(true);

  const report = useMemo(() => buildReport(reportRepo), [reportRepo, repos]);
  const dashRepo = reportRepo.score != null ? reportRepo : REPOS[0];
  const dashReport = useMemo(() => buildReport(dashRepo), [dashRepo, repos]);

  useEffect(() => {
    const root = document.querySelector(".app-scroll");
    if (root) root.scrollTo({ top: 0 });
    window.scrollTo({ top: 0 });
  }, [page, view]);

  const enterApp = () => { setShowConnect(false); setView("app"); setPage("dashboard"); };
  const onDemo = () => { setView("app"); setPage("dashboard"); };

  const startAnalysis = (repo) => {
    const r = repo || currentRepo;
    setAnalyzeRepo(r); setCurrentRepo(r);
    setAnalyzing(true); setPage("analysis");
  };
  const completeAnalysis = () => {
    setAnalyzing(false);
    setRepos((rs) => rs.map((r) => r.id === analyzeRepo.id
      ? { ...r, score: r.score ?? 72, verdict: r.verdict ?? "Needs Fixes", lastScan: "just now",
          coverage: r.coverage ?? 61, coverageDelta: 18, prRisk: r.prRisk ?? "High",
          risks: (r.risks.critical + r.risks.high + r.risks.medium + r.risks.low) === 0 ? { critical: 1, high: 3, medium: 6, low: 4 } : r.risks }
      : r));
    setReportRepo((prev) => ({ ...analyzeRepo, score: analyzeRepo.score ?? 72, verdict: analyzeRepo.verdict ?? "Needs Fixes" }));
    setHasReport(true); setPage("reports");
  };
  const cancelAnalysis = () => { setAnalyzing(false); setPage("repositories"); };

  const openReport = (repo) => {
    const r = repo && repo.score != null ? repo : reportRepo;
    setReportRepo(r); setHasReport(true); setPage("reports");
  };

  if (view === "landing") {
    return (
      <>
        <LandingPage onConnect={() => setShowConnect(true)} onDemo={onDemo} />
        {showConnect && <ConnectModal onClose={() => setShowConnect(false)} onConnected={enterApp} />}
      </>
    );
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar active={page} onNav={setPage} repos={repos} current={currentRepo}
        onSelectRepo={(r) => { setCurrentRepo(r); if (r.score != null) setReportRepo(r); }} hasReport={hasReport} />
      <div className="app-scroll" style={{ flex: 1, height: "100vh", overflowY: "auto" }}>
        <Topbar page={page} current={currentRepo} onRun={() => startAnalysis(currentRepo)} running={analyzing} />
        <div className="grid-bg" style={{ minHeight: "calc(100vh - 60px)" }}>
          {page === "dashboard" && <DashboardPage repo={dashRepo} report={dashReport} repos={repos}
            onNav={setPage} onAnalyze={startAnalysis} onReport={openReport} />}
          {page === "repositories" && <RepositoriesPage repos={repos} onAnalyze={startAnalysis}
            onReport={openReport} onConnect={() => setShowConnect(true)} />}
          {page === "analysis" && <AnalysisPage repo={analyzeRepo} live={analyzing}
            onComplete={completeAnalysis} onCancel={cancelAnalysis} />}
          {page === "reports" && <ReportsPage repo={reportRepo} report={report} onRerun={() => startAnalysis(reportRepo)} />}
        </div>
      </div>
      {showConnect && <ConnectModal onClose={() => setShowConnect(false)} onConnected={() => setShowConnect(false)} />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
