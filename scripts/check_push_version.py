#!/usr/bin/env python3
"""Pre-push gate: the local VERSION must be strictly ahead of the published one.

Exit codes: 0 = VERSION_OK, safe to push; 1 = BUMP_REQUIRED; 2 = COULD_NOT_VERIFY.
A missing remote VERSION (first release) counts as 0.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "Lzjin426/push-code"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/main/VERSION"
VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"


def parse(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def fetch_raw() -> str:
    with urllib.request.urlopen(RAW_URL, timeout=3) as response:
        return response.read().decode("utf-8").strip()


def fetch_gh() -> str:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/VERSION", "--jq", ".content"],
        capture_output=True,
        text=True,
        timeout=4,
    )
    if result.returncode != 0:
        if "404" in result.stderr:
            raise FileNotFoundError("remote VERSION missing")
        raise RuntimeError(result.stderr.strip() or "gh api failed")
    return base64.b64decode(result.stdout.strip()).decode("utf-8").strip()


def main() -> int:
    try:
        local = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        print("COULD_NOT_VERIFY missing-local-version")
        return 2
    remote = ""
    missing = 0
    for fetch in (fetch_raw, fetch_gh):
        try:
            remote = fetch()
            break
        except FileNotFoundError:
            missing += 1
        except urllib.error.HTTPError as error:
            if error.code == 404:
                missing += 1
        except Exception:
            pass
    if not remote:
        if missing == 2:
            print(f"VERSION_OK local={local} remote=none-first-release")
            return 0
        print("COULD_NOT_VERIFY network-unavailable")
        return 2
    if parse(local) > parse(remote):
        print(f"VERSION_OK local={local} remote={remote}")
        return 0
    print(f"BUMP_REQUIRED local={local} remote={remote} https://github.com/{REPO}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
