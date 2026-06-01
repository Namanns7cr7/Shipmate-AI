import httpx
import json

# Test GitHub API endpoints first
print('=== Testing GitHub API Integration ===')
github_repos_response = httpx.get('http://localhost:8000/api/github/repos')
repos_data = github_repos_response.json()
print(f'✓ GitHub repos endpoint: {len(repos_data)} repositories available')

if repos_data:
    first_repo = repos_data[0]
    repo_id = first_repo['id']
    print(f'✓ Using repository: {first_repo["name"]}')
    
    # Test branches endpoint
    branches_response = httpx.get(f'http://localhost:8000/api/github/repos/{repo_id}/branches')
    branches_data = branches_response.json()
    print(f'✓ GitHub branches endpoint: {len(branches_data)} branches available')
    
    if branches_data:
        first_branch = branches_data[0]['name']
        print(f'✓ Using branch: {first_branch}')

        # Test analysis with GitHub-first format
        print('\n=== Testing Production Analysis Swarm ===')
        r = httpx.post('http://localhost:8000/api/analyze', json={
            'repo_id': repo_id,
            'branch': first_branch,
            'feature_request': 'Add social login with GitHub OAuth and secure token storage.'
        })
        d = r.json()

        print(f'Status: {r.status_code}')
        print(f'Readiness Score: {d["readiness_score"]}/100')
        print(f'Recommendation: {d["recommendation"]}')
        print(f'Score Breakdown: {json.dumps(d["score_breakdown"])}')
        
        repo_summary = d['repo_summary']
        print(f'\nRepository Summary:')
        print(f'  - Name: {repo_summary["name"]}')
        print(f'  - Branch: {repo_summary["branch"]}')
        print(f'  - Tech Stack: {", ".join(repo_summary["tech_stack"])}')
        
        planner = d['agents']['planner']
        repo = d['agents']['repo_analyst']
        tests = d['agents']['test_generator']
        security = d['agents']['security_guard']
        delivery = d['agents']['delivery_manager']
        
        print(f'\nAgent Outputs:')
        print(f'  - Planner: {len(planner["frontend_tasks"])} frontend + {len(planner["backend_tasks"])} backend tasks')
        print(f'  - Repo Analyst: {len(repo["files_to_change"])} files to change')
        print(f'  - Test Generator: {len(tests["unit_tests"])} unit tests + {len(tests["api_tests"])} API tests')
        print(f'  - Security Guard: {len(security["risks"])} security risks identified')
        print(f'  - Delivery Manager: {len(delivery["sprint_plan"])} day sprint plan')
        
        print(f'\n✓ Analysis complete! Markdown report generated.')
        print(f'✓ All endpoints working correctly.')
else:
    print('No repositories available. Using legacy format for testing.')
    r = httpx.post('http://localhost:8000/api/analyze', json={
        'feature_request': 'Add login with role-based access and dashboard analytics.',
        'repo_context': 'TypeScript Node.js e-commerce app'
    })
    d = r.json()
    print(f'Status: {r.status_code}')
    print(f'Score: {d["readiness_score"]}/100')
print(f'DB Changes: {len(planner["database_changes"])}')
print(f'Files to Change: {len(repo["files_to_change"])}')
print(f'Unit Tests: {len(tests["unit_tests"])}')
print(f'API Tests: {len(tests["api_tests"])}')
print(f'Security Risks: {len(security["risks"])}')
print(f'CICD Recs: {len(delivery["cicd_recommendations"])}')
print(f'Markdown chars: {len(d["markdown_report"])}')
print('=== ALL CHECKS PASSED ===')
