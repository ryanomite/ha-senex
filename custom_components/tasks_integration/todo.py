"""To-Do list platform for Tasks Integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_API_URL, CONF_TOKEN, CONF_SELECTED_PROJECTS, DOMAIN
from .coordinator import TasksCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tasks To-Do platform."""
    coordinator: TasksCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Create a To-Do list entity for each selected project
    entities = []
    for project_id in coordinator.selected_projects:
        # Find project in data
        project = next(
            (p for p in coordinator.data.get("projects", []) if p["id"] == project_id),
            None
        )
        if project:
            entities.append(TasksTodoListEntity(coordinator, project, entry))
    
    async_add_entities(entities)


class TasksTodoListEntity(CoordinatorEntity, TodoListEntity):
    """A To-Do List entity for a Tasks project."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: TasksCoordinator,
        project: dict[str, Any],
        entry: ConfigEntry,
    ) -> None:
        """Initialize the To-Do list."""
        super().__init__(coordinator)
        
        self.project_id = project["id"]
        self.project_name = project["name"]
        self.api_url = coordinator.api_url
        self.token = coordinator.token
        
        self._attr_unique_id = f"{entry.entry_id}_{self.project_id}"
        self._attr_name = self.project_name

    @property
    def todo_items(self) -> list[TodoItem]:
        """Get the current set of To-Do items."""
        tasks = [
            t for t in self.coordinator.data.get("tasks", [])
            if t.get("projectId") == self.project_id and not t.get("deletedAt")
        ]
        
        items = []
        for task in tasks:
            status = TodoItemStatus.COMPLETED if task.get("completedAt") else TodoItemStatus.NEEDS_ACTION
            
            item = TodoItem(
                uid=task["id"],
                summary=task["title"],
                status=status,
                due=task.get("dueDate"),
                description=task.get("description"),
            )
            items.append(item)
        
        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a To-Do item."""
        # Extract HA user's first name from context
        context = self.hass.context
        user = None
        user_name = None
        
        if context.user_id:
            user = await self.hass.auth.async_get_user(context.user_id)
            if user and user.name:
                # Extract first name
                user_name = user.name.split()[0] if user.name else None
        
        # Find or create tag for this user
        tag_id = None
        if user_name:
            tag_id = await self._get_or_create_user_tag(user_name)
        
        # Create task via API
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api/tasks?token={self.token}"
            data = {
                "title": item.summary,
                "description": item.description or "",
                "dueDate": item.due.isoformat() if item.due else None,
                "priority": 4,  # Default priority
                "projectId": self.project_id,
                "tagIds": [tag_id] if tag_id else [],
                "source": "api",
            }
            
            async with session.post(url, json=data) as response:
                if response.status != 201:
                    _LOGGER.error("Failed to create task: %s", await response.text())
                    raise Exception("Failed to create task")

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a To-Do item."""
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api/tasks/{item.uid}?token={self.token}"
            
            data = {
                "title": item.summary,
                "description": item.description,
                "dueDate": item.due.isoformat() if item.due else None,
            }
            
            # Handle completion status
            if item.status == TodoItemStatus.COMPLETED:
                # Find if task is already completed
                task = next(
                    (t for t in self.coordinator.data.get("tasks", []) if t["id"] == item.uid),
                    None
                )
                if task and not task.get("completedAt"):
                    # Complete the task
                    complete_url = f"{self.api_url}/api/tasks/{item.uid}/complete?token={self.token}"
                    async with session.post(complete_url) as response:
                        if response.status != 200:
                            _LOGGER.error("Failed to complete task: %s", await response.text())
            else:
                # Uncomplete the task if it was completed
                task = next(
                    (t for t in self.coordinator.data.get("tasks", []) if t["id"] == item.uid),
                    None
                )
                if task and task.get("completedAt"):
                    uncomplete_url = f"{self.api_url}/api/tasks/{item.uid}/uncomplete?token={self.token}"
                    async with session.post(uncomplete_url) as response:
                        if response.status != 200:
                            _LOGGER.error("Failed to uncomplete task: %s", await response.text())
            
            # Update other fields
            async with session.put(url, json=data) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update task: %s", await response.text())
                    raise Exception("Failed to update task")

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete To-Do items."""
        async with aiohttp.ClientSession() as session:
            for uid in uids:
                # Soft delete by setting deletedAt
                url = f"{self.api_url}/api/tasks/{uid}?token={self.token}"
                data = {"deletedAt": "now"}  # Backend should handle this
                
                async with session.put(url, json=data) as response:
                    if response.status != 200:
                        _LOGGER.error("Failed to delete task %s: %s", uid, await response.text())

    async def async_move_todo_item(
        self, uid: str, previous_uid: str | None = None
    ) -> None:
        """Move a To-Do item (reorder)."""
        # Tasks app doesn't support explicit ordering, so this is a no-op
        pass

    async def _get_or_create_user_tag(self, user_name: str) -> str | None:
        """Get or create a tag for the HA user."""
        tags = self.coordinator.data.get("tags", [])
        
        # Look for existing tag
        existing_tag = next((t for t in tags if t["name"].lower() == user_name.lower()), None)
        if existing_tag:
            return existing_tag["id"]
        
        # Create new tag
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api/tags?token={self.token}"
            data = {
                "name": user_name,
                "color": "#4a7c59"  # Default color
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 201:
                    result = await response.json()
                    return result.get("id")
                else:
                    _LOGGER.error("Failed to create tag: %s", await response.text())
                    return None
