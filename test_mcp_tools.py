"""Quick local check of the MCP tools without an MCP client.

    pip install "mcp>=1.2,<2"
    python test_mcp_tools.py              # free tool only
    set APIFY_TOKEN=...  then run again   # also runs one real search (spending cap $0.05)
"""
import os
import time

import mcp_server as s

print("google_jobs_link:", s.google_jobs_link("registered nurse", "Houston, TX"))

if os.environ.get("APIFY_TOKEN"):
    t = time.time()
    run = s.start_job_search(["software engineer"], ["New York, NY"], coverage="fast",
                             max_jobs=10, max_total_charge_usd=0.05)
    print("start_job_search:", run["run_id"], run["status"], "in", round(time.time() - t, 1), "s")
    calls = 0
    while True:
        calls += 1
        t1 = time.time()
        res = s.get_job_results(run["run_id"])
        print(f"get_job_results call {calls}: finished={res['finished']} status={res['status']} "
              f"in {round(time.time() - t1)} s")
        if res["finished"] or calls >= 10:
            break
    print(res["message"], "total", round(time.time() - t), "s")
    for r in res["jobs"][:3]:
        print(" ", r.get("title"), "|", r.get("company"), "|", r.get("salary"), "|", (r.get("applyUrl") or "")[:60])
else:
    try:
        s.start_job_search(["software engineer"])
    except RuntimeError as e:
        print("start_job_search without token ->", str(e)[:70], "...")
