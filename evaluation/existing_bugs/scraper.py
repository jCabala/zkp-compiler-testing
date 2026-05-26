#!/usr/bin/env python3
"""Scraper for logical bugs in ZKP compiler repos via GitHub Search API."""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
import requests

SCRIPT_DIR = Path(__file__).parent

# Load .env from the same directory as this script
_env_file = SCRIPT_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
KEYWORDS_FILE = SCRIPT_DIR / "keywords.json"
RESULTS_DIR = SCRIPT_DIR / "results"

REPOS: dict[str, str] = {
    "circom":   "iden3/circom",
    "noir":     "noir-lang/noir",
    "zokrates": "Zokrates/ZoKrates",
    "gnark":    "ConsenSys/gnark",
}

GITHUB_API = "https://api.github.com"
MAX_PER_PAGE = 100
REQUEST_PAUSE = 2.0   # seconds between requests (stays under 30 req/min for authenticated)
KEYWORD_CHUNK = 5     # max keywords per OR-joined query (GitHub search is strict on length)

# Title prefixes that indicate maintenance/feature work rather than bug reports
_NOISE_PREFIXES = (
    "chore:", "chore(",
    "feat:", "feat(",
    "docs:", "docs(",
    "perf:", "perf(",
    "refactor:", "refactor(",
    "test:", "test(",
    "ci:", "ci(",
    "build:", "build(",
    "style:", "style(",
)
_NOISE_SUBSTRINGS = ("bump ", "release noir", "release zokrates", "release gnark")


# ---------------------------------------------------------------------------
# Keyword helpers
# ---------------------------------------------------------------------------

def load_keywords(path: Path) -> dict[str, list[str]]:
    with open(path) as f:
        return json.load(f)


