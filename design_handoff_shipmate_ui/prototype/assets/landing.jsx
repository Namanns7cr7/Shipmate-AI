/* ShipMate AI — Landing page */

/* ---- Live hero preview: 4 agents running/completing one by one ---- */
function LiveAgentPreview() {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setPhase((p) => (p + 1) % 9), 950);
    return () => clearInterval(id);
  }, []);
  const statusFor = (i) => phase < i + 1 ? "pending" : phase === i + 1 ? "running" : "complete";
  const done = phase >= 5;
  const completeStats = {
    repolens: "8 deps flagged", planforge: "4 milestones", guardrail: "1 critical", testpilot: "+18% cov",
  };
  return (
    <div className="card glow-border" style={{ padding: 0, overflow: "hidden", boxShadow: "var(--shadow-glow)" }}>
      {/* window chrome */}
      <div className="row between" style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)", background: "rgba(0,0,0,0.2)" }}>
        <div className="row gap-3">
          <Icon name="github" size={16} style={{ color: "var(--ink-2)" }} />
          <span className="mono" style={{ fontSize: 12.5, color: "#fff", fontWeight: 600 }}>northwind-labs/atlas-checkout</span>
          <span className="chip tone-emerald" style={{ fontSize: 10 }}><span className="dot dot-pulse" style={{ background: "#34d399" }} /> connected</span>
        </div>
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>main · a9f3c21</span>
      </div>

      <div style={{ padding: 18, display: "grid", gridTemplateColumns: "1fr 150px", gap: 18 }}>
        {/* agents */}
        <div className="col gap-2">
          <div className="eyebrow" style={{ marginBottom: 2 }}>Agents · live</div>
          {AGENTS.map((a, i) => {
            const st = statusFor(i);
            return (
              <div key={a.key} className="row between" style={{
                padding: "9px 11px", borderRadius: 11, transition: "all .35s ease",
                background: st === "running" ? `${a.hex}14` : "rgba(255,255,255,0.02)",
                border: `1px solid ${st === "pending" ? "var(--line)" : a.hex + "44"}`,
              }}>
                <div className="row gap-2" style={{ minWidth: 0 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 8, display: "grid", placeItems: "center", flexShrink: 0,
                    background: `${a.hex}1c`, color: a.hex, boxShadow: st === "running" ? `0 0 12px ${a.hex}66` : "none" }}>
                    <Icon name={a.icon} size={15} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 650, color: "#fff" }}>{a.name}</div>
                    <div style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
                      {st === "complete" ? completeStats[a.key] : st === "running" ? "working…" : "queued"}
                    </div>
                  </div>
                </div>
                {st === "running" ? <Spinner size={13} color={a.hex} />
                  : st === "complete" ? <span style={{ color: a.hex }}><Icon name="checkCircle" size={16} /></span>
                  : <span className="dot" style={{ background: "var(--ink-4)" }} />}
              </div>
            );
          })}
        </div>

        {/* readiness ring */}
        <div className="col center" style={{ justifyContent: "center", gap: 12 }}>
          <div className="eyebrow">Readiness</div>
          <div style={{ opacity: done ? 1 : 0.3, transition: "opacity .6s" }}>
            <ScoreRing value={done ? 72 : 0} size={120} stroke={9} animate delay={100} />
          </div>
          {done
            ? <VerdictPill verdict="Needs Fixes" />
            : <span className="chip tone-slate"><Spinner size={11} /> computing…</span>}
        </div>
      </div>

      {/* findings strip */}
      <div className="row gap-2 wrap" style={{ padding: "0 18px 18px" }}>
        {[["1 critical", "red"], ["3 high", "orange"], ["6 medium", "amber"], ["61% → 79% coverage", "cyan"]].map(([t, tone]) => (
          <span key={t} className={`chip tone-${tone}`} style={{ opacity: done ? 1 : 0.4, transition: "opacity .5s" }}>{t}</span>
        ))}
      </div>
    </div>
  );
}

