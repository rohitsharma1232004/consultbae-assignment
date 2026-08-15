# ConsultBae AI Automation Assignment — Task 1: Data Merge

## What this does

Merges 3 messy CSV files from different systems (Naukri applicants, gig workers,
CBNexus contacts) into a single deduplicated MySQL database. No single ID field
is common across all 3 files — matching is done via a bridge strategy: File 1
(naukri) has both email and phone, so it links File 2 (email-only) and File 3
(phone-only) together transitively, with a fuzzy name+city fallback for the rest.

**Result: 100 raw rows across 3 files → 55 unique people.**

## Project structure
consultbae-assignment/
├── data/
│ ├── raw/ # original 3 CSVs
│ └── processed/ # auto-generated data_issues_report.md
├── scripts/
│ ├── config.py # DB connection (reads .env)
│ ├── normalize.py # phone/email/city/date/CTC/rate cleaning functions
│ ├── entity_resolution.py # union-find matching logic across files
│ └── run_pipeline.py # main script - run this
├── sql/
│ └── schema.sql # MySQL table definitions
├── requirements.txt
└── .env.example # copy to .env and fill in your MySQL password

## How to run it

**Requirements:** Python 3.10+, MySQL Server (running locally)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Create the database
mysql -u root -p -e "CREATE DATABASE consultbae;"

# 3. Apply the schema
# (Windows PowerShell users: use Get-Content instead of <)
mysql -u root -p consultbae < sql/schema.sql

# 4. Set up your .env file (copy .env.example -> .env, add your MySQL password)

