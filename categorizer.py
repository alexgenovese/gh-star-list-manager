"""Categorization engine — repo classification, status evaluation, and moving.

Supports two classification modes:
1. By real GitHub star lists (categorize_by_lists)
2. By keyword/language matching against fallback categories (categorize_all)

Also provides the move_repo() utility used by the interactive menu.
"""

from config import FALLBACK_CATEGORIES, INACTIVITY_THRESHOLDS
from pathlib import Path
import json
from config import CATEGORIES_FILE


def load_custom_categories():
    """Load user-created custom categories from categories.json."""
    if CATEGORIES_FILE.exists():
        with open(CATEGORIES_FILE) as f:
            return json.load(f)
    return {}


def save_custom_categories(cats):
    """Persist user-created custom categories to categories.json."""
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(cats, f, indent=2)


def get_all_categories():
    """Merge fallback categories with custom user categories."""
    cats = dict(FALLBACK_CATEGORIES)
    custom = load_custom_categories()
    cats.update(custom)
    return cats


def classify_repo(repo, categories):
    """Score a repo against category keywords and languages.

    Returns the best-matching category name, or 'Other'.
    """
    text = (f"{repo['name']} {repo['description']} "
            f"{' '.join(repo['topics'])}").lower()
    lang = repo.get("language") or ""

    scores = {}
    for cat_name, cat_def in categories.items():
        if cat_name == "Other":
            continue
        score = 0
        for kw in cat_def.get("keywords", []):
            if kw.lower() in text:
                score += 2
        if lang in cat_def.get("languages", []):
            score += 3
        if score > 0:
            scores[cat_name] = score

    return max(scores, key=scores.get) if scores else "Other"


def _months_ago(date_str):
    """Calculate the number of months between now and a given ISO date string."""
    from datetime import datetime, timezone
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days / 30.44
    except Exception:
        return None


def classify_status(repo):
    """Determine the activity status of a repo.

    Evaluation order:
    1. archived flag -> 'archived'
    2. disabled flag -> 'disabled'
    3. Months since last meaningful activity (max of pushed_at / updated_at)
       -> 'active' | 'stable' | 'abandoned'

    Thresholds are read from INACTIVITY_THRESHOLDS (configurable via .env).
    """
    if repo.get("archived"):
        return "archived"
    if repo.get("disabled"):
        return "disabled"

    push_months = repo.get("months_since_push")
    updated_months = _months_ago(repo.get("updated_at"))

    active = INACTIVITY_THRESHOLDS["active_months"]
    stable = INACTIVITY_THRESHOLDS["stable_months"]

    # Use the OLDER of the two timestamps to determine true abandonment.
    oldest = None
    if push_months is not None and updated_months is not None:
        oldest = max(push_months, updated_months)
    elif push_months is not None:
        oldest = push_months
    elif updated_months is not None:
        oldest = updated_months
    else:
        return "unknown"

    if oldest <= active:
        return "active"
    if oldest <= stable:
        return "stable"
    return "abandoned"


def categorize_by_lists(repos, lists):
    """Assign each repo to its first matching GitHub star list.

    Repos that do not appear in any list are placed in 'Other'.
    Each repo also receives a 'status' via classify_status().

    Args:
        repos: list of repo dicts from fetch_all_starred()
        lists: dict from fetch_lists()  {name: {repos: [...], count: N}}

    Returns:
        dict: {list_name: [repo_dicts, ...]}
    """
    repo_map = {}
    for list_name, list_data in lists.items():
        for full_name in list_data["repos"]:
            repo_map.setdefault(full_name, []).append(list_name)

    result = {name: [] for name in lists}
    result["Other"] = []

    for repo in repos:
        full_name = repo["full_name"]
        matched_lists = repo_map.get(full_name, [])
        if matched_lists:
            repo["category"] = matched_lists[0]
            repo["categories"] = matched_lists
        else:
            repo["category"] = "Other"
        repo["status"] = classify_status(repo)
        result[repo["category"]].append(repo)

    return {k: v for k, v in result.items() if v}


def categorize_all(repos, categories=None):
    """Classify all repos using keyword/language scoring against categories.

    Used as a fallback when no GitHub Lists are available.
    """
    if categories is None:
        categories = get_all_categories()

    result = {cat: [] for cat in categories}

    for repo in repos:
        cat = classify_repo(repo, categories)
        if cat not in result:
            result[cat] = []
        repo["category"] = cat
        repo["status"] = classify_status(repo)
        result[cat].append(repo)

    return {k: v for k, v in result.items() if v}


def move_repo(full_name, new_category, categorized):
    """Move a repo from its current category to a new (or existing) one.

    Args:
        full_name: 'owner/repo' string
        new_category: target category name
        categorized: current categorized dict (mutated in place)

    Returns:
        (True, message) on success, (False, message) on failure.
    """
    repo = None
    old_cat = None

    for cat, repos in categorized.items():
        for r in repos:
            if r["full_name"] == full_name:
                repo = r
                old_cat = cat
                break
        if repo:
            break

    if not repo:
        return False, f"Repo '{full_name}' not found."

    categorized[old_cat].remove(repo)
    repo["category"] = new_category

    if new_category not in categorized:
        categorized[new_category] = []
    categorized[new_category].append(repo)

    return True, f"Moved from '{old_cat}' to '{new_category}'"
