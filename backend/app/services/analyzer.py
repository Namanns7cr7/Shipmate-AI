from app.models.schemas import (
    AnalyzeRequest, AnalyzeResponse, AgentResults,
    PlannerOutput, RepoAnalystOutput, TestGeneratorOutput,
    SecurityGuardOutput, DeliveryManagerOutput
)
from app.agents.planner import run_planner_agent
from app.agents.repo_analyst import run_repo_analyst_agent
from app.agents.test_generator import run_test_generator_agent
from app.agents.security_guard import run_security_guard_agent
from app.agents.delivery_manager import run_delivery_manager_agent
from typing import Dict, Tuple


def calculate_readiness_score(
    planner: PlannerOutput,
    repo_analyst: RepoAnalystOutput,
    test_generator: TestGeneratorOutput,
    security_guard: SecurityGuardOutput,
    delivery_manager: DeliveryManagerOutput
) -> Tuple[int, Dict[str, int]]:
    """
    Calculate production readiness score (0-100) from agent outputs.
    """
    score = 100
    breakdown = {}

    # Task clarity (max deduction: 15)
    total_tasks = (
        len(planner.frontend_tasks) +
        len(planner.backend_tasks) +
        len(planner.database_changes)
    )
    if total_tasks < 3:
        task_deduction = 15
    elif total_tasks < 6:
        task_deduction = 8
    else:
        task_deduction = 0
    score -= task_deduction
    breakdown["task_clarity"] = 30 - task_deduction * 2

    # Test coverage (max deduction: 20)
    coverage = test_generator.total_coverage_estimate
    if coverage < 50:
        test_deduction = 20
    elif coverage < 70:
        test_deduction = 10
    elif coverage < 80:
        test_deduction = 5
    else:
        test_deduction = 0
    score -= test_deduction
    breakdown["test_coverage"] = min(100, coverage)

    # Security risk level (max deduction: 20)
    critical_count = sum(1 for r in security_guard.risks if r.severity == "critical")
    high_count = sum(1 for r in security_guard.risks if r.severity == "high")
    security_deduction = min(20, critical_count * 8 + high_count * 4)
    score -= security_deduction
    breakdown["security_score"] = security_guard.overall_security_score

    # Deployment risk level (max deduction: 15)
    dep_risk_count = len(planner.deployment_risks)
    if dep_risk_count > 5:
        dep_deduction = 15
    elif dep_risk_count > 3:
        dep_deduction = 8
    else:
        dep_deduction = 3
    score -= dep_deduction
    breakdown["deployment_confidence"] = max(0, 100 - dep_risk_count * 10)

    # Repo impact confidence (max deduction: 10)
    high_risk_files = sum(1 for f in repo_analyst.files_to_change if f.risk_level == "high")
    repo_deduction = min(10, high_risk_files * 2)
    score -= repo_deduction
    breakdown["repo_confidence"] = repo_analyst.impact_score

    # CI/CD readiness (max deduction: 10)
    cicd_count = len(delivery_manager.cicd_recommendations)
    cicd_deduction = min(10, cicd_count * 2)
    score -= cicd_deduction
    breakdown["cicd_readiness"] = max(0, 100 - cicd_count * 15)

    final_score = max(0, min(100, score))
    return final_score, breakdown


