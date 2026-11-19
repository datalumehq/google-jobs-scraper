# Google Jobs Scraper (Python client + MCP server)

Get **Google Jobs** listings (the job box in Google Search) as JSON or CSV from Python, or as a tool for Claude, Cursor and other MCP clients: title, company, location, salary, posted date, the **full job description** and the **real apply URLs**.

```bash
python google_jobs.py "software engineer" --location "New York, NY" --date week
```

**What this repository is, plainly:** a small open-source client (about 150 lines, standard library only) and an MCP server. They do not scrape Google themselves. The scraping runs in a hosted Apify Actor, **[Google Jobs Scraper - Descriptions, Apply Links & Salary](https://apify.com/datalume/google-jobs-scraper)**, which you call with your own Apify token and pay per unique job. The next two sections explain why there is no key-free script here.

## Is there a Google Jobs API?

No. Google does not offer a public API for the job listings it shows in Search. To get them as data you either load the Google Jobs page yourself or use a service that does.

## Why a plain HTTP request does not work

We tested it. On **19 November 2026**, from a home connection, one request with a normal Chrome user agent:

```bash
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36" \
  "https://www.google.com/search?q=software+engineer+New+York&udm=8&hl=en&gl=us" -o page.html
```

Result: a 94 KB page with **0 job listings**. It is not a CAPTCHA and not a block of the IP address; the page only contains a redirect to `/httpservice/retry/enablejs`, Google's "turn on JavaScript" page. `requests`, `urllib` and `curl` all get that page, so a script of the "download the HTML and parse it" kind returns nothing.

The hosted Actor gets the full Jobs page through a search-results proxy and then handles the rest: Google gives about 10 jobs per request and no page 2, so it repeats each search with Google's own filters and merges the results, removes duplicates, and asks again when Google answers with a short page. On 19 November 2026 the default search ("software engineer", New York) returned **57 unique jobs from 9 requests in 84 seconds**.

## Quick start

Requires Python 3.8+ and an Apify account (a free plan works; you need its API token). Nothing to install for the script.

```bash
git clone https://github.com/datalumehq/google-jobs-scraper.git
cd google-jobs-scraper

# Windows: set APIFY_TOKEN=apify_api_...
export APIFY_TOKEN=apify_api_...
python google_jobs.py "registered nurse" --location "Houston, TX"
```

Get a token at [console.apify.com/settings/integrations](https://console.apify.com/settings/integrations). Every run has a spending cap (`--max-charge`, default $0.25): the Actor stops when the cap is reached.

## Options

| Option | What it does | Example |
|---|---|---|
| `query` | Job title, skill or company (required). Several allowed | `"data analyst" "data engineer"` |
| `--location` | City, region or country. Repeatable; every query is searched in every location | `--location "London"` |
| `--country` | 2-letter country Google searches from (default `us`) | `--country gb` |
| `--language` | Google language (default `en`). Use the local one outside English-speaking countries | `--language de` |
| `--date` | `any`, `today`, `3days`, `week` or `month` | `--date today` |
| `--type` | `fulltime`, `parttime`, `contract` or `internship` (English searches) | `--type contract` |
| `--remote` | Remote jobs only (English searches) | `--remote` |
| `--coverage` | Requests per search: `fast` (3), `standard` (9), `max` (13). More requests = more unique jobs | `--coverage max` |
| `--max-jobs` | Stop the run after this many jobs (0 = no limit) | `--max-jobs 50` |
| `--max-charge` | Spending cap for the run in USD (default 0.25) | `--max-charge 1` |
| `--csv FILE` | Write CSV instead of printing JSON | `--csv jobs.csv` |

## Output

One object per unique job. A real row from 19 November 2026 (`sample_output.json`), with the long fields shortened (the description, highlights and URLs are cut with "…"; this job had 8 apply links, 3 shown):

```json
{
  "title": "Sr Software Engineer - AI and Observability",
  "company": "Disney Entertainment & Sports LLC",
  "location": "New York, NY",
  "via": "Indeed",
  "postedAgo": "2 days ago",
  "schedule": "Full-time",
  "salary": "149K-199K a year",
  "salaryText": "149K-199K a year",
  "applyUrl": "https://www.linkedin.com/jobs/view/sr-software-engineer-ai-and-observability-at-the-walt-disney-company-4491705793?utm_c…",
  "applyLinks": [
    {
      "site": "Indeed",
      "url": "https://www.indeed.com/viewjob?jk=a1a02d95f912eaa9&utm_campaign=google_jobs_apply&utm_sour…",
      "direct": false,
      "titleMatch": null
    },
    {
      "site": "LinkedIn",
      "url": "https://www.linkedin.com/jobs/view/sr-software-engineer-ai-and-observability-at-the-walt-d…",
      "direct": false,
      "titleMatch": true
    },
    {
      "site": "ShowbizJobs",
      "url": "https://www.showbizjobs.com/jobs/disney-sr-software-engineer-ai-and-observability-in-new-y…",
      "direct": true,
      "titleMatch": true
    }
  ],
  "highlights": {
    "Qualifications": [
      "5+ years of applicable experience in backend development, with a proven track record of building and scaling AI-powered or data-driven applications",
      "…"
    ],
    "Benefits": [
      "Job Posting Statement The hiring range for this position in New York City, NY is $148,700 - $199,400 per year, and in Glendale, CA is $141,900 - $190,300 per ye …",
      "…"
    ],
    "Responsibilities": [
      "Innovation: We develop and implement groundbreaking products and techniques that shape industry norms and solve complex and distinctive technical problems",
      "…"
    ]
  },
  "description": "Job Requirements\n\nJob Description\n\nDisney Entertainment and ESPN Product & Technology\n\nTechnology is at the heart of Disney’s past, present, and future. Disney Entertainment and ESPN Product & Technology is a global organization of engineers, product developers, designers, technologists, data scientists, and more – all working to build and advance the technological backbone for Disney’s media busi …",
  "tags": [
    "2 days ago",
    "149K-199K a year",
    "Full-time",
    "Health insurance"
  ],
  "jobId": "pjSsvYmU8sFPWpW-AAAAAA==",
  "googleJobsUrl": "https://www.google.com/search?ibp=htl;jobs&q=software+engineer+New+York,+NY+full+time&htidocid=pjSsvYmU8sFPWpW-AAAAAA%3D…",
  "searchQuery": "software engineer",
  "searchLocation": "New York, NY",
  "country": "us",
  "language": "en",
  "scrapedAt": "2026-11-19T12:16:44+00:00"
}
```

`--csv` writes the flat columns: title, company, location, via, postedAgo, schedule, salary, applyUrl, jobId, searchQuery, searchLocation. Use JSON when you need the description, highlights or all apply links.

## What it costs

The client and the MCP server are free and MIT licensed. The Actor is **paid per unique job saved**, billed by Apify to your own account; the current price is on the [Actor page](https://apify.com/datalume/google-jobs-scraper). Searches with no results, pages Google blocked and duplicate jobs are not charged.

## Use it as an MCP server

[![Google Jobs MCP server – quality and maintenance score on Glama](https://glama.ai/mcp/servers/datalumehq/google-jobs-scraper/badges/score.svg)](https://glama.ai/mcp/servers/datalumehq/google-jobs-scraper)

`mcp_server.py` exposes three tools to any MCP client (Claude Desktop, Claude Code, Cursor, VS Code). Requires Python 3.10+.

| Tool | Cost | What it returns |
|---|---|---|
| `google_jobs_link` | Free, no API key, no network request | The Google Jobs page URL for a search, for you to open in a browser. A link only, no job data |
| `start_job_search` | Paid per unique job through your Apify account (price on the [Actor page](https://apify.com/datalume/google-jobs-scraper)) | Starts a search and returns a `run_id` at once. Filters: date posted, employment type, remote. Each search has a spending cap (`max_total_charge_usd`, default $0.25) and a job limit (`max_jobs`, default 20) |
| `get_job_results` | Free (reads the results of a search you started) | The listings as data once the search has finished: title, company, location, salary, posted date, full description, apply URLs. While the search is still running it says so and the client calls it again |

Why two steps: a search takes about a minute (59 seconds in our 19 November 2026 test with `fast` coverage), and some MCP clients stop waiting for a single tool call before that. Starting the search and fetching the results separately keeps every call short.

Install:

```bash
git clone https://github.com/datalumehq/google-jobs-scraper.git
cd google-jobs-scraper
pip install -r requirements.txt
```

Claude Desktop (`claude_desktop_config.json`), Cursor (`~/.cursor/mcp.json`) and most other clients use the same block. Use the full path to `mcp_server.py`:

```json
{
  "mcpServers": {
    "google-jobs": {
      "command": "python",
      "args": ["/path/to/google-jobs-scraper/mcp_server.py"],
      "env": { "APIFY_TOKEN": "<your Apify token, needed for start_job_search and get_job_results>" }
    }
  }
}
```

Claude Code:

```bash
claude mcp add google-jobs -e APIFY_TOKEN=<your token> -- python /path/to/google-jobs-scraper/mcp_server.py
```

Then ask in plain language, for example:

- "Find remote software engineer jobs posted today in the US and list the salaries"
- "Which companies are hiring registered nurses in Houston this week? Give me the apply links"

Without `APIFY_TOKEN` the link tool works and the other two return a message explaining how to add a token.

Prefer not to run anything locally? Apify's hosted MCP endpoint serves the same Actor: `https://mcp.apify.com?tools=datalume/google-jobs-scraper` (sign in with Apify on first use).

## Limits

- No Apify token, no job data: this repository cannot read Google Jobs on its own (see above).
- Google Jobs is not served in every country; searches there return nothing and cost nothing.
- Salary is present only when Google shows pay for the job.
- Employment type and remote filters use Google's English filter phrases. In other languages use `--date` and put the job type in the query.
- Google decides what it shows. Results can differ from what you see in your own browser.

## FAQ

**Is scraping Google Jobs allowed?**
The listings are public pages that Google shows to anyone without logging in. The Actor saves only the public job post, does not log in anywhere and collects no personal data. Check the terms and laws that apply to your use.

**Can I get more than 10 jobs per search?**
Yes. One request returns about 10 jobs; `--coverage standard` makes 9 requests with different Google filters and merges them (57 unique jobs in the 19 November 2026 test above). Niche searches return fewer.

**Can I run it daily for new jobs only?**
Yes: run it with `--date today` and the same queries each day. `jobId` lets you skip jobs you already have.

**Can I use requests/BeautifulSoup or Selenium instead?**
Plain HTTP libraries get the JavaScript page described above. A real browser can load Google Jobs, but that is a different kind of project (browser automation, proxies, blocks) and is not what this repository does.

**Something is missing or wrong?**
Please open an issue here.

## More

- Hosted Actor with all options, scheduling and exports: [apify.com/datalume/google-jobs-scraper](https://apify.com/datalume/google-jobs-scraper)
- Other scrapers by datalume: [apify.com/datalume](https://apify.com/datalume)

## License

MIT. Built with AI assistance; numbers come from real runs on the dates shown.

*Not affiliated with, endorsed by or sponsored by Google. This project only reads publicly available job listings shown by Google.*
