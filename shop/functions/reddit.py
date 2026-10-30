"""Helper for fetching posts from a subreddit's public JSON feed."""

import re

import requests

REDDIT_BASE_URL = "https://www.reddit.com"
USER_AGENT = "DjangoEcommerceApp/1.0"  # Reddit requires a User-Agent
TIMEOUT_SECONDS = 10


class RedditFetchError(Exception):
    """Raised when posts could not be fetched from Reddit."""


def build_url(subreddit):
    """Build the JSON feed URL, refusing anything that is not a plain name."""
    if not re.fullmatch(r"[A-Za-z0-9_]{2,21}", subreddit):
        raise RedditFetchError("That is not a valid subreddit name.")
    return f"{REDDIT_BASE_URL}/r/{subreddit}/.json"


def _safe_link(link):
    """Only allow http(s) links, so a feed can never inject other schemes."""
    if link.startswith(("https://", "http://")):
        return link
    return ""


def get_reddit_posts(subreddit="python", limit=10):
    """Return a list of posts, each with a title, author and url.

    Raises RedditFetchError (with a message fit to show a user) when the
    posts cannot be fetched or read.
    """
    url = build_url(subreddit)
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(
            url,
            headers=headers,
            params={"limit": limit},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RedditFetchError(
            "Could not reach Reddit. Please try again later."
        ) from exc

    if response.status_code == 403:
        raise RedditFetchError(
            "Reddit refused the request (HTTP 403). Reddit currently blocks "
            "many unauthenticated requests to its public feeds."
        )
    if response.status_code == 429:
        raise RedditFetchError(
            "Reddit says too many requests were made (HTTP 429). "
            "Please wait a minute and try again."
        )
    if response.status_code != 200:
        raise RedditFetchError(
            f"Reddit returned an error (HTTP {response.status_code})."
        )

    try:
        children = response.json()["data"]["children"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RedditFetchError(
            "Reddit sent a response that could not be read."
        ) from exc

    posts = []
    for item in children:
        post = item.get("data", {}) if isinstance(item, dict) else {}
        permalink = post.get("permalink", "")
        link = f"{REDDIT_BASE_URL}{permalink}" if permalink else ""
        posts.append(
            {
                "title": post.get("title", "(untitled)"),
                "author": post.get("author", "unknown"),
                "url": _safe_link(link or post.get("url", "")),
            }
        )
    return posts
