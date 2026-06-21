#!/usr/bin/env python3
"""Interactive TUI for the GitHub Star List Manager.

Entry point: run()
"""

import json
import os
import webbrowser
from datetime import datetime
from pathlib import Path

from config import (STARS_FILE, DATA_DIR, GITHUB_API, FALLBACK_CATEGORIES,
                    COLORS_ENABLED, EXPORT_FORMAT)
from fetcher import fetch_all_starred, fetch_lists, unstar_repo
from categorizer import (categorize_by_lists, categorize_all, move_repo,
                         get_all_categories, load_custom_categories,
                         save_custom_categories)


# ── Colors ──────────────────────────────────────────────────────────────
_R = "\033[91m" if COLORS_ENABLED else ""
_G = "\033[92m" if COLORS_ENABLED else ""
_Y = "\033[93m" if COLORS_ENABLED else ""
_B = "\033[94m" if COLORS_ENABLED else ""
_M = "\033[95m" if COLORS_ENABLED else ""
_C = "\033[96m" if COLORS_ENABLED else ""
_NC = "\033[0m" if COLORS_ENABLED else ""


def _color(severity, text):
    """Wrap text in ANSI color by severity keyword."""
    if not COLORS_ENABLED:
        return text
    clr = {"ok": _G, "warn": _Y, "err": _R, "info": _C, "hl": _M}.get(
        severity, _NC)
    return f"{clr}{text}{_NC}"


# ── I/O helpers ─────────────────────────────────────────────────────────

def header(title):
    """Print a section header with decorative borders."""
    sep = "=" * 60
    print(f"\n{_color('info', sep)}")
    print(f"  {title}")
    print(f"{_color('info', sep)}")


def choice(prompt, options, allow_back=False):
    """Prompt the user to pick from a list of numbered options.

    Args:
        prompt: question string
        options: list of (key, label) tuples, or plain strings
        allow_back: if True, add back option as 'b'

    Returns:
        Selected key (str), or 'b' if allow_back and user chose back.
    """
    print()
    print(f"  {_color('hl', prompt)}")
    for i, item in enumerate(options, 1):
        if isinstance(item, tuple):
            key, label = item
        else:
            key, label = str(i), item
        print(f"    {i}. {label}")
    if allow_back:
        print(f"    b. ← Back")
    valid = {str(i): (k if isinstance(item, tuple) else k)
             for i, (k, item) in enumerate(
                 [(opt if isinstance(opt, tuple) else (str(i), opt))
                  for i, opt in enumerate(options, 1)])}
    if allow_back:
        valid["b"] = "b"
    while True:
        inp = input(f"\n  {_color('ok', '›')} ").strip().lower()
        if inp in valid:
            return valid[inp]
        print(f"  {_color('err', 'Invalid choice')}")


def press_any_key():
    """Wait for the user to press Enter."""
    print()
    input(f"  {_color('warn', '[Press Enter to continue...]')}")
    print()


# ── Main menu ───────────────────────────────────────────────────────────

def run():
    """Display the main menu and dispatch to sub-menus."""
    from config import get_token, get_github_username

    header("GitHub Star List Manager")
    token = get_token()
    if not token:
        print("No token provided. Exiting.")
        return

    username = get_github_username() or "(unknown)"
    print(f"  Authenticated as: {_color('ok', username)}")
    print(f"  Data directory:   {DATA_DIR}")

    stale = None
    categorized = None
    repos_loaded = False
    lists = None

    while True:
        header("Main Menu")
        print(f"  {'★' if repos_loaded else '☆'}")
        print(f"  Stars loaded: {_color('ok', 'Yes') if repos_loaded else _color('warn', 'No')}")
        if categorized:
            print(f"  Categories:   {_color('info', str(len(categorized)))}")
        print()

        opts = [
            ("fetch", "Fetch and categorize starred repos"),
        ]
        if categorized:
            opts.append(("browse", "Browse categorized repos"))
            opts.append(("search", "Search repos"))
            opts.append(("menu_list", "Manage lists"))
            opts.append(("unstar", "Unstar repos (stale / multi-list)"))

        opts += [
            ("menu_cat", "Manage categories"),
            ("export", "Export data"),
            ("refresh", "Refresh from cache"),
        ]
        if STARS_FILE.exists():
            opts.append(("load", "Load cached stars"))
        opts.append(("quit", "Quit"))

        cmd = choice("What do you want to do?", opts)

        if cmd == "quit":
            print(f"\n  {_color('ok', 'Bye!')}")
            break
        elif cmd == "fetch":
            repos = fetch_all_starred(token)
            if not repos:
                print("No starred repos found.")
                continue
            _cache_stars(repos)
            lists = fetch_lists(token)
            if lists:
                print(f"Found {len(lists)} GitHub Lists.")
                categorized = categorize_by_lists(repos, lists)
            else:
                categorized = categorize_all(repos)
            repos_loaded = True
            stale = None
        elif cmd == "load":
            repos = _load_stars()
            if not repos:
                continue
            lists = fetch_lists(token)
            if lists:
                categorized = categorize_by_lists(repos, lists)
            else:
                categorized = categorize_all(repos)
            repos_loaded = True
            stale = None
        elif cmd == "browse":
            if categorized:
                _browse_repos(categorized, token)
        elif cmd == "search":
            if categorized:
                _search_repos(categorized)
        elif cmd == "menu_list":
            if categorized and lists:
                _menu_list(categorized, lists, token)
            else:
                print("No GitHub Lists available.")
        elif cmd == "unstar":
            if categorized:
                _menu_unstar(categorized, token)
        elif cmd == "menu_cat":
            _menu_categories(categorized, token)
        elif cmd == "export":
            _export_menu(categorized)
        elif cmd == "refresh":
            stale = _rebuild_categories(categorized, lists, token)


