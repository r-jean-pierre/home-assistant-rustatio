"""Config flow for Rustatio."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    RustatioApi,
    RustatioApiError,
    RustatioAuthError,
    RustatioConnectionError,
)
from .const import CONF_BASE_URL, CONF_TOKEN, DEFAULT_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RustatioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Rustatio configuration."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure a Rustatio server."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalize_input(user_input)
            self._async_abort_entries_match({CONF_BASE_URL: data[CONF_BASE_URL]})

            if (error := await self._async_validate(data)) is None:
                return self.async_create_entry(title="Rustatio", data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(DEFAULT_BASE_URL, ""),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Allow the Rustatio URL or token to be changed from the UI."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalize_input(user_input)

            if any(
                other.entry_id != entry.entry_id
                and other.data.get(CONF_BASE_URL) == data[CONF_BASE_URL]
                for other in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")

            if (error := await self._async_validate(data)) is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=data,
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(
                entry.data[CONF_BASE_URL],
                entry.data.get(CONF_TOKEN, ""),
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Start reauthentication after a rejected token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Request and validate a replacement Rustatio token."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_BASE_URL: entry.data[CONF_BASE_URL],
                CONF_TOKEN: user_input.get(CONF_TOKEN, "").strip(),
            }

            if (error := await self._async_validate(data)) is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_TOKEN: data[CONF_TOKEN]},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TOKEN,
                        default=entry.data.get(CONF_TOKEN, ""),
                    ): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

    async def _async_validate(self, data: dict[str, str]) -> str | None:
        """Validate access to the configured Rustatio API."""
        api = RustatioApi(
            async_get_clientsession(self.hass),
            data[CONF_BASE_URL],
            data[CONF_TOKEN] or None,
        )

        try:
            await api.async_get_instance_summaries()
            await api.async_get_watch_status()
        except RustatioAuthError:
            return "invalid_auth"
        except RustatioConnectionError:
            return "cannot_connect"
        except RustatioApiError:
            return "invalid_response"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error while validating the API")
            return "unknown"

        return None


def _normalize_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Normalize config flow input before storing it."""
    return {
        CONF_BASE_URL: user_input[CONF_BASE_URL].strip().rstrip("/"),
        CONF_TOKEN: user_input.get(CONF_TOKEN, "").strip(),
    }


def _schema(base_url: str, token: str) -> vol.Schema:
    """Build the common URL/token schema used by setup and reconfigure."""
    return vol.Schema(
        {
            vol.Required(
                CONF_BASE_URL,
                default=base_url,
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
            vol.Optional(
                CONF_TOKEN,
                default=token,
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        }
    )
