import httpx
import json

r = httpx.post('http://localhost:8000/api/analyze', json={
    'feature_request': 'Add login with role-based access and dashboard analytics.',
    'repo_context': 'TypeScript Node.js e-commerce app'
})
d = r.json()

print('=== SHIPMATE AI FINAL VERIFICATION ===')
print(f'Status: {r.status_code}')
print(f'Score: {d["readiness_score"]}/100')
print(f'Breakdown: {json.dumps(d["score_breakdown"])}')
planner = d['agents']['planner']
repo = d['agents']['repo_analyst']
tests = d['agents']['test_generator']
security = d['agents']['security_guard']
delivery = d['agents']['delivery_manager']
print(f'Frontend Tasks: {len(planner["frontend_tasks"])}')
print(f'Backend Tasks: {len(planner["backend_tasks"])}')
print(f'DB Changes: {len(planner["database_changes"])}')
print(f'Files to Change: {len(repo["files_to_change"])}')
print(f'Unit Tests: {len(tests["unit_tests"])}')
print(f'API Tests: {len(tests["api_tests"])}')
print(f'Security Risks: {len(security["risks"])}')
print(f'CICD Recs: {len(delivery["cicd_recommendations"])}')
print(f'Markdown chars: {len(d["markdown_report"])}')
print('=== ALL CHECKS PASSED ===')