# ── Browse ──────────────────────────────────────────────────────────────

def _browse_repos(categorized, token):
    """Browse repos interactively by category list."""
    cats = sorted(categorized.keys())
    while True:
        sel = choice("Select a category:", cats, allow_back=True)
        if sel == "b":
            break
        _show_category(sel, categorized[sel], token)


def _show_category(category, repos, token):
    """Display repos in a single category and offer per-repo actions.

    Actions available:
      o → open in browser
      m → move to another category
      u → unstar
    """
    if not repos:
        print(f"  Category '{category}' is empty.")
        return

    header(f"Category: {category} ({len(repos)} repos)")
    count_by_status = {"active": 0, "stable": 0, "abandoned": 0, "archived": 0, "disabled": 0, "unknown": 0}
    for r in repos:
        count_by_status[r.get("status", "unknown")] = (
            count_by_status.get(r.get("status", "unknown"), 0) + 1)
    print(f"  Active: {_color('ok', count_by_status['active'])}  "
          f"Stable: {_color('warn', count_by_status['stable'])}  "
          f"Abandoned: {_color('err', count_by_status['abandoned'])}  "
          f"Archived: {count_by_status['archived']}  "
          f"Disabled: {count_by_status['disabled']}")
    print()

    for i, repo in enumerate(repos, 1):
        _print_repo_short(i, repo)

    print()
    while True:
        inp = input(
            f"  {_color('ok', '›')} "
            f"Enter number to inspect, or "
            f"{_color('warn', 'q')} to go back: "
        ).strip().lower()
        if inp == "q":
            break
        if inp.isdigit():
            idx = int(inp) - 1
            if 0 <= idx < len(repos):
                _inspect_repo(repos[idx], token, categorized={
                    cat: repos for cat, repos in {category: repos}.items()})


def _print_repo_short(index, repo):
    """Print a compact, one-line summary of a repo."""
    status_color = {
        "active": _G, "stable": _Y, "abandoned": _R,
        "archived": _M, "disabled": _M
    }.get(repo.get("status", ""), _NC)

    status_badge = repo.get("status", "?")[:3].upper()
    lang = repo.get("language") or "--"
    desc = (repo.get("description") or "")[:80]
    print(f"  {_color('hl', f'{index:>3}')} "
          f"[{status_color}{status_badge:>4}{_NC}] "
          f"{_color('ok', repo['full_name']):35} "
          f"{_color('warn', lang):>10}  "
          f"{desc}")


