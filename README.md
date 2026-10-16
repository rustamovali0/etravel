# Etravel QA Checklist

`index.html` is the application and contains its Supabase project URL, public
publishable API key and table name (`qa_test_cases`).

## Automated Supabase check

The **Supabase keepalive** GitHub Actions workflow checks the database every two
calendar days. GitHub evaluates the schedule daily at **10:17 Asia/Baku (06:17 UTC)**;
the Python script skips dates less than two days after the last successful check.
This works across month and year boundaries. Failed checks are retried on the next
daily run. GitHub can delay scheduled runs.

Each check sends a real, read-only PostgREST query (`SELECT id LIMIT 1`) against
the dedicated `etravel_keepalive` table using the application's public API key.
It never inserts, updates or deletes
test cases, and it does not print returned rows or API keys. No additional GitHub
secrets or Supabase service-role key are needed.

After success, the workflow commits `.github/supabase-keepalive.json`, containing
the time of the last successful query. This also generates repository activity to
avoid GitHub's 60-day inactivity timeout for scheduled workflows in public repos.
The commit uses `[skip ci]` and does not retrigger this workflow. The workflow needs
`contents: write`; a future branch rule blocking bot pushes will fail this step.

Before enabling the workflow, run [`supabase/keepalive.sql`](supabase/keepalive.sql)
once in the configured project's Supabase SQL Editor. It creates a one-row health
table with RLS and grants the anonymous role permission to read only its `id`.
It grants no anonymous insert, update or delete permission. No existing test
cases are touched. The SQL is transactional and can be rerun.

The first check runs when this workflow is pushed or merged to `main`. To check
immediately afterward, open **Actions → Supabase keepalive → Run workflow → main**. A manual
run always queries, even if the next scheduled check is not due yet. Inspect the
Actions logs for errors; a failed query does not advance the success timestamp.

Supabase may still pause Free projects with insufficient activity: its current
guidance mentions a few database requests each day. A query every two days is a
best-effort check, not a guarantee against pausing. If already paused, first use
**Resume project** in the Supabase dashboard, then rerun the workflow. Paid plans
are exempt from inactivity pausing.

During inspection on 2026-10-16, the application query to `qa_test_cases` returned
HTTP 404 / `PGRST205` (table not found in the schema cache). That is separate from
the keepalive table. Confirm the application's project URL and restore or correct
its table before expecting the QA checklist to load data.

References: [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing),
[GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
