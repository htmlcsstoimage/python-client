"""Internal HTTP transport for HCTI API requests."""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from typing import Any

import httpx

from ._version import __version__

_USER_AGENT = f"HCTIPython/{re.sub(r'[^A-Za-z0-9._+-]', '-', __version__)}"


class HttpTransport:
    """Send authenticated requests through an owned or injected HTTPX client."""

    def __init__(
        self,
        api_id: str,
        api_key: str,
        *,
        http_client: httpx.Client | None,
        base_url: str,
    ) -> None:
        self._base_url = base_url
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(timeout=30.0)
        credentials = base64.b64encode(f"{api_id}:{api_key}".encode()).decode()
        self._auth_header = f"Basic {credentials}"

    def post(self, path: str, payload: Mapping[str, Any]) -> httpx.Response:
        """Send a JSON POST request."""

        return self._http_client.post(
            f"{self._base_url}{path}",
            headers={
                "Authorization": self._auth_header,
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
            json=payload,
        )

    def delete(
        self,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        """Send a DELETE request with an optional JSON body."""

        headers = {
            "Authorization": self._auth_header,
            "User-Agent": _USER_AGENT,
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        return self._http_client.request(
            "DELETE",
            f"{self._base_url}{path}",
            headers=headers,
            json=payload,
        )

    def close(self) -> None:
        """Close only an HTTPX client created by this transport."""

        if self._owns_http_client:
            self._http_client.close()