def _inspect_repo(repo, token, categorized=None):
    """Show detailed info for a single repo with actions."""
    header(f"Repo: {repo['full_name']}")
    print(f"  Description:     {repo.get('description') or '--'}")
    print(f"  URL:             {repo['url']}")
    print(f"  Language:        {repo.get('language') or '--'}")
    print(f"  Topics:          {', '.join(repo['topics']) if repo['topics'] else '--'}")
    print(f"  Stars:           {repo['stargazers_count']}")
    print(f"  Forks:           {repo['forks_count']}")
    print(f"  Last push:       {_color('err', repo['pushed_at'] or '--')}"
          f"  ({repo.get('months_since_push', '?')} months ago)")
    print(f"  Status:          {_color_badge(repo.get('status', '?'))}")
    print(f"  Archived:        {repo.get('archived', False)}")
    print(f"  Category:        {repo.get('category', '?')}")

    actions = [
        ("o", "Open in browser"),
        ("m", "Move to another category"),
        ("u", "Unstar"),
    ]
    print()
    print(f"  [{_color('ok', 'o')}] Open in browser")
    print(f"  [{_color('ok', 'm')}] Move to another category")
    print(f"  [{_color('ok', 'u')}] Unstar")

    cmd = input(f"\n  {_color('ok', '›')} Action [{_color('warn', 'b')}ack]: ").strip().lower()

    if cmd == "o":
        webbrowser.open(repo["url"])
    elif cmd == "m":
        if categorized:
            cats = sorted(categorized.keys())
            target = choice("Move to which category?",
                            [(c, c) for c in cats if c != repo.get("category")],
                            allow_back=True)
            if target != "b":
                success, msg = move_repo(repo["full_name"], target, categorized)
                print(f"  {_color('ok' if success else 'err', msg)}")
                press_any_key()
    elif cmd == "u":
        _confirm_unstar(repo, token)


def _color_badge(status):
    """Return an ANSI-colored status badge string."""
    map = {
        "active": _G, "stable": _Y, "abandoned": _R,
        "archived": _M, "disabled": _M, "unknown": "?"
    }
    clr = map.get(status, _NC)
    return f"{clr}{status.upper():>9}{_NC}"


# ── Search ──────────────────────────────────────────────────────────────

def _search_repos(categorized):
    """Search across all categorized repos by name, description, or topics."""
    query = input(f"\n  {_color('ok', '›')} Search for: ").strip().lower()
    if not query:
        return

    results = []
    for cat, repos in categorized.items():
        for repo in repos:
            text = (f"{repo['full_name']} {repo['description']} "
                    f"{' '.join(repo['topics'])}").lower()
            if query in text:
                results.append((cat, repo))

    print(f"\n  {_color('info', f'{len(results)} result(s)')} "
          f"for '{query}':\n")
    for cat, repo in results[:30]:
        print(f"  [{_color('warn', cat):16}] "
              f"{_color('ok', repo['full_name'])}")
        if repo.get("description"):
            print(f"  {'  '}{repo['description'][:100]}")
        print()
    if len(results) > 30:
        print(f"  ... and {len(results) - 30} more.\n")

    press_any_key()


# ── List management ─────────────────────────────────────────────────────

def _menu_list(categorized, lists, token):
    """Manage GitHub Lists: view, rename, move repos between lists."""
    header("List Manager")
    list_names = sorted(lists.keys())
    if not list_names:
        print("No lists available.")
        press_any_key()
        return

    sel = choice("Select a list:", list_names, allow_back=True)
    if sel == "b":
        return

    _inspect_list(sel, lists, categorized, token)


def _inspect_list(name, lists, categorized, token):
    """Show repos in a specific GitHub list with mass actions."""
    header(f"List: {name} [{lists[name]['count']} repos]")
    repos = lists[name]["repos"]

    page_size = 20
    offset = 0

    while True:
        page = repos[offset:offset + page_size]
        for i, full_name in enumerate(page, offset + 1):
            cat = _find_category_for(full_name, categorized)
            print(f"  {_color('hl', f'{i:>3}')}  "
                  f"{_color('ok', full_name):35}  "
                  f"[{_color('warn', cat or '?')}]")
        print()

        has_next = offset + page_size < len(repos)
        has_prev = offset > 0

        actions = []
        if has_prev:
            actions.append("p: ← Previous")
        if has_next:
            actions.append("n: Next →")
        actions.append("q: Back to list menu")

        print(f"  {', '.join(actions)}")
        cmd = input(f"  {_color('ok', '›')} ").strip().lower()

        if cmd == "q":
            break
        elif cmd == "n" and has_next:
            offset += page_size
        elif cmd == "p" and has_prev:
            offset = max(0, offset - page_size)


def _find_category_for(full_name, categorized):
    """Return the category name for a repo, or None if not found."""
    if not categorized:
        return None
    for cat, repos in categorized.items():
        for r in repos:
            if r["full_name"] == full_name:
                return cat
    return None


# ── Unstar menu ─────────────────────────────────────────────────────────

