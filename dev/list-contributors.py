#!/usr/bin/env python3
__doc__ = """
Extracts copyright information from software forges.
Also shows the number of commits.
If an email address is not configured on the forge's account profile, tries
to extract it from commits.
Currently supports only github. :-/

Copyright 2024 Federico Ceratto <federico@debian.org>
Released under GPLv3, see /usr/share/common-licenses/GPL-3
---
"""
# Linted with Black

from typing import Tuple, Any, List
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime
from urllib.parse import urlparse
import os
import sys
import http.client
import json


def parse_args() -> Tuple[Any, str, str]:
    ap = ArgumentParser(usage=__doc__)
    ap.add_argument("url", help="Project URL")
    ap.add_argument("--github-token-fn", default="~/.github_token")
    ap.add_argument(
        "-t", help="Truncate authors list. Default: 10", default=10, type=int
    )
    args = ap.parse_args()
    u = urlparse(args.url.rstrip("/"))
    if u.netloc != "github.com":
        print("Only github is supported at the moment, sorry :(")
        sys.exit(1)
    try:
        _, ownername, reponame = u.path.split("/")[:3]
        if not (ownername and reponame):
            raise Exception()
    except Exception:
        print("Unable to extract owner and repo name from URL")
        sys.exit(1)

    return args, ownername, reponame


def fetch_author_details(
    conn, headers: dict, nickname: str, ownername: str, reponame: str
) -> Tuple[str, str]:
    path = f"/users/{nickname}"
    conn.request("GET", path, "", headers)
    data = conn.getresponse().read()
    j = json.loads(data.decode())
    name = j["name"]
    email = j["email"]

    if email:
        return name, email

    path = f"/repos/{ownername}/{reponame}/commits?author={nickname}&per_page=1"
    conn.request("GET", path, "", headers)
    data = conn.getresponse().read().decode()
    j = json.loads(data)
    try:
        email = j[0]["commit"]["author"]["email"]
    except Exception:
        email = ""
    if not email:
        email = "???"
    return name, email


def load_token(args) -> str:
    token = os.getenv("GITHUB_TOKEN") or ""
    if not token:
        token = Path(args.github_token_fn).expanduser().read_text().strip()

    if not token:
        print("Token not found. Use GITHUB_TOKEN env var or --github-token-fn")
        sys.exit(1)

    return token


def fetch_authors(conn, headers: dict, ownername: str, reponame: str) -> List[Tuple]:
    path = f"/repos/{ownername}/{reponame}/stats/contributors"
    conn.request("GET", path, "", headers)
    resp = conn.getresponse()
    j = json.loads(resp.read().decode())

    li = []
    for a in j:
        author_login = a["author"]["login"]
        if '[bot]' in author_login:
            continue

        first = datetime(9999, 1, 1)
        last = datetime(1970, 1, 1)
        commit_cnt = 0
        for wb in a["weeks"]:
            if wb["c"] == 0:
                continue  # zero commits this week

            commit_cnt += wb["c"]
            ts = datetime.utcfromtimestamp(wb["w"])
            if ts > last:
                last = ts
            if ts < first:
                first = ts

        li.append((commit_cnt, author_login, first, last))

    li.sort(reverse=True)
    return li


def main() -> None:
    args, ownername, reponame = parse_args()
    token = load_token(args)
    conn = http.client.HTTPSConnection("api.github.com")
    headers = {
        "Authorization": f"bearer {token}",
        "User-Agent": "Debian-Contributors-Fetcher",
        "Content-Type": "application/json",
    }
    authors = fetch_authors(conn, headers, ownername, reponame)

    for cnt, au, start, end in authors[: args.t]:
        full_name, email = fetch_author_details(conn, headers, au, ownername, reponame)
        a = f"{start.year}-{end.year} {full_name} <{email}>"
        print(f"{a:<70} {cnt:>7} {au}")
    if len(authors) > args.t:
        print(f"The listing above was trimmed: {len(authors)} authors in total")


if __name__ == "__main__":
    main()
