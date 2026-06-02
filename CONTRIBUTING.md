# Contributing to ShipMate AI

Thank you for your interest in contributing to ShipMate AI! This document provides guidelines and instructions for contributing to the project.

---

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please treat everyone with respect and professionalism.

---

## Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/Shipmate-AI.git
cd Shipmate-AI
git remote add upstream https://github.com/Namanns7cr7/Shipmate-AI.git
```

### 2. Create a Feature Branch
```bash
git checkout -b feature/my-feature
# or
git checkout -b bugfix/my-bug
```

### 3. Set Up Development Environment

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

---

## Development Workflow

### Code Style

#### Frontend (TypeScript/React)
- **Formatter**: Prettier
- **Linter**: ESLint
- **Setup**: Already configured in `eslint.config.js`

```bash
cd frontend
npm run lint
npm run format  # (if format script exists)
```

#### Backend (Python)
- **Formatter**: Black
- **Import Sorter**: isort

```bash
# Install dev tools
pip install black isort

# Format code
black backend/
isort backend/

# Check
black --check backend/
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add GitHub OAuth support
fix: resolve CORS issue in API
docs: update README with deployment guide
refactor: simplify agent swarm logic
test: add unit tests for security guard
chore: update dependencies
```

---

## Pull Request Process

### Before You Submit

1. **Sync with upstream**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Test your changes**
   ```bash
   # Backend
   cd backend && python verify.py
   
   # Frontend
   cd frontend && npm run build
   ```

3. **Check for conflicts**
   ```bash
   git diff main...HEAD
   ```

### Creating a PR

1. Push to your fork
   ```bash
   git push origin feature/my-feature
   ```

2. Open a Pull Request on GitHub
   - Title: Clear, concise description
   - Description: Explain what, why, and how
   - Link any related issues: `Fixes #123`

3. PR Checklist:
   - [ ] Tests added/updated
   - [ ] Documentation updated
   - [ ] No console errors/warnings
   - [ ] Code formatted correctly
   - [ ] Breaking changes documented

### Review & Merge

- Address review comments promptly
- Discussions happen in PR comments
- Maintainer will merge once approved

---

## Areas for Contribution

### High Priority
- [ ] Real Azure OpenAI integration
- [ ] Real GitHub App OAuth flow
- [ ] Report storage in Azure Blob
- [ ] Database persistence
- [ ] Unit tests

### Medium Priority
- [ ] Enhanced error handling
- [ ] Advanced filtering/search
- [ ] Report templates
- [ ] Export to PDF
- [ ] Dark/light mode toggle

### Low Priority
- [ ] UI polish
- [ ] Additional themes
- [ ] Internationalization (i18n)
- [ ] Accessibility improvements

---

## Adding New Agents

### Backend Structure

1. Create `backend/app/agents/my_agent.py`:
```python
from app.models.schemas import MyAgentOutput
from typing import Optional

def run_my_agent(feature_request: str, repo_context: Optional[str] = None) -> MyAgentOutput:
    """
    My custom agent for analyzing X.
    
    Args:
        feature_request: The user's feature description
        repo_context: Repository context/metadata
    
    Returns:
        MyAgentOutput with analysis results
    """
    
    # Your agent logic here
    results = {
        # ... your output
    }
    
    return MyAgentOutput(**results)
```

2. Add to `schemas.py`:
```python
class MyAgentOutput(BaseModel):
    field1: str
    field2: List[str]
    # ...
```

3. Integrate in `analyzer.py`:
```python
from app.agents.my_agent import run_my_agent

def run_full_analysis(request: AnalyzeRequest, repo_details: Dict = None):
    # ... existing code ...
    my_agent = run_my_agent(feature_request, repo_context)
    # ... add to results ...
```

---

## Adding New Frontend Components

### Component Structure

```typescript
// src/components/MyComponent.tsx
import { motion } from 'framer-motion';

interface MyComponentProps {
  // Your props
}

export function MyComponent({ /* props */ }: MyComponentProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {/* Your component JSX */}
    </motion.div>
  );
}
```

### Best Practices
- Use TypeScript for type safety
- Use Tailwind CSS for styling
- Use Framer Motion for animations
- Keep components focused and reusable
- Document props with JSDoc comments

---

## Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm run test
```

### Integration Tests
```bash
# Run backend
cd backend && python main.py &

# Run frontend dev server
cd frontend && npm run dev &

# Run integration tests
npm run test:e2e
```

---

## Documentation

### Updating README
- Keep it concise and current
- Update Table of Contents
- Include examples
- Link to deployment guide

### Code Comments
- Comment the "why", not the "what"
- Use JSDoc/docstrings for public functions
- Keep comments up to date

### Commit Messages
Link to issues and reference related code:
```bash
git commit -m "feat: implement Azure OpenAI integration

- Add azure_openai_service.py
- Update agent classes to use real LLM
- Add configuration for model selection

Fixes #42"
```

---

## Running Locally

### Full Stack Development

**Terminal 1 - Backend:**
```bash
cd backend
python main.py
# Runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# Runs on http://localhost:5173
```

**Terminal 3 - Testing:**
```bash
cd backend
python verify.py
```

---

## Debugging

### Backend
```python
# Add prints
print(f"Debug: {variable}")

# Or use debugger
import pdb; pdb.set_trace()

# Or use logging
import logging
logger = logging.getLogger(__name__)
logger.info("Debug message")
```

### Frontend
```typescript
// Add console logs
console.log('Debug:', variable);

// Or use React DevTools browser extension
// Or VSCode debugger with launch.json
```

---

## Reporting Issues

### Bug Reports
Include:
- Description of the bug
- Steps to reproduce
- Expected vs. actual behavior
- Your environment (OS, browser, versions)
- Screenshots/logs if applicable

### Feature Requests
Include:
- Clear description of the feature
- Why it would be useful
- Possible implementation approach
- Related issues/PRs

---

## Questions?

- 💬 Open a Discussion on GitHub
- 📧 Email: contribute@shipmate.ai
- 🐛 Report bugs in Issues
- 📖 Check docs at /DEPLOYMENT.md

---

## Acknowledgments

Thank you for helping make ShipMate AI better! 🙏

All contributors are recognized in our [CONTRIBUTORS.md](CONTRIBUTORS.md) file.

---

**Happy coding! 🚀**