def generate_markdown_report(
    feature_request: str,
    planner: PlannerOutput,
    repo_analyst: RepoAnalystOutput,
    test_generator: TestGeneratorOutput,
    security_guard: SecurityGuardOutput,
    delivery_manager: DeliveryManagerOutput,
    readiness_score: int
) -> str:
    """Generate a comprehensive Markdown report for export."""

    md = f"""# 🚀 ShipMate AI — Production Readiness Report

> **Feature Request:** {feature_request}

---

## 📊 Production Readiness Score: {readiness_score}/100

| Dimension | Status |
|-----------|--------|
| Task Clarity | {"✅ Clear" if len(planner.frontend_tasks) + len(planner.backend_tasks) >= 6 else "⚠️ Needs work"} |
| Test Coverage | {test_generator.total_coverage_estimate}% estimated |
| Security Risk Level | {"🔴 High" if any(r.severity == "critical" for r in security_guard.risks) else "🟡 Medium"} |
| Deployment Confidence | {"🟡 Moderate" if len(planner.deployment_risks) > 3 else "🟢 Good"} |
| CI/CD Readiness | {"⚠️ Needs setup" if len(delivery_manager.cicd_recommendations) > 3 else "✅ Ready"} |

---

## 📋 Section 1: Implementation Plan

### Frontend Tasks
"""
    for task in planner.frontend_tasks:
        md += f"\n- **[{task.id}]** `{task.priority.upper()}` **{task.title}** ({task.effort} points)\n  {task.description}\n"

    md += "\n### Backend Tasks\n"
    for task in planner.backend_tasks:
        md += f"\n- **[{task.id}]** `{task.priority.upper()}` **{task.title}** ({task.effort} points)\n  {task.description}\n"

    md += "\n### Database Changes\n"
    for task in planner.database_changes:
        md += f"\n- **[{task.id}]** `{task.priority.upper()}` **{task.title}** ({task.effort} points)\n  {task.description}\n"

    md += f"""
### Deployment Risks
"""
    for risk in planner.deployment_risks:
        md += f"\n- {risk}\n"

    md += f"""
---

## 🔍 Section 2: Repo Impact Analysis

**Architecture Notes:** {repo_analyst.architecture_notes}

### Files Requiring Changes
| File | Risk | Change Type | Reason |
|------|------|-------------|--------|
"""
    for f in repo_analyst.files_to_change:
        risk_icon = "🔴" if f.risk_level == "high" else "🟡" if f.risk_level == "medium" else "🟢"
        md += f"| `{f.path}` | {risk_icon} {f.risk_level.upper()} | {f.change_type} | {f.reason} |\n"

    md += "\n### Affected APIs\n"
    for api in repo_analyst.affected_apis:
        md += f"\n- `{api}`\n"

    md += "\n### Risky Dependencies\n"
    for dep in repo_analyst.risky_dependencies:
        md += f"\n- ⚠️ {dep}\n"

    md += "\n### Patterns to Follow\n"
    for pattern in repo_analyst.patterns_to_follow:
        md += f"\n- {pattern}\n"

    md += f"""
---

## 🧪 Section 3: Test Suite

### Unit Tests
"""
    for test in test_generator.unit_tests:
        md += f"\n#### `{test.name}` — {test.type.upper()} | Priority: {test.priority.upper()}\n"
        md += f"{test.description}\n\n**Assertions:**\n"
        for assertion in test.assertions:
            md += f"- [ ] {assertion}\n"

    md += "\n### API Integration Tests\n"
    for test in test_generator.api_tests:
        md += f"\n#### `{test.name}` — {test.type.upper()} | Priority: {test.priority.upper()}\n"
        md += f"{test.description}\n\n**Assertions:**\n"
        for assertion in test.assertions:
            md += f"- [ ] {assertion}\n"

    md += "\n### Edge Cases\n"
    for test in test_generator.edge_cases:
        md += f"\n- **{test.name}**: {test.description}\n"

    md += "\n### Regression Checklist\n"
    for item in test_generator.regression_checklist:
        md += f"\n- {item}\n"

    md += f"""
---

## 🔒 Section 4: Security Risk Report

| ID | Title | Severity | Category |
|----|-------|----------|----------|
"""
    for risk in security_guard.risks:
        sev_icon = "🔴" if risk.severity == "critical" else "🟠" if risk.severity == "high" else "🟡"
        md += f"| {risk.id} | {risk.title} | {sev_icon} {risk.severity.upper()} | {risk.category} |\n"

    md += "\n### Detailed Risk Findings\n"
    for risk in security_guard.risks:
        md += f"""
#### {risk.id}: {risk.title}
- **Severity:** {risk.severity.upper()}
- **Category:** {risk.category}
- **Description:** {risk.description}
- **Recommendation:** {risk.recommendation}
"""
        if risk.cve_reference:
            md += f"- **Reference:** {risk.cve_reference}\n"

    md += "\n### Exposed Secrets Detected\n"
    for secret in security_guard.exposed_secrets:
        md += f"\n- {secret}\n"

    md += "\n### Dependency Vulnerabilities\n"
    for dep in security_guard.dependency_warnings:
        md += f"\n- 🔴 {dep}\n"

    md += f"""
---

## 🚢 Section 5: Release Plan

**Estimated Release:** {delivery_manager.estimated_release_date}
**Release Readiness Score:** {delivery_manager.release_readiness_score}/100

### Sprint Plan
"""
    for sprint in delivery_manager.sprint_plan:
        md += f"\n#### {sprint.day}\n**Owner:** {sprint.owner}\n"
        for task in sprint.tasks:
            md += f"\n- [ ] {task}\n"

    md += f"""
### Standup Summary
{delivery_manager.standup_summary}

### PR Review Summary
{delivery_manager.pr_review_summary}

### CI/CD Recommendations
"""
    for rec in delivery_manager.cicd_recommendations:
        md += f"\n- {rec}\n"

    md += "\n### Next Team Actions\n"
    for action in delivery_manager.next_actions:
        md += f"\n- {action}\n"

    md += """
---

*Generated by ShipMate AI — Agentic Engineering Command Center*
*Reinventing how software teams ship.*
"""
    return md


