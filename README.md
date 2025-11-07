# Tasks Integration for Home Assistant

This custom integration connects your Home Assistant instance to your Tasks application, syncing selected projects as To-Do list entities.

**Repository:** `https://github.com/YOUR_USERNAME/tasks-ha-integration`

## Features

- **Bidirectional Sync**: Tasks created in Home Assistant appear in Tasks, and vice versa
- **Real-time Updates**: Uses WebSocket connection for instant synchronization
- **Project Selection**: Choose which projects to sync during setup
- **User Tagging**: Tasks created in HA are automatically tagged with the creating user's first name
- **Full CRUD Support**: Create, read, update, and delete tasks from Home Assistant

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/YOUR_USERNAME/tasks-ha-integration`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Tasks Integration" in the integration list
9. Click "Install"
10. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/tasks_integration` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Configuration > Integrations
2. Click the "+ ADD INTEGRATION" button
3. Search for "Tasks Integration"
4. Enter your configuration:
   - **API URL**: The base URL of your Tasks API (e.g., `https://tasks-api.terraandryan.com`)
   - **WebSocket URL**: The WebSocket URL (e.g., `wss://tasks-api.terraandryan.com`)
   - **API Token**: Your authentication token from the Tasks app (found in Settings > API Token)
5. Select which projects you want to sync as To-Do lists
6. Click "Submit"

## Usage

Each selected project will appear as a To-Do list entity in Home Assistant with the name of the project.

### Creating Tasks

Tasks created in Home Assistant will:
- Be assigned to the selected project
- Have source set to "api"
- Be tagged with the Home Assistant user's first name
- Sync immediately to the Tasks application

### Completing Tasks

- Mark tasks as complete/incomplete in Home Assistant
- Changes sync immediately via WebSocket

### Deleting Tasks

- Deleting a task in Home Assistant soft-deletes it in Tasks
- Deleted tasks in Tasks are removed from Home Assistant

### Task Properties

The integration syncs:
- Title/Summary
- Description
- Due Date
- Completion Status

## Troubleshooting

### Connection Issues

- Verify your API URL and WebSocket URL are correct
- Ensure your API token is valid (check in Tasks Settings)
- Check that your Home Assistant instance can reach the Tasks API

### Tasks Not Syncing

- Check the Home Assistant logs for errors
- Verify the WebSocket connection is established
- Try reloading the integration

### Debug Logging

Add this to your `configuration.yaml` to enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.tasks_integration: debug
```

## Support

For issues, feature requests, or questions, please open an issue on GitHub.

## License

MIT License