# 5. Run the pipeline
python scripts/run_pipeline.py
```

Expected output:
Loading and cleaning each source file...
naukri: 40 clean rows, gig: 30 clean rows, cbnexus: 30 clean rows
Resolving entities across files...
100 total rows -> 55 unique people
Done. 55 unique people created from 100 source rows.

## Matching strategy

Rows across all 3 files are unioned into groups (Union-Find / connected
components) whenever they share a normalized email OR a normalized phone
number. Because File 1 (naukri) contains BOTH fields, it acts as a bridge:
a File 2 row and a File 3 row that never share a direct key can still end
up in the same group by both linking through the same File 1 row.

Rows left unmatched after that get one more pass: fuzzy name match (≥88
similarity) **and** matching city. If more than one equally-good candidate
is found (ambiguous), the rows are deliberately **not** auto-merged — a
wrong merge silently corrupts two people's records, which is worse than
leaving two rows for one person. Every match (or non-match) is logged in
the `match_log` table with a method and confidence score, so any merge
can be traced back and audited.

## Data issues found and how they were handled

| Source | Issue | Action taken |
|---|---|---|
| source1_naukri | Phone format inconsistent (`+91...`, `0...`, plain 10-digit) | Normalized to plain 10-digit by stripping non-digits and country code |
| source1_naukri | pandas silently reads Phone as int64, stripping `+`/leading `0` if not forced to string | Loaded with `dtype=str` explicitly |
| source1_naukri | City casing/whitespace inconsistent; `Bangalore`/`Bengaluru`, `Gurgaon`/`Gurugram` used as synonyms | Canonicalized via a lookup map to one spelling per city |
| source1_naukri | Applied Date mixes 4 formats (`DD-MM-YYYY`, `YYYY-MM-DD`, `D Mon YYYY`, `MM/DD/YYYY`); some values genuinely ambiguous | Parsed with a 4-format cascade; ambiguous values assumed `MM/DD/YYYY` |
| source1_naukri | Current CTC mixes lakhs (`2.4`) and absolute rupees (`327287`) in one column | Any value < 100 treated as lakhs, multiplied by 100000 |
| source1_naukri | Intra-file duplicate: same email+phone, name written differently (`R. Verma` vs `Rohit Verma`) | Kept the row with the fuller name, dropped the other |
| source1_naukri | Intra-file duplicate: same phone, different email (repeat submission) | Kept the first submission, dropped the duplicate |
| source2_gig_workers | Fully blank row | Dropped |
| source2_gig_workers | Malformed row: all values shifted one column left, corrupted duplicate of an existing correct row | Detected via invalid email format, dropped |
| source2_gig_workers | Email casing inconsistent (some fully uppercase) | Lowercased for matching |
| source2_gig_workers | Rate column mixes hourly (`1415/hr`) and monthly (`72k/month`) pay | Parsed into separate `rate_amount` + `rate_unit` fields (not converted — no reliable hours/month figure to convert safely) |
| source3_cbnexus | Header row re-injected as a data row | Detected and dropped |
| source3_cbnexus | Phone format inconsistent (3 formats mixed) | Normalized to plain 10-digit |
| source3_cbnexus | Two rows named "Arjun Mehta", same city, but **different** phone numbers | Kept as two separate people — name+city alone isn't reliable enough evidence to merge; one candidate matched File 1 by phone, the other was later fuzzy-matched to a different, unambiguous File 2 row |

*(Full machine-generated version of this table: `data/processed/data_issues_report.md`)*

## Stuck log

**1. PowerShell doesn't support `<` for file redirection into a command.**
Running `mysql -u root -p consultbae < sql/schema.sql` failed with
`The '<' operator is reserved for future use`. Searched the exact error text,
found that PowerShell needs piping instead of shell-style redirection. Fixed
with: `Get-Content sql/schema.sql | mysql -u root -p consultbae`. I didn't
just switch to Git Bash to avoid the issue, because the assignment will be
run by an evaluator on their own machine — solving it the PowerShell way
keeps the README accurate for a Windows setup.

**2. `mysql` command not recognized in PowerShell despite MySQL being installed.**
MySQL Server was installed, but its `bin` folder wasn't in the Windows PATH
environment variable, so PowerShell couldn't find `mysql.exe`. Located the
actual install path (`C:\Program Files\MySQL\MySQL Server 8.0\bin`) by
searching the whole C: drive for `mysql.exe`, then added that folder to the
system PATH permanently via Environment Variables, and restarted the
terminal so the new PATH would load. Considered just calling the full path
every time instead, but fixing PATH once is less error-prone for repeated
use across the rest of the assignment (Task 2/3 will also need MySQL access).

**3. `git push` hung on "please complete authentication in your browser" and the browser tab looked broken, so it got closed.**
First attempt: closed the tab thinking it failed, which just abandoned the
auth flow (the terminal was still waiting for it). Re-ran `git push -u origin
main` a second time, let the new browser tab load fully this time, and
authorized the GitHub device flow properly. It succeeded on retry — the
underlying "issue" wasn't a real bug, just closing the auth tab too early.
Was ready to fall back to a Personal Access Token if the retry failed again,
since that avoids the browser flow entirely, but it wasn't needed.

## Tools used

- **Python 3.11** — pandas, mysql-connector-python, rapidfuzz, python-dotenv
- **MySQL 8.0** — data storage
- **Union-Find (custom implementation)** — entity resolution across files
- **Git + GitHub** — version control
- **Claude** — used to design the matching strategy, write and debug the
  pipeline code, and troubleshoot the Windows/PowerShell/Git environment
  issues listed above. Every function was reviewed and tested against the
  actual data before being kept; normalization thresholds (e.g. the fuzzy
  match score of 88, the CTC lakhs/rupees cutoff of 100) were chosen by
  inspecting the real value distributions in the CSVs, not defaults taken
  on faith.

## Task 2: n8n Automation — LLM-based Skill Tagging

**Flow:** `n8n/skill-tagging-workflow.json`

A manually-triggered n8n workflow that:
1. Queries MySQL for every person who doesn't yet have a `skill_category`,
   combining their skills from `staging_naukri` and `staging_gig_workers`
2. Loops over each person one at a time (Loop Over Items, batch size 1)
3. Sends their combined skills to **Google Gemini** (`gemini-flash-lite-latest`)
   with a classification prompt, asking it to pick one of:
   `automation-heavy`, `web dev`, `data`, `other`
4. Waits 5 seconds (to stay within Gemini's free-tier rate limit of
   15 requests/minute)
5. Writes the returned category back into `people.skill_category` in MySQL
6. Loops back for the next person, until all are tagged

**Result:** all 55 people successfully classified, 0 left untagged.

### Why Gemini free tier instead of a paid API

The task only requires "an LLM step" - it doesn't specify a paid provider.
Google AI Studio's Gemini free tier requires no credit card and comfortably
covers this volume (1,500 requests/day vs. the 55 needed here), so using it
kept this take-home assignment at zero cost without compromising on using a
real, capable LLM.

### Why `gemini-flash-lite-latest` specifically

This is a simple single-label classification task with no need for deep
reasoning, so the lightest/fastest model was the right fit - `gemini-2.5-pro`
would have added latency and a much stricter free-tier cap (50 requests/day)
for no quality benefit here. The `-latest` alias was chosen over a pinned
version number after an earlier pinned model (`gemini-3.5-flash-lite`) was
deprecated for new users mid-task; the alias avoids that failure mode going
forward.

### Why "Loop Over Items" + "Wait" instead of relying on n8n's per-item execution

n8n normally fires a downstream node once per input item without any node
telling it to. Left alone, that meant all 55 requests hit the Gemini API
back-to-back and the free tier's 15 requests/minute limit was exceeded by
item 16. Wrapping the LLM call in an explicit Loop Over Items (batch size 1)
→ Gemini → Wait (5s) → back to Loop cycle throttles requests to roughly
12/minute, comfortably under the limit, at the cost of the whole run taking
~5 minutes instead of a few seconds.