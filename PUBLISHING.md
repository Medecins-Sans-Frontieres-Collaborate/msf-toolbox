# MSF Toolbox Publishing System

## Overview

The package uses a modern, automated publishing pipeline with two paths:

1. **Automated (Recommended)**: Label-based version bumping triggers automatic releases
2. **Manual**: Direct script-based publishing using twine

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   PR Merged to main                                                 │
│   (with bump:patch/minor/major label)                               │
│            │                                                        │
│            ▼                                                        │
│   ┌─────────────────────┐                                           │
│   │  auto-version.yml   │ ─── Creates tag + GitHub Release         │
│   └─────────────────────┘                                           │
│            │                                                        │
│            ▼  (triggers on: release published)                      │
│   ┌─────────────────────┐                                           │
│   │    publish.yml      │                                           │
│   │  ┌───────────────┐  │                                           │
│   │  │validate-version│  │ ── Checks setuptools_scm matches tag     │
│   │  └───────────────┘  │                                           │
│   │         │           │                                           │
│   │         ▼           │                                           │
│   │  ┌───────────────┐  │                                           │
│   │  │    build      │  │ ── Builds wheel + sdist                   │
│   │  └───────────────┘  │                                           │
│   │         │           │                                           │
│   │         ▼           │                                           │
│   │  ┌───────────────┐  │                                           │
│   │  │  TestPyPI     │  │ ── Publishes to test.pypi.org             │
│   │  └───────────────┘  │                                           │
│   │         │           │                                           │
│   │         ▼           │                                           │
│   │  ┌───────────────┐  │                                           │
│   │  │ Test Install  │  │ ── Verifies install on Python 3.10-3.12   │
│   │  │ (matrix)      │  │                                           │
│   │  └───────────────┘  │                                           │
│   │         │           │                                           │
│   │         ▼           │                                           │
│   │  ┌───────────────┐  │                                           │
│   │  │    PyPI       │  │ ── Publishes to pypi.org                  │
│   │  └───────────────┘  │                                           │
│   │         │           │                                           │
│   │         ▼           │                                           │
│   │  ┌───────────────┐  │                                           │
│   │  │  Changelog    │  │ ── Updates release notes                  │
│   │  └───────────────┘  │                                           │
│   └─────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, uses `setuptools_scm` for dynamic versioning |
| `.github/workflows/ci.yml` | Runs tests on push/PR (multi-OS, Python 3.11) |
| `.github/workflows/auto-version.yml` | Creates releases from labeled PRs |
| `.github/workflows/publish.yml` | Builds and publishes to PyPI |
| `scripts/publish.py` | Manual publishing script |
| `scripts/validate_version.py` | Validates version consistency |

## Versioning Strategy

The package uses **`setuptools_scm`** for automatic versioning derived from git tags:

```toml
[tool.setuptools_scm]
write_to = "src/msftoolbox/_version.py"
version_scheme = "post-release"
local_scheme = "dirty-tag"
```

- No hardcoded version in `pyproject.toml` (uses `dynamic = ["version"]`)
- Version is extracted from git tags at build time
- Tags follow `vX.Y.Z` format (e.g., `v0.2.1`)

---

## Deployment Instructions

### Method 1: Fully Automated (GitHub UI Only)

This method requires no local git commands beyond your normal development workflow.

1. **Create a PR** with your changes to `main` (via GitHub UI or local git)

2. **Add a version label** to the PR in GitHub:
   - `bump:patch` - Bug fixes (0.2.0 → 0.2.1)
   - `bump:minor` - New features (0.2.0 → 0.3.0)
   - `bump:major` - Breaking changes (0.2.0 → 1.0.0)

3. **Merge the PR** - This triggers the full pipeline automatically:
   - `auto-version.yml` calculates new version and creates GitHub release
   - `publish.yml` builds and publishes to TestPyPI first, then PyPI

4. **Verify** at https://pypi.org/project/msftoolbox/

### Method 2: Hybrid (Local Git + GitHub Actions Publishing)

Use this when you want more control over tagging but still want automated publishing.

