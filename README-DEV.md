# Development Guide for KiCad MCP Python

This guide covers development workflows and tools for the KiCad MCP Python project.

## Hot Reload Development Server

For development, you can use the hot reload server that automatically restarts when you make code changes.

### Quick Start

```bash
# Install development dependencies (including watchdog)
poetry install

# Run the development server with hot reload
poetry run python dev_server.py
```

### Features

- **Automatic Restart**: Server restarts automatically when Python files change
- **Debounced Changes**: Multiple rapid changes are debounced to avoid excessive restarts
- **Smart Filtering**: Only monitors relevant Python files, ignores cache and build directories
- **Server Output**: Real-time display of server logs with clear prefixes
- **Graceful Shutdown**: Proper cleanup when stopping the development server

### Usage Options

```bash
# Basic usage (default: main.py)
poetry run python dev_server.py

# Specify a different server script
poetry run python dev_server.py --script my_server.py

# Enable verbose logging
poetry run python dev_server.py --verbose

# Help
poetry run python dev_server.py --help
```

### What Gets Monitored

The file watcher monitors:
- ✅ All `.py` files in the project
- ✅ New files and moved files
- ✅ Nested directories

The file watcher ignores:
- ❌ `__pycache__` directories
- ❌ `.pytest_cache` directories  
- ❌ `.git` directories
- ❌ `build/` and `dist/` directories
- ❌ Virtual environment directories
- ❌ Screenshot output directories
- ❌ Temporary files
- ❌ Non-Python files

### Development Workflow

1. **Start Development Server**:
   ```bash
   poetry run python dev_server.py
   ```

2. **Make Code Changes**: Edit any Python file in the project

3. **Automatic Restart**: The server detects changes and restarts automatically

4. **Test Changes**: The new server instance includes your changes

5. **Stop Server**: Press `Ctrl+C` to stop both the file watcher and server

### Troubleshooting

#### Server Won't Start
- Ensure `main.py` exists or specify the correct script with `--script`
- Check that all dependencies are installed: `poetry install`
- Verify KiCad IPC server is running (Tools → External Plugin → Start Server)

#### Too Many Restarts
- The system includes debouncing (1-second delay) to prevent excessive restarts
- If you're experiencing issues, try increasing the debounce delay in `dev_server.py`

#### Changes Not Detected
- Ensure you're editing files within the project directory
- Check that the files have `.py` extensions
- Verify the files aren't in ignored directories (see list above)

#### Server Process Issues
- The development server monitors the child process and will restart it if it crashes
- If you need to debug the actual server process, you can still run `poetry run python main.py` directly

## Production vs Development

- **Development**: Use `dev_server.py` for active development with hot reload
- **Production/Testing**: Use `main.py` directly for stable operation without file watching

## Environment Setup

Make sure you have your environment properly configured:

```bash
# Example .env file
KICAD_CLI_PATH=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
PCB_PATHS=/path/to/your/project1.kicad_pcb,/path/to/your/project2.kicad_pcb
```

## Advanced Configuration

### Custom Debounce Delay

Edit `dev_server.py` and modify the `CodeChangeHandler` initialization:

```python
event_handler = CodeChangeHandler(
    restart_callback=self.restart_server,
    debounce_delay=2.0  # Increase to 2 seconds
)
```

### Additional File Types

To monitor additional file types, modify the `should_restart_for_file` method:

```python
def should_restart_for_file(self, file_path: str) -> bool:
    # Monitor Python files and config files
    return file_path.endswith(('.py', '.toml', '.env'))
```

### Custom Ignore Patterns

Add more ignore patterns in the `should_restart_for_file` method:

```python
ignore_patterns = [
    '__pycache__',
    '.pytest_cache',
    # Add your custom patterns here
    'my_custom_dir/',
    'temp_files/'
]
```

## Integration with IDEs

### VS Code
- The development server works well with VS Code
- Use the integrated terminal to run the development server
- VS Code's file changes will trigger automatic restarts

### PyCharm
- Run the development server in PyCharm's terminal
- Configure run configurations if needed for easier access

### Command Line
- The development server is designed to work well from the command line
- All output is clearly labeled and easy to follow

## Logging

The development server provides comprehensive logging:

```
2024-01-20 10:30:15 - dev_server - INFO - Starting MCP server: /path/to/main.py
2024-01-20 10:30:15 - dev_server - INFO - Server started with PID: 12345
2024-01-20 10:30:15 - dev_server - INFO - [SERVER] KiCad MCP Server created and configured successfully
2024-01-20 10:30:20 - dev_server - INFO - Code change detected: /path/to/file.py
2024-01-20 10:30:21 - dev_server - INFO - Triggering server restart due to code changes...
```

Use `--verbose` flag for even more detailed logging during debugging.