/* ---------------- Navbar ---------------- */
function LandingNav({ onConnect, onDemo }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll); return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <header style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 50, height: 68,
      transition: "all .3s ease",
      background: scrolled ? "rgba(7,12,24,0.82)" : "transparent",
      backdropFilter: scrolled ? "blur(16px)" : "none",
      borderBottom: scrolled ? "1px solid var(--line)" : "1px solid transparent",
    }}>
      <div className="row between" style={{ maxWidth: 1200, margin: "0 auto", height: "100%", padding: "0 28px" }}>
        <Wordmark size={18} mark={34} />
        <nav className="row gap-1" style={{ position: "absolute", left: "50%", transform: "translateX(-50%)" }}>
          {["Product", "Agents", "Why ShipMate", "Pricing"].map((l) => (
            <a key={l} href="#" className="btn-ghost" style={{ padding: "8px 13px", borderRadius: 9, border: "none", fontSize: 13.5, fontWeight: 550, color: "var(--ink-3)" }}
              onMouseEnter={(e) => e.currentTarget.style.color = "#fff"} onMouseLeave={(e) => e.currentTarget.style.color = "var(--ink-3)"}>{l}</a>
          ))}
        </nav>
        <div className="row gap-2">
          <button className="btn btn-secondary btn-sm" onClick={onDemo}>Sign in</button>
          <GitHubConnectButton onClick={onConnect} label="Connect GitHub" variant="light" size="btn-sm" />
        </div>
      </div>
    </header>
  );
}

/* ---------------- Hero ---------------- */
function Hero({ onConnect, onDemo }) {
  return (
    <section style={{ position: "relative", paddingTop: 132, paddingBottom: 70, overflow: "hidden" }}>
      <RadarBg sweep rings blobs />
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, transparent 60%, var(--bg))" }} aria-hidden="true" />
      <div style={{ position: "relative", maxWidth: 1200, margin: "0 auto", padding: "0 28px", display: "grid", gridTemplateColumns: "1.05fr 0.95fr", gap: 56, alignItems: "center" }}>
        <div className="anim-up">
          <span className="pill" style={{ marginBottom: 22 }}>
            <span className="dot dot-pulse" style={{ background: "#34d399" }} />
            Agentic Engineering Command Center
          </span>
          <h1 style={{ fontSize: 56, lineHeight: 1.04, fontWeight: 850, letterSpacing: "-0.035em", margin: "0 0 20px" }}>
            Ship <span className="gradient-ink">production-ready</span> code with AI agents
          </h1>
          <p style={{ fontSize: 17.5, lineHeight: 1.6, color: "var(--ink-2)", maxWidth: 520, margin: "0 0 16px" }}>
            Connect GitHub and ShipMate's agents analyze your repo, detect PR &amp; security risks,
            generate the tests you're missing, and return a single deployment-readiness score.
          </p>
          <div className="row gap-2 wrap" style={{ marginBottom: 30 }}>
            {["Connect GitHub", "Analyze repo", "Detect risks", "Generate tests", "Ship readiness"].map((s, i) => (
              <React.Fragment key={s}>
                <span className="mono" style={{ fontSize: 12, color: i === 4 ? "var(--blue-2)" : "var(--ink-3)", fontWeight: 600 }}>{s}</span>
                {i < 4 && <Icon name="arrowRight" size={13} style={{ color: "var(--ink-4)" }} />}
              </React.Fragment>
            ))}
          </div>
          <div className="row gap-3 wrap">
            <GitHubConnectButton onClick={onConnect} label="Connect GitHub" variant="light" size="btn-lg" />
            <button className="btn btn-secondary btn-lg" onClick={onDemo}><Icon name="play" size={15} /> View Demo</button>
          </div>
          <div className="row gap-5 wrap" style={{ marginTop: 26 }}>
            {["No code changes", "Read-only access", "Results in ~90s"].map((t) => (
              <span key={t} className="row gap-2" style={{ fontSize: 12.5, color: "var(--ink-3)" }}>
                <Icon name="check" size={14} style={{ color: "#34d399" }} /> {t}
              </span>
            ))}
          </div>
        </div>
        <div className="anim-up" style={{ animationDelay: ".15s" }}>
          <LiveAgentPreview />
        </div>
      </div>

      {/* workflow band */}
      <div style={{ position: "relative", maxWidth: 1100, margin: "58px auto 0", padding: "0 28px" }}>
        <div className="card" style={{ padding: "22px 20px" }}>
          <div className="eyebrow row center" style={{ marginBottom: 16, gap: 8 }}><Icon name="compass" size={13} /> The ShipMate pipeline</div>
          <WorkflowPipeline autoplay />
        </div>
      </div>
    </section>
  );
}

