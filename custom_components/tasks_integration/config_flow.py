"""Config flow for Tasks Integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import CONF_API_URL, CONF_TOKEN, CONF_WS_URL, CONF_SELECTED_PROJECTS, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_URL): str,
        vol.Required(CONF_WS_URL): str,
        vol.Required(CONF_TOKEN): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{data[CONF_API_URL]}/api/data?token={data[CONF_TOKEN]}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 401:
                    raise InvalidAuth
                if response.status != 200:
                    raise CannotConnect
                
                result = await response.json()
                projects = result.get("projects", [])
                
                return {"title": "Tasks", "projects": projects}
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Tasks API: %s", err)
            raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tasks Integration."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}
        self._projects = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(user_input[CONF_TOKEN])
            self._abort_if_unique_id_configured()
            
            self._data = user_input
            self._projects = info["projects"]
            
            # Move to project selection step
            return await self.async_step_select_projects()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_select_projects(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle project selection step."""
        # Build project options with hierarchy
        project_options = {}
        
        def build_hierarchy(projects, parent_id=None, indent=0):
            """Recursively build hierarchical project list."""
            filtered = [p for p in projects if p.get("parentId") == parent_id and not p.get("deletedAt")]
            for project in sorted(filtered, key=lambda x: x.get("name", "")):
                prefix = "  " * indent
                project_options[project["id"]] = f"{prefix}{project['name']}"
                build_hierarchy(projects, project["id"], indent + 1)
        
        build_hierarchy(self._projects)
        
        if user_input is None:
            return self.async_show_form(
                step_id="select_projects",
                data_schema=vol.Schema({
                    vol.Required(CONF_SELECTED_PROJECTS): cv.multi_select(project_options)
                }),
            )
        
        # Combine all data and create entry
        self._data[CONF_SELECTED_PROJECTS] = user_input[CONF_SELECTED_PROJECTS]
        
        return self.async_create_entry(
            title="Tasks",
            data=self._data,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