def _menu_unstar(categorized, token):
    """Unstar repos — choose by stale/abandoned status or multi-list overlap."""
    header("Unstar Repos")
    opts = [
        ("stale", "Show stale/abandoned repos"),
        ("multi", "Show repos in multiple lists (list overlap)"),
    ]
    sel = choice("Select mode:", opts, allow_back=True)
    if sel == "b":
        return
    if sel == "stale":
        _unstale(categorized, token)
    elif sel == "multi":
        _unmulti(categorized, token)


def _unstale(categorized, token):
    """Find repos that are abandoned/archived and let user unstar them."""
    header("Stale/Abandoned Repos")
    stale_statuses = ("abandoned", "archived", "disabled")
    stale_repos = []
    for cat, repos in categorized.items():
        for r in repos:
            if r.get("status") in stale_statuses:
                stale_repos.append((cat, r))

    if not stale_repos:
        print(f"  {_color('ok', 'No stale repos found!')}")
        press_any_key()
        return

    print(f"  Found {_color('err', str(len(stale_repos)))} "
          f"stale/abandoned repos.\n")

    for i, (cat, repo) in enumerate(stale_repos[:50], 1):
        _print_repo_short(i, repo)

    if len(stale_repos) > 50:
        print(f"\n  ... and {len(stale_repos) - 50} more.")

    print()
    inp = input(
        f"  {_color('ok', '›')} "
        f"Enter numbers to unstar (comma-separated), or "
        f"{_color('warn', 'a')}ll, {_color('warn', 'q')}uit: "
    ).strip().lower()

    if inp == "q":
        return

    targets = []
    if inp == "a":
        targets = stale_repos
    else:
        indices = set()
        for part in inp.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(stale_repos):
                    indices.add(idx)
        targets = [stale_repos[i] for i in indices]

    if not targets:
        print("No repos selected.")
        press_any_key()
        return

    print(f"\n  Unstarring {len(targets)} repos...")
    for cat, repo in targets:
        owner, name = repo["full_name"].split("/")
        ok = unstar_repo(owner, name, token)
        s = _color("ok", "✓") if ok else _color("err", "✗")
        print(f"    {s} {repo['full_name']}")

    # Flush cache so changes reflect on next fetch
    _flush_cache()
    press_any_key()


def _unmulti(categorized, token):
    """Find repos that appear in multiple lists and offer to unstar."""
    header("Repos in Multiple Lists")

    multi_repos = {}
    for cat, repos in categorized.items():
        for r in repos:
            fname = r["full_name"]
            if fname in multi_repos:
                multi_repos[fname][1].append(cat)
            else:
                multi_repos[fname] = (r, [cat], cat)

    overlapping = {k: v for k, v in multi_repos.items()
                   if len(v[1]) > 1}

    if not overlapping:
        print(f"  {_color('ok', 'No repos in multiple lists.')}")
        press_any_key()
        return

    print(f"  Found {_color('err', str(len(overlapping)))} repos "
          f"in multiple lists:\n")
    for i, (full_name, (repo, cats, _)) in enumerate(
            sorted(overlapping.items()), 1):
        print(f"  {_color('hl', f'{i:>3}')}  "
              f"{_color('ok', full_name):35}  "
              f"Lists: {', '.join(cats)}")

    inp = input(
        f"\n  {_color('ok', '›')} "
        f"Enter numbers to unstar (comma-separated) or "
        f"{_color('warn', 'q')}uit: "
    ).strip().lower()

    if inp == "q":
        return

    indices = set()
    for part in inp.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(overlapping):
                indices.add(idx)

    targets = [list(overlapping.values())[i] for i in indices]
    if not targets:
        return

    for repo, cats, _ in targets:
        owner, name = repo["full_name"].split("/")
        ok = unstar_repo(owner, name, token)
        s = _color("ok", "✓") if ok else _color("err", "✗")
        print(f"    {s} {repo['full_name']}")

    _flush_cache()
    press_any_key()


# ── Categories management ───────────────────────────────────────────────

