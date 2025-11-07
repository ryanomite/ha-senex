"""DataUpdateCoordinator for Tasks Integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
import websockets

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API_URL, CONF_TOKEN, CONF_WS_URL, CONF_SELECTED_PROJECTS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TasksCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Tasks data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api_url = entry.data[CONF_API_URL]
        self.ws_url = entry.data[CONF_WS_URL]
        self.token = entry.data[CONF_TOKEN]
        self.selected_projects = entry.data.get(CONF_SELECTED_PROJECTS, [])
        self._ws = None
        self._ws_task = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        
        # Start WebSocket connection
        self._ws_task = hass.loop.create_task(self._connect_websocket())

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.api_url}/api/data?token={self.token}&includeCompleted=true"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        raise UpdateFailed(f"Error fetching data: {response.status}")
                    
                    data = await response.json()
                    
                    # Filter tasks by selected projects
                    tasks = [
                        t for t in data.get("tasks", [])
                        if t.get("projectId") in self.selected_projects
                    ]
                    
                    return {
                        "tasks": tasks,
                        "projects": data.get("projects", []),
                        "tags": data.get("tags", []),
                        "users": data.get("users", []),
                    }
            except aiohttp.ClientError as err:
                raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _connect_websocket(self):
        """Maintain WebSocket connection for real-time updates."""
        while True:
            try:
                uri = f"{self.ws_url}?token={self.token}"
                async with websockets.connect(uri) as websocket:
                    _LOGGER.info("WebSocket connected to Tasks")
                    self._ws = websocket
                    
                    async for message in websocket:
                        _LOGGER.debug("WebSocket message received: %s", message)
                        # Trigger a refresh when data changes
                        await self.async_request_refresh()
                        
            except Exception as err:
                _LOGGER.error("WebSocket error: %s", err)
                self._ws = None
                await asyncio.sleep(5)  # Wait before reconnecting

    async def async_shutdown(self):
        """Shutdown coordinator."""
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