def run_full_analysis(request: AnalyzeRequest, repo_details: Dict = None) -> AnalyzeResponse:
    """
    Run all 5 agents and compile the final production readiness report.
    
    GitHub-first flow:
    1. Fetch repository details from GitHub Service
    2. Run all 5 agents with repo context
    3. Calculate readiness score
    4. Generate markdown report
    5. Return comprehensive analysis
    """

    feature_request = request.feature_request
    
    # Build repo context from repo details
    repo_context = ""
    if repo_details:
        tech_stack = ", ".join(repo_details.get("tech_stack", []))
        repo_context = f"Repository: {repo_details.get('name', '')}. Tech Stack: {tech_stack}. Language: {repo_details.get('language', '')}."

    # Run agents in sequence (in production, could be parallel)
    planner = run_planner_agent(feature_request, repo_context)
    repo_analyst = run_repo_analyst_agent(feature_request, repo_context)
    test_generator = run_test_generator_agent(feature_request, repo_context)
    security_guard = run_security_guard_agent(feature_request, repo_context)
    delivery_manager = run_delivery_manager_agent(feature_request, repo_context)

    # Calculate score
    readiness_score, score_breakdown = calculate_readiness_score(
        planner, repo_analyst, test_generator, security_guard, delivery_manager
    )

    # Generate markdown report
    markdown_report = generate_markdown_report(
        feature_request, planner, repo_analyst, test_generator,
        security_guard, delivery_manager, readiness_score
    )

    summary = (
        f"ShipMate AI analyzed your feature request and generated a complete production plan. "
        f"Production readiness score: {readiness_score}/100. "
        f"Generated {len(planner.frontend_tasks) + len(planner.backend_tasks) + len(planner.database_changes)} implementation tasks, "
        f"{len(test_generator.unit_tests) + len(test_generator.api_tests) + len(test_generator.edge_cases)} test cases, "
        f"{len(security_guard.risks)} security risks, "
        f"{len(delivery_manager.cicd_recommendations)} CI/CD recommendations, "
        f"and a {delivery_manager.estimated_release_date.split('(')[0].strip()} release plan."
    )
    
    # Determine recommendation
    if readiness_score >= 80:
        recommendation = "Ready to ship"
    elif readiness_score >= 60:
        recommendation = "Needs fixes before shipping"
    else:
        recommendation = "Major issues to address"
    
    # Build repo summary
    repo_summary = {
        "name": repo_details.get("name", "Unknown") if repo_details else "Unknown",
        "branch": request.branch,
        "tech_stack": repo_details.get("tech_stack", []) if repo_details else [],
        "file_count": 42,  # Mock
        "files_to_modify": [f.path for f in repo_analyst.files_to_change],
        "language": repo_details.get("language", "Unknown") if repo_details else "Unknown",
        "stars": repo_details.get("stars", 0) if repo_details else 0,
    }

    return AnalyzeResponse(
        repo_summary=repo_summary,
        agents=AgentResults(
            planner=planner,
            repo_analyst=repo_analyst,
            test_generator=test_generator,
            security_guard=security_guard,
            delivery_manager=delivery_manager
        ),
        readiness_score=readiness_score,
        recommendation=recommendation,
        summary=summary,
        markdown_report=markdown_report,
        score_breakdown=score_breakdown
    )
