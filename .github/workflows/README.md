# GitHub Actions Workflows

This directory contains automated CI/CD workflows for the Stremio HU Live Movies addon.

## Workflows

### 🚀 Build and Push (`build-and-push.yml`)

Builds and publishes Docker images to GitHub Container Registry (ghcr.io).

**Triggers:**
- Push to `main` or `develop` branches
- Tags starting with `v*` (e.g., `v1.0.0`)
- Pull requests to `main`
- Manual workflow dispatch

**What it does:**
1. **Builds Docker image** using multi-stage Dockerfile with BuildKit
2. **Pushes to GitHub Container Registry** (ghcr.io)
3. **Multi-architecture support** - builds for `linux/amd64` and `linux/arm64`
4. **Smart tagging strategy:**
   - Branch names (e.g., `main`, `develop`)
   - Semantic versions (e.g., `v1.2.3`, `1.2`, `1`)
   - Git SHA with branch prefix (e.g., `main-abc1234`)
   - `latest` tag for default branch
5. **Layer caching** via GitHub Actions cache for faster builds
6. **Artifact attestation** for supply chain security
7. **Integration test** - runs container and validates endpoints

**Image location:**
```bash
ghcr.io/radamhu/stremio-musor-tv:latest
```

**Pull the image:**
```bash
docker pull ghcr.io/radamhu/stremio-musor-tv:latest
```

**Optional: Docker Hub support**
To enable Docker Hub publishing, uncomment the Docker Hub login step and add these secrets to your repository:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

---

### 🧪 CI - Tests and Linting (`ci.yml`)

Runs automated tests, linting, and security scans on every push and pull request.

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`
- Manual workflow dispatch

**What it does:**

#### Test Job
- **Python versions:** Tests against Python 3.11 and 3.12
- **Dependency caching** for faster runs
- **Playwright installation** for browser automation tests
- **Code quality checks:**
  - `flake8` - Python linting and error detection
  - `black` - Code formatting validation
  - `isort` - Import statement organization
  - `mypy` - Type checking (non-blocking)
- **Test execution** with `pytest`
  - Coverage reporting
  - XML and terminal output
- **Codecov integration** (optional - requires `CODECOV_TOKEN` secret)

#### Dockerfile Linting
- **Hadolint** - Best practices validation for Dockerfile
- Catches common Docker antipatterns

#### Security Scanning
- **Trivy** - Vulnerability scanning for dependencies and filesystem
- Uploads results to GitHub Security tab
- Checks for CVEs in Python packages and system dependencies

**Requirements:**
- Tests are located in `tests/` directory
- All Python code follows project standards (see `.github/instructions/copilot-instructions.md`)

---

## Setup Requirements

### Repository Secrets

The workflows use the following secrets (most are automatic):

#### Automatic (provided by GitHub)
- `GITHUB_TOKEN` - Automatically provided for GitHub Actions
  - Used for pushing to ghcr.io
  - No setup required

#### Optional (manual setup required)
- `DOCKERHUB_USERNAME` - Docker Hub username (if pushing to Docker Hub)
- `DOCKERHUB_TOKEN` - Docker Hub access token (if pushing to Docker Hub)
- `CODECOV_TOKEN` - Codecov API token (for coverage reporting)

**To add secrets:**
1. Go to repository Settings
2. Navigate to Secrets and variables → Actions
3. Click "New repository secret"
4. Add the secret name and value

### Repository Permissions

Ensure the following permissions are enabled:

1. **Settings → Actions → General → Workflow permissions:**
   - ✅ Read and write permissions
   - ✅ Allow GitHub Actions to create and approve pull requests

2. **Settings → Code security and analysis:**
   - ✅ Enable Dependency graph
   - ✅ Enable Dependabot alerts (recommended)
   - ✅ Enable Code scanning (for Trivy results)

---

## Usage Examples

### Trigger a Manual Build

```bash
# Via GitHub UI
# Go to Actions → Build and Push Docker Image → Run workflow

# Via GitHub CLI
gh workflow run build-and-push.yml
```

### Create a Release

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0

# This will trigger the workflow and create images with tags:
# - v1.0.0
# - 1.0
# - 1
# - latest (if on main branch)
```

### Run Tests Locally

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov flake8 black isort mypy

# Install Playwright
playwright install chromium

# Run linting
flake8 src/
black --check src/
isort --check-only src/
mypy src/ --ignore-missing-imports

# Run tests
pytest tests/ -v --cov=src
```

---

## Workflow Status Badges

Add these badges to your `README.md`:

```markdown
![Build and Push](https://github.com/radamhu/stremio-musor_tv/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)
![CI](https://github.com/radamhu/stremio-musor_tv/workflows/CI%20-%20Tests%20and%20Linting/badge.svg)
```

---

## Troubleshooting

### Build fails with "permission denied"
- Check that workflow permissions are set to "Read and write"
- Ensure GITHUB_TOKEN has access to packages

### Tests fail with Playwright errors
- Playwright browsers are automatically installed in CI
- Check that `playwright install chromium` runs successfully

### Security scan finds vulnerabilities
- Review Trivy results in Security tab
- Update dependencies in `requirements.txt`
- Update base image in `Dockerfile` if needed

### Docker image is too large
- Multi-stage build already optimizes size
- Check for unnecessary files being copied
- Consider `.dockerignore` file

---

## Cache Strategy

### Docker Build Cache
- Uses GitHub Actions cache (`type=gha`)
- Caches Docker layers between builds
- Speeds up rebuilds by ~70%

### Python Dependency Cache
- Uses `actions/setup-python@v5` cache
- Caches pip dependencies
- Automatic cache key based on `requirements.txt`

### Playwright Browser Cache
- Browsers are installed fresh in each run
- Consider adding browser cache in future (adds complexity)

---

## Maintenance

### Updating Workflow Actions
```bash
# Check for updated action versions periodically
# Major versions are pinned (e.g., @v4, @v5) for stability
# Update by changing version numbers in workflow files
```

### Adding New Tests
```bash
# Add test files to tests/ directory
# Follow naming convention: test_*.py
# Use pytest fixtures for setup/teardown
# CI will automatically run new tests
```

### Modifying Docker Build
```bash
# Edit Dockerfile for build changes
# Workflow will automatically pick up changes
# Test locally first: docker build -t test .
```

---

## Related Documentation

- [Copilot Instructions](../instructions/copilot-instructions.md) - Project coding standards
- [Docker Layer Caching](../../docs/DOCKER_LAYER_CACHING_AND_RICH_LOGGING.md) - Build optimization details
- [Render Deployment](../../docs/RENDER_DEPLOYMENT.md) - Production deployment guide

---

**Last Updated:** October 19, 2025  
**Maintained by:** Repository contributors
