"""Minimal You.com Search API adapter for evidence retrieval."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class YouSearchError(Exception):
    """Raised when You.com cannot provide usable evidence."""


@dataclass(frozen=True)
class Evidence:
    title: str
    url: str
    text: str


class YouSearchClient:
    endpoint = "https://ydc-index.io/v1/search"

    def __init__(self, api_key: str | None = None, timeout_seconds: int = 30):
        self.api_key = api_key or os.getenv("YOUCOM_API_KEY") or os.getenv("YDC_API_KEY")
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, count: int = 8) -> list[Evidence]:
        if not self.api_key:
            raise YouSearchError("You.com API credentials are not configured.")
        body = json.dumps({"query": query, "count": count}).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as error:
            raise YouSearchError("You.com search request failed.") from error
        except json.JSONDecodeError as error:
            raise YouSearchError("You.com returned invalid JSON.") from error

        web_results = payload.get("results", {}).get("web", [])
        evidence = []
        for result in web_results:
            url = result.get("url")
            title = result.get("title")
            snippets = result.get("snippets") or []
            text = result.get("description") or (snippets[0] if snippets else "")
            if isinstance(url, str) and url.startswith(("http://", "https://")) and title and text:
                evidence.append(Evidence(title=str(title), url=url, text=str(text)))
        if not evidence:
            raise YouSearchError("You.com returned no usable web evidence.")
        return evidence
