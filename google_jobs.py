"""Google Jobs from Python: a small client for the hosted Google Jobs scraper.

Google does not answer plain HTTP requests for its Jobs results (see README), so this
script does not scrape Google itself. It starts the Apify Actor
"datalume/google-jobs-scraper" with your own Apify token, waits for it and prints the
jobs as JSON or CSV. Standard library only.

    set APIFY_TOKEN=...            (Linux/macOS: export APIFY_TOKEN=...)
    python google_jobs.py "software engineer" --location "New York, NY"
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ACTOR = "datalume~google-jobs-scraper"
ACTOR_URL = "https://apify.com/datalume/google-jobs-scraper"
API = "https://api.apify.com/v2"
TOKEN_HELP = ("APIFY_TOKEN is not set. Create a token at https://console.apify.com/settings/integrations "
              f"and put it in the APIFY_TOKEN environment variable. Actor: {ACTOR_URL}")

DATE_POSTED = ("any", "today", "3days", "week", "month")
EMPLOYMENT = ("any", "fulltime", "parttime", "contract", "internship")
COVERAGE = ("fast", "standard", "max")
CSV_FIELDS = ["title", "company", "location", "via", "postedAgo", "schedule", "salary",
              "applyUrl", "jobId", "searchQuery", "searchLocation"]
DONE = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
RUN_ID_RX = re.compile(r"^[A-Za-z0-9]{17}$")


def google_jobs_url(query, location="", country="us", language="en"):
    """The Google Jobs page for a search, to open in a browser."""
    q = f"{query} {location}".strip()
    return ("https://www.google.com/search?q=" + urllib.parse.quote_plus(q)
            + f"&udm=8&hl={urllib.parse.quote(language)}&gl={urllib.parse.quote(country)}")


def build_input(queries, locations=None, country="us", language="en", date_posted="any",
                employment_type="any", remote_only=False, coverage="standard",
                max_jobs_per_search=100, max_jobs=0):
    queries = [q.strip() for q in (queries or []) if q and q.strip()]
    if not queries:
        raise ValueError("give at least one job search query, e.g. 'registered nurse'")
    if date_posted not in DATE_POSTED:
        raise ValueError("date_posted must be one of: " + ", ".join(DATE_POSTED))
    if employment_type not in EMPLOYMENT:
        raise ValueError("employment_type must be one of: " + ", ".join(EMPLOYMENT))
    if coverage not in COVERAGE:
        raise ValueError("coverage must be one of: " + ", ".join(COVERAGE))
    return {
        "queries": queries,
        "locations": [x.strip() for x in (locations or []) if x and x.strip()],
        "country": (country or "us").lower(),
        "language": language or "en",
        "datePosted": date_posted,
        "employmentType": employment_type,
        "remoteOnly": bool(remote_only),
        "coverage": coverage,
        "maxJobsPerSearch": max(1, int(max_jobs_per_search)),
        "maxJobs": max(0, int(max_jobs)),
    }


def _call(method, url, token, body=None, timeout=90):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Apify returned HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")


def _token(token=None):
    token = token or os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError(TOKEN_HELP)
    return token


def console_url(run_id):
    return f"https://console.apify.com/actors/runs/{run_id}"


def start_run(run_input, token=None, max_total_charge_usd=0.25):
    """Start the Actor and return at once: {"run_id", "status"}."""
    run = _call("POST", f"{API}/acts/{ACTOR}/runs?maxTotalChargeUsd={float(max_total_charge_usd)}",
                _token(token), run_input)["data"]
    return {"run_id": run["id"], "status": run.get("status")}


def run_info(run_id, token=None, wait_secs=0):
    """Status of a run. With wait_secs > 0 Apify holds the request until the run finishes (at most 60 s)."""
    if not RUN_ID_RX.match(run_id or ""):
        raise ValueError("run_id does not look like an Apify run ID (17 letters and digits)")
    wait = int(max(0, min(60, wait_secs)))
    return _call("GET", f"{API}/actor-runs/{run_id}?waitForFinish={wait}", _token(token), timeout=wait + 30)["data"]


def run_items(run, token=None):
    """Jobs saved by a run (the dict returned by run_info)."""
    return _call("GET", f"{API}/datasets/{run['defaultDatasetId']}/items?clean=true&format=json", _token(token))


def run_actor(run_input, token=None, max_total_charge_usd=0.25, wait_secs=900):
    """Start the Actor, wait until it finishes (at most wait_secs) and return its jobs."""
    token = _token(token)
    run_id = start_run(run_input, token, max_total_charge_usd)["run_id"]
    deadline = time.monotonic() + wait_secs
    while True:
        left = deadline - time.monotonic()
        run = run_info(run_id, token, wait_secs=max(1, left))
        if run["status"] in DONE:
            break
        if left <= 60:
            raise RuntimeError(f"The run is still {run['status']} after {wait_secs}s. It keeps running on Apify; "
                               f"open {console_url(run_id)} to see or export the results.")
    items = run_items(run, token)
    if run["status"] != "SUCCEEDED" and not items:
        raise RuntimeError(f"The run ended with status {run['status']} and no jobs. Details: {console_url(run_id)}")
    return items


def main(argv=None):
    p = argparse.ArgumentParser(description="Google Jobs listings (title, company, salary, description, apply links) "
                                            "through the hosted Apify Actor datalume/google-jobs-scraper.")
    p.add_argument("query", nargs="+", help='job title, skill or company, e.g. "registered nurse". Several allowed')
    p.add_argument("--location", action="append", default=[], help='city, region or country, e.g. "Houston, TX". Repeatable')
    p.add_argument("--country", default="us", help="2-letter country Google searches from (default us)")
    p.add_argument("--language", default="en", help="Google language, e.g. en, de, ja (default en)")
    p.add_argument("--date", default="any", choices=DATE_POSTED, help="date posted (default any)")
    p.add_argument("--type", default="any", choices=EMPLOYMENT, help="employment type, English searches (default any)")
    p.add_argument("--remote", action="store_true", help="remote jobs only (English searches)")
    p.add_argument("--coverage", default="standard", choices=COVERAGE, help="requests per search: fast 3, standard 9, max 13")
    p.add_argument("--max-jobs", type=int, default=0, help="stop the run after this many jobs (0 = no limit)")
    p.add_argument("--max-charge", type=float, default=0.25, help="spending cap for this run in USD (default 0.25)")
    p.add_argument("--csv", metavar="FILE", help="write CSV instead of printing JSON")
    a = p.parse_args(argv)
    try:
        run_input = build_input(a.query, a.location, a.country, a.language, a.date, a.type,
                                a.remote, a.coverage, 100, a.max_jobs)
        jobs = run_actor(run_input, max_total_charge_usd=a.max_charge)
    except (RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(jobs)
        print(f"{len(jobs)} jobs -> {a.csv}", file=sys.stderr)
    else:
        json.dump(jobs, sys.stdout, ensure_ascii=False, indent=2)
        print(file=sys.stdout)
        print(f"{len(jobs)} jobs", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
