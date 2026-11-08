"""The sign-in `next` destination: which same-site addresses a sign-in may
send the browser back to.

An open redirect is the risk, so the check is positive and strict: the path
must be byte-identical to one of the navigation tabs' routes, and the query
(if any) may hold only unreserved characters, the separators of a plain query
string and percent-escapes. A scheme, a host, a second slash, a backslash, a
fragment, a control character or anything else makes the whole value
unusable (`None`), and the caller falls back to the plain sign-in.
"""

import re

MAX_NEXT_LENGTH = 200
_QUERY_PATTERN = re.compile(r"(?:[A-Za-z0-9_.~=&,:+-]|%[0-9A-Fa-f]{2})*")


def validated_next_route(candidate, allowed_paths):
    """`candidate` when it is an allowed path, optionally followed by a safe
    query string, else None. `allowed_paths` is the set of exact routes."""
    if not isinstance(candidate, str) or len(candidate) > MAX_NEXT_LENGTH:
        return None
    path, separator, query = candidate.partition("?")
    if path not in allowed_paths:
        return None
    if separator and not _QUERY_PATTERN.fullmatch(query):
        return None
    return candidate