/* ---------------- Value badges ---------------- */
function ValueBadges() {
  const items = [
    { icon: "branch", label: "PR Risk Detection", tone: "blue" },
    { icon: "shieldCheck", label: "Security Guardrails", tone: "amber" },
    { icon: "flask", label: "Test Generation", tone: "cyan" },
    { icon: "cpu", label: "CI/CD Readiness", tone: "purple" },
    { icon: "gauge", label: "Deployment Score", tone: "emerald" },
  ];
  return (
    <section style={{ maxWidth: 1100, margin: "0 auto", padding: "8px 28px 20px" }}>
      <div className="row center gap-3 wrap">
        {items.map((it, i) => (
          <Reveal key={it.label} delay={i * 60}>
            <div className={`chip tone-${it.tone}`} style={{ padding: "9px 15px", fontSize: 13 }}>
              <Icon name={it.icon} size={15} /> {it.label}
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ---------------- Agents section ---------------- */
function AgentsSection() {
  const cards = [...AGENTS, { key: "ship", name: "Ship Report", tone: "blue", hex: "#60a5fa", icon: "rocket", tag: "Deployment Readiness", sub: "Synthesizes every agent into one go/no-go readiness score." }];
  return (
    <section style={{ maxWidth: 1160, margin: "0 auto", padding: "70px 28px" }}>
      <Reveal>
        <div className="col center" style={{ textAlign: "center", marginBottom: 44 }}>
          <span className="eyebrow" style={{ marginBottom: 12 }}>Five specialists · one crew</span>
          <h2 style={{ fontSize: 38, fontWeight: 820, letterSpacing: "-0.03em", margin: 0 }}>A crew of agents for your codebase</h2>
          <p className="muted" style={{ fontSize: 16, maxWidth: 540, marginTop: 12 }}>Each agent owns one slice of readiness. Together they turn a repo into a deployment decision.</p>
        </div>
      </Reveal>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 16 }}>
        {cards.map((a, i) => (
          <Reveal key={a.key} delay={i * 70}>
            <div className="card card-hover" style={{ padding: 22, height: "100%" }}>
              <div style={{ width: 46, height: 46, borderRadius: 13, display: "grid", placeItems: "center",
                background: `${a.hex}18`, border: `1px solid ${a.hex}44`, color: a.hex, marginBottom: 16 }}>
                <Icon name={a.icon} size={23} />
              </div>
              <div className="row gap-2" style={{ marginBottom: 6 }}>
                <h3 style={{ fontSize: 17, fontWeight: 750, margin: 0 }}>{a.name}</h3>
              </div>
              <div className={`chip tone-${a.tone}`} style={{ marginBottom: 12 }}>{a.tag}</div>
              <p className="muted" style={{ fontSize: 13, lineHeight: 1.6, margin: 0 }}>{a.sub}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ---------------- Why teams section ---------------- */
function WhySection() {
  const cards = [
    { icon: "radar", tone: "emerald", title: "Understand repo health instantly", body: "Connect a repo and get its stack, architecture, dependency risk and coverage mapped in under two minutes — no setup, no config." },
    { icon: "shieldCheck", tone: "amber", title: "Catch risky changes before merge", body: "GuardRail flags exposed secrets, injection paths and CVEs at PR time, so the dangerous diff never reaches production." },
    { icon: "rocket", tone: "blue", title: "Ship with confidence", body: "One readiness score with a clear Ready / Needs Fixes / Blocked verdict — and the exact next action to move the needle." },
  ];
  return (
    <section style={{ position: "relative", padding: "40px 0 80px" }}>
      <div style={{ maxWidth: 1160, margin: "0 auto", padding: "0 28px" }}>
        <Reveal>
          <div className="col center" style={{ textAlign: "center", marginBottom: 44 }}>
            <span className="eyebrow" style={{ marginBottom: 12 }}>Why teams use ShipMate AI</span>
            <h2 style={{ fontSize: 38, fontWeight: 820, letterSpacing: "-0.03em", margin: 0, maxWidth: 600 }}>From repo to deploy decision, without the guesswork</h2>
          </div>
        </Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
          {cards.map((c, i) => (
            <Reveal key={c.title} delay={i * 90}>
              <div className="card card-hover" style={{ padding: 28, height: "100%" }}>
                <div style={{ width: 52, height: 52, borderRadius: 15, display: "grid", placeItems: "center",
                  background: `var(--${c.tone === "blue" ? "blue" : c.tone})18`, border: "1px solid var(--line-2)",
                  color: `var(--${c.tone})`, marginBottom: 20, boxShadow: `0 0 30px var(--${c.tone})22` }}>
                  <Icon name={c.icon} size={26} />
                </div>
                <h3 style={{ fontSize: 20, fontWeight: 760, margin: "0 0 10px", letterSpacing: "-0.02em" }}>{c.title}</h3>
                <p className="muted" style={{ fontSize: 14, lineHeight: 1.65, margin: 0 }}>{c.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------- Final CTA ---------------- */
function FinalCTA({ onConnect }) {
  return (
    <section style={{ position: "relative", padding: "0 28px 90px" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <Reveal>
          <div className="card glow-border" style={{ position: "relative", overflow: "hidden", padding: "60px 40px", textAlign: "center" }}>
            <RadarBg sweep rings blobs={false} style={{ opacity: 0.6 }} />
            <div style={{ position: "relative" }}>
              <div style={{ margin: "0 auto 22px", width: "fit-content" }}><LogoMark size={52} /></div>
              <h2 style={{ fontSize: 40, fontWeight: 840, letterSpacing: "-0.035em", margin: "0 0 14px", lineHeight: 1.08 }}>
                Connect GitHub.<br />Get your readiness score.
              </h2>
              <p className="muted" style={{ fontSize: 16.5, maxWidth: 480, margin: "0 auto 30px", lineHeight: 1.6 }}>
                Point ShipMate at a repository and watch the crew work. Read-only, revocable, and free to try.
              </p>
              <div className="row center gap-3 wrap">
                <GitHubConnectButton onClick={onConnect} label="Connect GitHub" variant="light" size="btn-lg" />
                <span className="row gap-2 muted" style={{ fontSize: 13 }}><Icon name="lock" size={14} /> SOC 2 · read-only scopes</span>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
      <footer className="row between wrap" style={{ maxWidth: 1160, margin: "60px auto 0", padding: "28px 28px 0", borderTop: "1px solid var(--line)", gap: 16 }}>
        <Wordmark size={15} mark={28} glow={false} />
        <span className="muted" style={{ fontSize: 12.5 }}>© 2026 ShipMate AI · Navigate every repo to production.</span>
        <div className="row gap-4">
          {["Docs", "Security", "GitHub"].map((l) => <a key={l} href="#" className="muted" style={{ fontSize: 12.5 }}>{l}</a>)}
        </div>
      </footer>
    </section>
  );
}

/* ---------------- Landing root ---------------- */
function LandingPage({ onConnect, onDemo }) {
  return (
    <div style={{ background: "var(--bg)" }}>
      <LandingNav onConnect={onConnect} onDemo={onDemo} />
      <Hero onConnect={onConnect} onDemo={onDemo} />
      <ValueBadges />
      <AgentsSection />
      <WhySection />
      <FinalCTA onConnect={onConnect} />
    </div>
  );
}

Object.assign(window, { LandingPage, LiveAgentPreview });
