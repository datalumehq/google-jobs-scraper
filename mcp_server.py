"""MCP server for Google Jobs.

Three tools:
  google_jobs_link     free, no API key, no network: the Google Jobs page for a search,
                       for the user to open in a browser
  start_job_search     needs an Apify token: starts a search and returns a run_id at once
  get_job_results      needs an Apify token: the jobs of that search once it has finished

A search takes about a minute, longer than some MCP clients wait for one tool call, so
searching is split into "start" and "get results". Jobs are paid per unique job.

Run:  pip install "mcp>=1.2,<2" && python mcp_server.py      (stdio transport)
"""
from mcp.server.fastmcp import FastMCP

import google_jobs as gj

mcp = FastMCP("google-jobs")


@mcp.tool()
def google_jobs_link(query: str, location: str = "", country: str = "us", language: str = "en") -> str:
    """Build the Google Jobs web page URL for a job search, for the user to open in a browser. Free, no API key, makes no network request.

    It returns only a link, not job data: Google does not return job listings to plain
    HTTP requests, so this server cannot read that page itself. Use start_job_search
    when the listings are needed as data.

    Args:
        query: job title, skill or company, e.g. "registered nurse".
        location: city, region or country, e.g. "Houston, TX". Empty = no location.
        country: 2-letter country Google searches from, e.g. "us", "gb", "de".
        language: Google language code, e.g. "en", "de", "ja".
    """
    if not (query or "").strip():
        raise ValueError("query is empty, e.g. 'registered nurse'")
    return gj.google_jobs_url(query.strip(), (location or "").strip(), country or "us", language or "en")


@mcp.tool()
def start_job_search(queries: list[str], locations: list[str] | None = None, country: str = "us",
                     language: str = "en", date_posted: str = "any", employment_type: str = "any",
                     remote_only: bool = False, coverage: str = "fast", max_jobs: int = 20,
                     max_total_charge_usd: float = 0.25) -> dict:
    """Start a Google Jobs search and return a run_id immediately. Step 1 of 2: then call get_job_results(run_id) to get the listings (title, company, location, salary, posted date, full job description and the real apply URLs).

    Starts the hosted Apify Actor "datalume/google-jobs-scraper" with your own Apify
    account. Requires the APIFY_TOKEN environment variable. It is PAID per unique job
    saved (current price: https://apify.com/datalume/google-jobs-scraper ); searches with
    no results and blocked pages are not charged. Starting a search spends money even if
    the results are never fetched, so start one only when the user wants job data. The
    run stops at max_jobs and at max_total_charge_usd. Every query is searched in every
    location; one search takes about a minute (19 Nov 2026: 59 s with "fast" coverage).

    Args:
        queries: job titles, skills or companies, e.g. ["registered nurse"].
        locations: cities, regions or countries, e.g. ["Houston, TX"]. Empty = no location.
        country: 2-letter country Google searches from, e.g. "us", "gb", "de", "in".
        language: Google language code. Use the local language outside English-speaking countries.
        date_posted: "any", "today", "3days", "week" or "month".
        employment_type: "any", "fulltime", "parttime", "contract" or "internship" (English searches).
        remote_only: remote / work-from-home jobs only (English searches).
        coverage: requests per search: "fast" (3), "standard" (9) or "max" (13). More requests = more unique jobs and a longer run.
        max_jobs: stop after this many jobs in total. Keep small to control cost and response size.
        max_total_charge_usd: hard spending cap for this search, in USD.
    """
    run_input = gj.build_input(queries, locations, country, language, date_posted, employment_type,
                               remote_only, coverage, 100, max(1, int(max_jobs)))
    run = gj.start_run(run_input, max_total_charge_usd=max_total_charge_usd)
    searches = len(run_input["queries"]) * max(1, len(run_input["locations"]))
    return {"run_id": run["run_id"], "status": run["status"], "searches": searches,
            "next": f"Call get_job_results with run_id {run['run_id']}. Expect about a minute per search."}


@mcp.tool()
def get_job_results(run_id: str, wait_secs: int = 40) -> dict:
    """Get the jobs found by a search started with start_job_search. Step 2 of 2. Reading results is free; it never starts a new search.

    Waits up to wait_secs for the search to finish. Returns {"finished", "status", "jobs",
    "message"}. If "finished" is false the search is still running and "jobs" is empty:
    call get_job_results again with the same run_id (do not start a new search).

    Args:
        run_id: the run_id returned by start_job_search.
        wait_secs: how long to wait for the search to finish, 0-45 seconds.
    """
    run = gj.run_info((run_id or "").strip(), wait_secs=max(0, min(45, int(wait_secs))))
    status = run["status"]
    if status not in gj.DONE:
        return {"finished": False, "status": status, "jobs": [],
                "message": "Still running. Call get_job_results again with the same run_id."}
    jobs = gj.run_items(run)
    if status == "SUCCEEDED":
        msg = f"{len(jobs)} jobs."
    else:
        msg = f"The run ended with status {status}; {len(jobs)} jobs were saved before that. Details: {gj.console_url(run['id'])}"
    return {"finished": True, "status": status, "jobs": jobs, "message": msg}


if __name__ == "__main__":
    mcp.run()