def _menu_categories(categorized, token):
    """Create, rename, or delete custom categories.

    Fallback categories (defined in config) cannot be removed.
    """
    header("Category Manager")

    custom = load_custom_categories()
    all_cats = get_all_categories()

    opts = [
        ("add", "Add new category"),
    ]
    if custom:
        opts.append(("del", "Delete custom categories"))
    opts.append(("list", "Show all categories"))
    if custom:
        opts.append(("recalc", "Re-classify all repos"))
    opts.append(("back", "← Back"))

    sel = choice("Category options:", opts)
    if sel == "back":
        return
    elif sel == "add":
        name = input(f"  {_color('ok', '›')} "
                     f"New category name: ").strip()
        if name:
            custom[name] = {"keywords": [], "languages": []}
            save_custom_categories(custom)
            print(f"  {_color('ok', f'Category \"{name}\" added.')}")
            print(f"  Edit keywords/languages in {DATA_DIR}/categories.json")
    elif sel == "del":
        if not custom:
            print("No custom categories to delete.")
        else:
            to_del = choice("Select category to delete:",
                            list(custom.keys()), allow_back=True)
            if to_del != "b":
                custom.pop(to_del, None)
                save_custom_categories(custom)
                print(f"  {_color('ok', f'Deleted \"{to_del}\".')}")
    elif sel == "list":
        header("All Categories")
        for cat in all_cats:
            kw = all_cats[cat].get("keywords", [])
            lang = all_cats[cat].get("languages", [])
            source = "custom" if cat in custom else "built-in"
            print(f"  {_color('ok', cat):20} "
                  f"[{_color('warn', source):8}]  "
                  f"{len(kw)} keywords, {len(lang)} languages")
        press_any_key()
    elif sel == "recalc":
        if not categorized:
            print("No repos loaded.")
            return
        repos = []
        for cat_repos in categorized.values():
            repos.extend(cat_repos)
        new_cats = categorize_all(repos)
        categorized.clear()
        categorized.update(new_cats)
        print(f"  {_color('ok', 'Re-classified')} "
              f"{len(repos)} repos into {len(new_cats)} categories.")


# ── Export ──────────────────────────────────────────────────────────────

def _export_menu(categorized):
    """Export categorized repo list to stdout or file as TXT or JSON."""
    if not categorized:
        print("No data to export.")
        press_any_key()
        return

    header("Export")

    fmt = choice("Output format:", [
        ("txt", "Plain text"),
        ("json", "JSON"),
    ], allow_back=True)
    if fmt == "b":
        return

    dest = choice("Destination:", [
        ("screen", "Screen (stdout)"),
        ("file", "File"),
    ], allow_back=True)
    if dest == "b":
        return

    if dest == "screen":
        if fmt == "txt":
            for cat, repos in sorted(categorized.items()):
                print(f"\n--- {cat} ({len(repos)} repos) ---")
                for r in repos:
                    print(f"  {r['full_name']}  [{r.get('status','?').upper()}]")
        else:
            print(json.dumps(categorized, indent=2, default=str))
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"github_stars_export_{ts}.{fmt}"
        fpath = DATA_DIR / fname
        if fmt == "txt":
            with open(fpath, "w") as f:
                for cat, repos in sorted(categorized.items()):
                    f.write(f"\n--- {cat} ({len(repos)} repos) ---\n")
                    for r in repos:
                        f.write(f"  {r['full_name']}  "
                                f"[{r.get('status','?').upper()}]\n")
        else:
            with open(fpath, "w") as f:
                json.dump(categorized, f, indent=2, default=str)
        print(f"  Saved to: {fpath}")

    press_any_key()


# ── Cache helpers ───────────────────────────────────────────────────────

def _cache_stars(repos):
    """Persist fetched starred repos to stars.json."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(STARS_FILE, "w") as f:
        json.dump(repos, f, indent=2, default=str)
    print(f"  Cached {len(repos)} repos.")


def _load_stars():
    """Load starred repos from stars.json cache."""
    if not STARS_FILE.exists():
        print("No cached stars found. Fetch first.")
        return []
    with open(STARS_FILE) as f:
        repos = json.load(f)
    print(f"  Loaded {len(repos)} repos from cache.")
    return repos


def _flush_cache():
    """Delete the local stars.json cache, forcing a fresh fetch next time."""
    if STARS_FILE.exists():
        STARS_FILE.unlink()
        print("  Cache flushed.")


def _rebuild_categories(categorized, lists, token):
    """Re-classify all repos and return categorized dict.

    This is used as the 'refresh' action.
    """
    if not categorized:
        print("No repos to rebuild.")
        return None
    repos = []
    for cat_repos in categorized.values():
        repos.extend(cat_repos)
    if lists:
        new_cats = categorize_by_lists(repos, lists)
    else:
        new_cats = categorize_all(repos)
    categorized.clear()
    categorized.update(new_cats)
    print(f"  Rebuilt {len(new_cats)} categories from {len(repos)} repos.")
    return None