**Local steps:**

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create and push an annotated tag
git tag -a v0.2.1 -m "Release v0.2.1"
git push origin v0.2.1
```

**GitHub steps:**

1. Go to **Releases** → **Draft a new release**
2. Choose your tag (e.g., `v0.2.1`)
3. Add release title and notes
4. Click **Publish release**

This triggers `publish.yml` which handles the rest.

### Method 3: Fully Local (Manual Publishing)

Use this for emergency releases, testing, or when GitHub Actions is unavailable.

**Prerequisites:**
- Install build tools: `pip install build twine`
- Configure `~/.pypirc` with your PyPI API token:

```ini
[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TESTPYPI_TOKEN_HERE
```

**Publishing steps:**

```bash
# Test on TestPyPI first
python scripts/publish.py --test

# If successful, publish to PyPI
python scripts/publish.py

# Available options:
#   --skip-tests   Skip pytest before publishing
#   --skip-build   Use existing dist/ contents
```

---

## Comparison: GitHub vs Local Options

| Task | GitHub UI | Local Git | Notes |
|------|-----------|-----------|-------|
| Create PR | Yes | Yes (then push) | Either works |
| Add version label | Yes | No | Labels are GitHub-only |
| Merge PR | Yes | No (use GitHub) | Enables CI checks |
| Create tag | Yes (via release) | Yes | Local gives more control |
| Create release | Yes | No | Required to trigger publish |
| Publish to PyPI | Automatic | `scripts/publish.py` | GitHub uses OIDC auth |
| View build logs | Yes | N/A | Only in Actions |

### When to Use Each Approach

| Scenario | Recommended Method |
|----------|-------------------|
| Standard release | Method 1 (Fully Automated) |
| Specific tag message or signing | Method 2 (Hybrid) |
| CI is broken/unavailable | Method 3 (Fully Local) |
| Testing the publish process | Method 3 with `--test` |
| Hotfix with custom version | Method 2 or 3 |

---

## GitHub Setup Requirements

### 1. GitHub Environments

Create two environments in repository **Settings → Environments**:
- **`pypi`** - For production releases
- **`testpypi`** - For test releases

### 2. OIDC Trusted Publishers (PyPI)

On both PyPI and TestPyPI, add a trusted publisher:

1. Go to your project on pypi.org (or test.pypi.org)
2. Navigate to **Publishing** → **Add a new publisher**
3. Configure:
   - **Publisher**: GitHub Actions
   - **Repository owner**: `Medecins-Sans-Frontieres-Collaborate`
   - **Repository name**: `msf-toolbox`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi` (or `testpypi`)

This enables passwordless publishing via OIDC tokens.

### 3. Repository Labels

Create these labels for version bumping (Settings → Labels):
- `bump:patch`
- `bump:minor`
- `bump:major`

---

## Pipeline Safeguards

1. **Version validation** - Ensures git tag matches setuptools_scm output
2. **TestPyPI first** - Package is tested on TestPyPI before PyPI
3. **Multi-version testing** - Installation tested on Python 3.10, 3.11, 3.12
4. **Import verification** - Core modules are imported to catch missing dependencies
5. **CI gate** - `ci.yml` must pass before merging (pylint score >= 6, tests pass)

---

## Troubleshooting

### Version mismatch error

If `validate-version` fails, ensure:
- The tag is on the correct commit (not ahead or behind)
- The tag follows `vX.Y.Z` format
- You've fetched all tags locally: `git fetch --tags`

### TestPyPI install fails

- Package may not be immediately available; the workflow waits up to 5 minutes
- Check if dependencies are available on TestPyPI (uses PyPI as fallback)

### Manual publish auth errors

- Verify your `~/.pypirc` has correct tokens
- Ensure token has upload permissions for the project
- For new projects, you may need to create the project on PyPI first

### Import test failures

- Check that all dependencies are listed in `pyproject.toml`
- Ensure no circular imports in the package
- Verify `src/msftoolbox/__init__.py` exists and is properly configured

---

## Verification

After publishing, verify the release:

```bash
# From PyPI
pip install msftoolbox==X.Y.Z
python -c "import msftoolbox; print('Success')"

# From TestPyPI
pip install -i https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    msftoolbox==X.Y.Z
```

Package URLs:
- **PyPI**: https://pypi.org/project/msftoolbox/
- **TestPyPI**: https://test.pypi.org/project/msftoolbox/