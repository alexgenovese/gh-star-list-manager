# GitHub Star List Manager

**Organize, categorize, and clean up your GitHub starred repos — all from your terminal.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3c873a?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen?style=flat-square)](#)

Zero external dependencies — built entirely on the Python standard library.

---

## Features

- **Fetch and cache** all your starred repos from GitHub (paginated, 100 per page)
- **Categorize by GitHub Lists** — maps repos to your existing star lists via GraphQL API
- **Keyword scoring fallback** — automatically classifies repos by name, description, topics, and language against configurable categories
- **Status classification** — marks each repo as `active`, `stable`, `abandoned`, `archived`, or `disabled` based on last push date
- **Interactive TUI** — browse, search, move, and unstar repos with a simple numbered menu
- **Bulk unstar** — clean up stale/abandoned repos, or unstar repos that appear in multiple lists
- **Custom categories** — add your own categories with keyword and language rules, saved to `categories.json`
- **Export** — categorized reports in TXT or JSON, to screen or file
- **Rate-limit aware** — respects GitHub API limits, waits and retries on 403

---

## Installation

```bash
# Clone or copy the project, then:
cd gh-star-list-manager

# (Optional) Create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# No pip install needed — pure stdlib
```

---

## Setup

You need a [GitHub Personal Access Token](https://github.com/settings/tokens) with **`public_repo`** scope (read-only for fetch, read+write to unstar).

### Option A — `.env` file (recommended)

```bash
cp .env.example .env
# Edit .env and add:
# GITHUB_TOKEN=ghp_your_token_here
```

### Option B — Environment variable

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

### Option C — On first run

The tool prompts for your token on first launch and automatically saves it to `.env` for future use.

---

## Usage

```bash
python3 main.py
```

### Main menu walkthrough

```
============================================================
  GITHUB STAR LIST MANAGER
============================================================

  Stars loaded: Yes
  Categories:   8

  1. Fetch and categorize starred repos
  2. Browse categorized repos
  3. Search repos
  4. Manage lists
  5. Unstar repos (stale / multi-list)
  6. Manage categories
  7. Export data
  8. Refresh from cache
  9. Load cached stars
  10. Quit
```

### Typical workflow

1. **Fetch** — downloads all starred repos and GitHub Lists
2. **Browse** — explore repos grouped by list or category
3. **Search** — search across all repos by name, description, or topics
4. **Unstar** — select stale repos or list overlaps and remove them
5. **Export** — save categorized report to file

---

## Architecture

```
main.py
  └─ interactive.py          # TUI menu system
       ├─ fetcher.py         # GitHub REST + GraphQL API calls
       ├─ categorizer.py     # Classification engine
       └─ config.py          # Token, paths, thresholds
            └─ data/         # stars.json, categories.json, exports
```

### Data flow

```
GitHub API ──fetch──▶ stars.json (cache) ──categorize──▶ categorized dict
                               │                               │
                         GitHub Lists                    Browse / Search
                         (GraphQL)                         Move / Unstar
                                                              │
                                                         Export (txt/json)
```

---

## Status Classification

| Status     | Condition                                   |
|------------|---------------------------------------------|
| `active`   | Last push < 6 months                        |
| `stable`   | Last push 6–18 months                       |
| `abandoned`| Last push > 18 months                       |
| `archived` | GitHub `archived: true` flag                |
| `disabled` | GitHub `disabled: true` flag                |
| `unknown`  | No push/update data available               |

Thresholds are configurable via `.env`:
- `THRESHOLD_ACTIVE_MONTHS` (default: `6`)
- `THRESHOLD_STABLE_MONTHS` (default: `18`)

---

## Default Categories

| Category     | Sample keywords                                       | Languages                    |
|-------------|-------------------------------------------------------|------------------------------|
| AI/ML       | machine-learning, deep-learning, ai, llm, pytorch     | Python                       |
| Web Dev     | javascript, typescript, react, vue, nextjs            | JavaScript, TypeScript, HTML |
| DevOps      | docker, kubernetes, terraform, ansible, ci-cd         | Dockerfile, Shell, HCL       |
| Mobile      | ios, android, flutter, react-native                   | Swift, Kotlin, Dart          |
| Data        | data, database, sql, nosql, postgresql, pandas        | SQL, Julia, R                |
| CLI/Tools   | cli, command-line, terminal, tool, utility            | Go, Rust                     |
| Docs/Risorse| awesome, list, resource, tutorial, course             | —                            |
| Other       | *(fallback for unmatched repos)*                      | —                            |

---

## Configuration (`.env`)

| Variable                  | Default | Description                        |
|---------------------------|---------|------------------------------------|
| `GITHUB_TOKEN`            | —       | GitHub Personal Access Token       |
| `GITHUB_USERNAME`         | —       | GitHub username (optional)         |
| `API_PER_PAGE`            | `100`   | Repos per API page                 |
| `API_TIMEOUT`             | `30`    | HTTP timeout (seconds)             |
| `THRESHOLD_ACTIVE_MONTHS` | `6`     | Months for "active" status         |
| `THRESHOLD_STABLE_MONTHS` | `18`    | Months for "stable" status         |
| `EXPORT_FORMAT`           | `txt`   | Export format (`txt` or `json`)    |
| `COLORS_ENABLED`          | `true`  | ANSI colors in terminal            |

---

## Exports

Reports are saved to `data/` as either plain text or JSON:

```bash
data/
├── github_stars_export_20250621_143022.txt
├── github_stars_export_20250621_143022.json
├── stars.json              # Local cache of all starred repos
└── categories.json         # Custom categories you've created
```

---

## Technical Notes

- **Rate limit**: 5,000 requests/hour with a token; automatic retry on 403
- **Pagination**: 100 repos per request, automatic loop
- **Caching**: stars.json keeps data local — no need to re-fetch every run
- **Zero dependencies**: only `urllib`, `json`, `os`, `pathlib`, `datetime` from stdlib
- **Python**: 3.10+
- **GitHub API**: REST v3 (stars) + GraphQL (Lists)
