#!/usr/bin/env python3
"""Query the app's Supabase table and record success without changing app data."""

import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / ".github/supabase-keepalive.json"


def main():
    now = datetime.now(timezone.utc)
    # A daily scheduler plus a persisted date avoids cron's month-boundary gaps.
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and STATUS_FILE.exists():
        previous = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        last_success = datetime.fromisoformat(previous["last_success_utc"])
        if (now.date() - last_success.date()).days < 2:
            print("Next Supabase check is not due yet.")
            return

    html = (ROOT / "index.html").read_text(encoding="utf-8")

    def setting(name):
        match = re.search(r"\bconst\s+" + name + r"\s*=\s*(['\"])([^'\"]+)\1", html)
        if not match:
            raise ValueError(f"Missing {name} in index.html")
        return match.group(2)

    base_url = setting("SUPABASE_URL").rstrip("/")
    api_key = setting("SUPABASE_ANON_KEY")
    table = setting("TABLE_NAME")
    if not re.fullmatch(r"https://[a-z0-9-]+\.supabase\.co", base_url):
        raise ValueError("Expected the app's HTTPS Supabase project URL")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", table):
        raise ValueError("Invalid Supabase table name")
    # tc_id is already used by the application. No row contents enter the logs.
    url = f"{base_url}/rest/v1/{table}?{urlencode({'select': 'tc_id', 'limit': 1})}"
    headers = {"apikey": api_key, "Accept": "application/json", "Cache-Control": "no-cache"}
    # Publishable sb_ keys are API keys, not JWTs. Legacy anon JWTs need both headers.
    if api_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {api_key}"

    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                if response.status != 200:
                    raise ValueError(f"Unexpected HTTP status: {response.status}")
                data = json.load(response)
                if not isinstance(data, list):
                    raise ValueError("Expected a table query result")
            break
        except HTTPError as error:
            if attempt == 2 or (error.code != 429 and error.code < 500):
                raise RuntimeError(
                    f"Supabase query failed (HTTP {error.code}). "
                    "Check project status, the public API key and table read permissions."
                ) from None
            print(f"Supabase returned HTTP {error.code}; retrying.")
        except (URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError("Supabase query failed after 3 network attempts.") from None
            print("Supabase network request failed; retrying.")
        time.sleep(5 * (attempt + 1))

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps({
            "last_success_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "table": table,
            "operation": "SELECT tc_id LIMIT 1",
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Supabase database query succeeded. Application data was preserved.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"Supabase keepalive failed: {error}", file=sys.stderr)
        sys.exit(1)
