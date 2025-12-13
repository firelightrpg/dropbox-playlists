"""
Generate SAPISIDHASH authorization header from SAPISID cookie.
Run this when you need to refresh the authorization header in browser.json.

To get your SAPISID:
1. Go to Firefox DevTools -> Storage -> Cookies -> music.youtube.com
2. Find the cookie named "SAPISID"
3. Copy its value and add it to .env as SAPISID=<value>
"""

import hashlib
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()


def generate_sapisidhash(
    sapisid: str, origin: str = "https://music.youtube.com"
) -> str:
    """Generate SAPISIDHASH from SAPISID cookie value."""
    ts = int(time.time())
    h = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{h}"


if __name__ == "__main__":
    sapisid = os.environ.get("SAPISID")

    if not sapisid:
        if len(sys.argv) > 1:
            sapisid = sys.argv[1]
        else:
            print("Error: SAPISID not found in .env or as argument")
            print("Add SAPISID=<your_value> to .env file")
            sys.exit(1)

    print(generate_sapisidhash(sapisid))
