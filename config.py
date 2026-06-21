"""Configuration and environment helpers for the GitHub Star List Manager.

Loads .env, defines paths, API constants, inactivity thresholds,
and provides token retrieval utilities.
"""

import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STARS_FILE = DATA_DIR / "stars.json"
CATEGORIES_FILE = DATA_DIR / "categories.json"
ENV_FILE = BASE_DIR / ".env"

GITHUB_API = "https://api.github.com"


def _load_env():
    """Load environment variables from .env file if it exists."""
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if value and key not in os.environ:
                os.environ[key] = value


_load_env()

# --- Fallback categories (used only when no GitHub Lists are available) ---
FALLBACK_CATEGORIES = {
    "AI/ML": {
        "keywords": ["machine-learning", "deep-learning", "ai", "llm", "gpt", "transformers",
                      "neural-network", "nlp", "computer-vision", "pytorch", "tensorflow",
                      "langchain", "rag", "fine-tuning", "stable-diffusion", "diffusion"],
        "languages": ["Python"]
    },
    "Web Dev": {
        "keywords": ["javascript", "typescript", "react", "vue", "angular", "nextjs",
                      "svelte", "html", "css", "frontend", "backend", "fullstack",
                      "web", "http", "api", "rest", "graphql"],
        "languages": ["JavaScript", "TypeScript", "HTML", "CSS"]
    },
    "DevOps": {
        "keywords": ["docker", "kubernetes", "k8s", "terraform", "ansible", "ci-cd",
                      "devops", "aws", "azure", "gcp", "cloud", "infrastructure",
                      "nginx", "linux", "bash"],
        "languages": ["Dockerfile", "Shell", "HCL"]
    },
    "Mobile": {
        "keywords": ["ios", "android", "flutter", "react-native", "swift", "kotlin",
                      "mobile", "ios-app", "android-app"],
        "languages": ["Swift", "Kotlin", "Dart"]
    },
    "Data": {
        "keywords": ["data", "database", "sql", "nosql", "postgresql", "mongodb",
                      "redis", "elasticsearch", "pandas", "data-science", "analytics",
                      "visualization", "etl", "pipeline"],
        "languages": ["SQL", "Julia", "R"]
    },
    "CLI/Tools": {
        "keywords": ["cli", "command-line", "terminal", "tool", "utility", "toolkit",
                      "productivity", "automation", "script"],
        "languages": ["Go", "Rust"]
    },
    "Docs/Risorse": {
        "keywords": ["awesome", "list", "resource", "collection", "curated", "tutorial",
                      "course", "book", "learning", "cheatsheet", "documentation"],
        "languages": []
    },
    "Other": {
        "keywords": [],
        "languages": []
    }
}

# --- Inactivity thresholds (customizable via .env) ---
INACTIVITY_THRESHOLDS = {
    "active_months": int(os.environ.get("THRESHOLD_ACTIVE_MONTHS", 6)),
    "stable_months": int(os.environ.get("THRESHOLD_STABLE_MONTHS", 18)),
}

API_PER_PAGE = int(os.environ.get("API_PER_PAGE", 100))
API_TIMEOUT = int(os.environ.get("API_TIMEOUT", 30))
COLORS_ENABLED = os.environ.get("COLORS_ENABLED", "true").lower() == "true"
EXPORT_FORMAT = os.environ.get("EXPORT_FORMAT", "txt")


def get_token():
    """Return a valid GitHub token from env, .env, or prompt the user."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    print("No GITHUB_TOKEN found.")
    print("Options:")
    print("  1. Set GITHUB_TOKEN in your .env file")
    print("  2. Export: export GITHUB_TOKEN='ghp_...'")
    print("  3. Enter it below")
    print()
    print("Generate at: https://github.com/settings/tokens")
    print("Scope required: public_repo (read + write)")
    print()
    token = input("Token: ").strip()
    if token:
        os.environ["GITHUB_TOKEN"] = token
        _save_token_to_env(token)
    return token


def _save_token_to_env(token):
    """Persist the token into .env so it's available on next runs."""
    env_path = ENV_FILE
    if env_path.exists():
        lines = env_path.read_text().splitlines()
        found = False
        for i, line in enumerate(lines):
            if line.startswith("GITHUB_TOKEN="):
                lines[i] = f"GITHUB_TOKEN={token}"
                found = True
                break
        if found:
            env_path.write_text("\n".join(lines) + "\n")
        else:
            with open(env_path, "a") as f:
                f.write(f"\nGITHUB_TOKEN={token}\n")
    else:
        with open(env_path, "w") as f:
            f.write(f"GITHUB_TOKEN={token}\n")


def get_github_username():
    """Return the GitHub username from env or .env."""
    return os.environ.get("GITHUB_USERNAME", "")


def ensure_data_dir():
    """Create the data directory if it does not exist."""
    DATA_DIR.mkdir(exist_ok=True)
