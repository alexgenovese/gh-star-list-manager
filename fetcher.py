"""GitHub API fetcher — retrieves starred repos and user star lists.

Uses only the Python standard library (urllib, json, datetime).
Supports pagination, rate-limit handling, and the GitHub GraphQL API
for fetching the user's star lists (Lists feature).
"""

import json
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone
from config import API_PER_PAGE, API_TIMEOUT


def _headers(token):
    """Build standard HTTP headers for GitHub REST API v3."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "gh-star-list-manager"
    }


def _request(url, token):
    """Perform an authenticated GET request and return parsed JSON.

    Handles 401 (invalid token) and 403 (rate limit) transparently.
    """
    req = urllib.request.Request(url, headers=_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("[ERROR] Invalid or expired token.")
            raise SystemExit(1)
        if e.code == 403:
            reset = e.headers.get("X-RateLimit-Reset")
            if reset:
                wait = max(int(reset) - int(time.time()), 0) + 2
                print(f"[RATE LIMIT] Waiting {wait}s...")
                time.sleep(wait)
                return _request(url, token)
            raise
        raise


def _get_pagination_link(resp):
    """Extract the 'next' page URL from the Link header."""
    link_header = resp.headers.get("Link", "")
    for part in link_header.split(","):
        if 'rel="next"' in part:
            return part.split(";")[0].strip().strip("<>")
    return None


def fetch_all_starred(token):
    """Fetch ALL starred repositories for the authenticated user.

    Handles pagination automatically (100 per page).
    Returns a list of dicts with full repo metadata.
    """
    repos = []
    url = (f"https://api.github.com/user/starred"
           f"?per_page={API_PER_PAGE}&sort=updated&direction=desc")
    page = 1

    print("Fetching starred repos from GitHub...", end="", flush=True)

    while url:
        req = urllib.request.Request(url, headers=_headers(token))
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            link_header = resp.headers.get("Link", "")

        for repo in data:
            repos.append(_extract_repo(repo))

        count = len(repos)
        print(f" {count}", end="", flush=True)

        url = None
        for part in link_header.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
                break

        page += 1

    print(f" - {len(repos)} repos fetched.")
    return repos


def _extract_repo(repo):
    """Extract and normalize relevant fields from a GitHub API repo object."""
    pushed = repo.get("pushed_at")
    if pushed:
        pushed_dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        months_ago = (datetime.now(timezone.utc) - pushed_dt).days / 30.44
    else:
        months_ago = None

    return {
        "id": repo["id"],
        "full_name": repo["full_name"],
        "name": repo["name"],
        "owner": repo["owner"]["login"],
        "description": repo.get("description") or "",
        "url": repo["html_url"],
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "stargazers_count": repo.get("stargazers_count", 0),
        "forks_count": repo.get("forks_count", 0),
        "open_issues_count": repo.get("open_issues_count", 0),
        "archived": repo.get("archived", False),
        "disabled": repo.get("disabled", False),
        "created_at": repo.get("created_at"),
        "updated_at": repo.get("updated_at"),
        "pushed_at": pushed,
        "months_since_push": (round(months_ago, 1)
                              if months_ago is not None else None),
    }


def fetch_lists(token):
    """Fetch the authenticated user's star lists (Lists feature) via GraphQL.

    Returns a dict: {list_name: {"repos": [full_names...], "count": N}}
    Returns an empty dict if no lists exist or on error.
    """
    query = {
        "query": """
{
  viewer {
    login
    lists(first: 50) {
      totalCount
      nodes {
        id
        name
        items(first: 100) {
          totalCount
          nodes {
            ... on Repository {
              nameWithOwner
            }
          }
        }
      }
    }
  }
}
"""
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "gh-star-list-manager",
    }
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(query).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as r:
        d = json.loads(r.read().decode())
        if "errors" in d:
            print(f"[ERROR] GraphQL: {d['errors'][0]['message']}")
            return {}

    lists_data = d["data"]["viewer"]["lists"]["nodes"]
    result = {}
    for lst in lists_data:
        name = lst["name"]
        repos = []
        for item in lst.get("items", {}).get("nodes", []):
            if item and item.get("nameWithOwner"):
                repos.append(item["nameWithOwner"])
        result[name] = {"repos": repos, "count": len(repos)}
    return result


def unstar_repo(owner, repo_name, token):
    """Remove a star (unstar) from a repository via the GitHub API.

    Returns True if the star was successfully removed (HTTP 204).
    """
    url = f"https://api.github.com/user/starred/{owner}/{repo_name}"
    req = urllib.request.Request(
        url, headers=_headers(token), method="DELETE"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status == 204
    except urllib.error.HTTPError:
        return False