def flatten_keywords(kw_dict: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for kws in kw_dict.values():
        for kw in kws:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                result.append(kw)
    return result


def quote_kw(kw: str) -> str:
    return f'"{kw}"' if " " in kw else kw


def chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def find_matching_keywords(text: str, keywords: list[str]) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def is_likely_noise(item: dict) -> bool:
    if not item.get("matched_keywords"):
        return True
    title = (item.get("title") or item.get("message_first_line", "")).lower().strip()
    if title.startswith(_NOISE_PREFIXES):
        return True
    if any(s in title for s in _NOISE_SUBSTRINGS):
        return True
    return False


# ---------------------------------------------------------------------------
# HTTP session + pagination
# ---------------------------------------------------------------------------

def make_session(token: str | None) -> requests.Session:
    s = requests.Session()
    s.headers["Accept"] = "application/vnd.github+json"
    s.headers["X-GitHub-Api-Version"] = "2022-11-28"
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def _wait_for_rate_limit(resp: requests.Response) -> None:
    reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
    wait = max(reset_ts - time.time(), 1) + 1
    print(f"    Rate limited — waiting {wait:.0f}s...", flush=True)
    time.sleep(wait)


def paginate(session: requests.Session, url: str, params: dict, max_results: int = 1000) -> list[dict]:
    results: list[dict] = []
    page = 1
    while len(results) < max_results:
        params = {**params, "page": page, "per_page": MAX_PER_PAGE}
        while True:
            resp = session.get(url, params=params)
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                _wait_for_rate_limit(resp)
                continue
            break

        if resp.status_code == 422:
            err = resp.json()
            details = "; ".join(e.get("message", "") for e in err.get("errors", []))
            print(f"    Query rejected: {err.get('message', '')} — {details}", flush=True)
            print(f"    Query was: {params.get('q', '')}", flush=True)
            break
        resp.raise_for_status()

        data = resp.json()
        items = data.get("items", [])
        results.extend(items)

        total = data.get("total_count", 0)
        if len(items) < MAX_PER_PAGE or len(results) >= min(total, max_results):
            break

        page += 1
        time.sleep(REQUEST_PAUSE)

    return results


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def _search_issues(
    session: requests.Session,
    repo: str,
    keywords: list[str],
    all_kws: list[str],
    is_pr: bool,
) -> list[dict]:
    kind = "pr" if is_pr else "issue"
    label = "pull_requests" if is_pr else "issues"
    seen: dict[int, dict] = {}

    for chunk in chunked(keywords, KEYWORD_CHUNK):
        kw_part = " OR ".join(quote_kw(kw) for kw in chunk)
        query = f"{kw_part} repo:{repo} is:{kind}"
        params = {"q": query, "sort": "updated", "order": "desc"}
        items = paginate(session, f"{GITHUB_API}/search/issues", params)
        time.sleep(REQUEST_PAUSE)

        for item in items:
            num = item["number"]
            if num in seen:
                # Merge any newly matched keywords
                body = (item.get("body") or "")
                title = item.get("title", "")
                new_matches = find_matching_keywords(f"{title} {body}", all_kws)
                existing = set(seen[num]["matched_keywords"])
                seen[num]["matched_keywords"] = sorted(existing | set(new_matches))
            else:
                body = (item.get("body") or "")
                title = item.get("title", "")
                entry = {
                    "number": num,
                    "title": title,
                    "url": item["html_url"],
                    "state": item["state"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "labels": [lb["name"] for lb in item.get("labels", [])],
                    "matched_keywords": find_matching_keywords(f"{title} {body}", all_kws),
                    "body_preview": body[:600],
                }
                entry["likely_noise"] = is_likely_noise(entry)
                seen[num] = entry

    results = list(seen.values())
    candidates = sum(1 for r in results if not r["likely_noise"])
    print(f"    {label}: {len(results)} total, {candidates} candidates", flush=True)
    return results


def _search_commits(
    session: requests.Session,
    repo: str,
    keywords: list[str],
    all_kws: list[str],
) -> list[dict]:
    orig_accept = session.headers["Accept"]
    session.headers["Accept"] = "application/vnd.github.cloak-preview+json"
    seen: dict[str, dict] = {}

    for chunk in chunked(keywords, KEYWORD_CHUNK):
        kw_part = " OR ".join(quote_kw(kw) for kw in chunk)
        params = {
            "q": f"{kw_part} repo:{repo}",
            "sort": "committer-date",
            "order": "desc",
        }
        items = paginate(session, f"{GITHUB_API}/search/commits", params)
        time.sleep(REQUEST_PAUSE)

        for item in items:
            sha = item["sha"]
            message = item.get("commit", {}).get("message", "")
            if sha not in seen:
                entry = {
                    "sha": sha[:12],
                    "message_first_line": message.split("\n")[0],
                    "url": item["html_url"],
                    "date": item.get("commit", {}).get("committer", {}).get("date", ""),
                    "matched_keywords": find_matching_keywords(message, all_kws),
                }
                entry["likely_noise"] = is_likely_noise(entry)
                seen[sha] = entry
            else:
                new_matches = find_matching_keywords(message, all_kws)
                existing = set(seen[sha]["matched_keywords"])
                seen[sha]["matched_keywords"] = sorted(existing | set(new_matches))
                seen[sha]["likely_noise"] = is_likely_noise(seen[sha])

    session.headers["Accept"] = orig_accept
    results = list(seen.values())
    candidates = sum(1 for r in results if not r["likely_noise"])
    print(f"    commits: {len(results)} total, {candidates} candidates", flush=True)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape ZKP compiler repos for logical bugs via GitHub Search API."
    )
    parser.add_argument(
        "--repos",
        nargs="+",
        choices=list(REPOS.keys()),
        default=list(REPOS.keys()),
        help="Repos to scrape (default: all)",
    )
    parser.add_argument("--no-commits", action="store_true", help="Skip commit search")
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub personal access token (or set GITHUB_TOKEN env var)",
    )
    args = parser.parse_args()

    if not args.token:
        print(
            "WARNING: No GitHub token — rate limit is 10 req/min (very slow).\n"
            "         Set GITHUB_TOKEN env var for 30 req/min.\n",
            file=sys.stderr,
        )

    kw_dict = load_keywords(KEYWORDS_FILE)
    all_kws = flatten_keywords(kw_dict)
    categories = list(kw_dict.keys())
    print(f"Loaded {len(all_kws)} unique keywords across {len(categories)} categories.")
    print(f"Categories: {', '.join(categories)}\n")

    session = make_session(args.token)
    RESULTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = RESULTS_DIR / f"{timestamp}_results.json"

    all_results: dict = {
        "metadata": {
            "scraped_at": timestamp,
            "repos": {k: REPOS[k] for k in args.repos},
            "keyword_categories": categories,
            "keywords": kw_dict,
        },
        "results": {},
    }

    for repo_key in args.repos:
        repo = REPOS[repo_key]
        print(f"=== {repo} ===", flush=True)

        repo_results: dict[str, list] = {}
        repo_results["issues"] = _search_issues(session, repo, all_kws, all_kws, is_pr=False)
        repo_results["pull_requests"] = _search_issues(session, repo, all_kws, all_kws, is_pr=True)

        if not args.no_commits:
            repo_results["commits"] = _search_commits(session, repo, all_kws, all_kws)

        all_results["results"][repo_key] = repo_results

        # Save incrementally so partial results survive interruption
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"  Saved → {output_file.name}\n", flush=True)

    # Summary
    print("=== Summary (total → candidates after noise filtering) ===")
    for rk, res in all_results["results"].items():
        def counts(items: list) -> str:
            total = len(items)
            cands = sum(1 for x in items if not x.get("likely_noise"))
            return f"{total:>4} → {cands:>4}"
        i = counts(res.get("issues", []))
        p = counts(res.get("pull_requests", []))
        c = counts(res.get("commits", []))
        print(f"  {REPOS[rk]:<30}  issues {i}   PRs {p}   commits {c}")
    print(f"\nFull results: {output_file}")


if __name__ == "__main__":
    main()
