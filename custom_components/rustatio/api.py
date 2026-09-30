"""Small asynchronous client for the Rustatio HTTP API."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout


class RustatioError(Exception):
    """Base exception for Rustatio API errors."""


class RustatioConnectionError(RustatioError):
    """Raised when Rustatio cannot be reached."""


class RustatioAuthError(RustatioError):
    """Raised when Rustatio rejects the configured token."""


class RustatioApiError(RustatioError):
    """Raised when Rustatio returns an unexpected API response."""


class RustatioApi:
    """Minimal client for the Rustatio endpoints used by Home Assistant."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        token: str | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token or None

    async def async_get_instance_summaries(self) -> list[dict[str, Any]]:
        """Return the compact summary of all Rustatio instances."""
        data = await self._async_get_data("/api/instances/summary")
        if not isinstance(data, list) or not all(
            isinstance(item, dict) for item in data
        ):
            raise RustatioApiError("Instance summary has an unexpected format")
        return data

    async def async_get_watch_status(self) -> dict[str, Any]:
        """Return the Rustatio watch-folder status."""
        data = await self._async_get_data("/api/watch/status")
        if not isinstance(data, dict):
            raise RustatioApiError("Watch status is not an object")
        return data

    async def _async_get_data(self, path: str) -> Any:
        """Fetch a Rustatio ApiSuccess response and return its data field."""
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with self._session.get(
                f"{self._base_url}{path}",
                headers=headers,
                timeout=ClientTimeout(total=10),
            ) as response:
                if response.status in (401, 403):
                    raise RustatioAuthError("Rustatio rejected the API token")

                response.raise_for_status()
                try:
                    payload = await response.json(content_type=None)
                except (TypeError, ValueError) as err:
                    raise RustatioApiError(
                        "Rustatio returned invalid JSON"
                    ) from err

        except RustatioAuthError:
            raise
        except ClientResponseError as err:
            raise RustatioApiError(
                f"Rustatio returned HTTP {err.status}"
            ) from err
        except (ClientError, TimeoutError) as err:
            raise RustatioConnectionError(
                "Could not connect to Rustatio"
            ) from err

        if not isinstance(payload, dict):
            raise RustatioApiError("Rustatio returned invalid JSON")

        if payload.get("success") is not True or "data" not in payload:
            raise RustatioApiError("Unexpected Rustatio API response")

        return payload["data"]
