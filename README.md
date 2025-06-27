# Ping Bot

A simple Python bot that monitors the status of a webpage every 2 minutes and logs any changes. Now with a web dashboard for easy configuration!

## Features

- Monitors a specific URL every 2 minutes
- Logs HTTP status codes and timestamps
- Detects and logs changes in status codes
- Runs continuously in a loop
- Logs to both console and file (`ping_bot.log`)
- Handles network errors gracefully
- **NEW**: Web dashboard for easy configuration
- **NEW**: Real-time log viewing
- **NEW**: Start/stop bot from web interface

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Web Dashboard (Recommended)

1. Start the dashboard:
```bash
python dashboard.py
```

2. Open your browser to: `http://localhost:5000`

3. Configure your settings:
   - Enter the target URL
   - Set the check interval
   - Enable/disable the bot
   - View real-time logs

### Option 2: Command Line

1. Edit the `TARGET_URL` in `ping_bot.py` to set your desired URL:
```python
TARGET_URL = "https://your-website.com"  # Change this to your target URL
```

2. Run the bot:
```bash
python ping_bot.py
```

3. The bot will start monitoring and logging to both console and `ping_bot.log` file.

4. To stop the bot, press `Ctrl+C`.

## Dashboard Features

The web dashboard provides:

- **Real-time Status**: See if the bot is running or stopped
- **Easy Configuration**: Change URL and interval without editing code
- **Live Logs**: View recent monitoring logs with color coding
- **Start/Stop Control**: Enable or disable monitoring with a checkbox
- **Responsive Design**: Works on desktop and mobile devices

## Configuration

### Via Dashboard
- Access the web interface at `http://localhost:5000`
- Modify settings through the form
- Click "Update Configuration" to apply changes

### Via Code
You can modify these settings in the `main()` function of `ping_bot.py`:

- `TARGET_URL`: The URL to monitor
- `CHECK_INTERVAL`: Check interval in seconds (default: 120 = 2 minutes)

## Log Output

The bot logs:
- Initial status check
- Status changes (with warning level)
- Unchanged status (info level)
- Network errors
- Next check countdown

## Example Output

```
2024-01-15 10:30:00,123 - INFO - Starting ping bot for https://example.com
2024-01-15 10:30:00,124 - INFO - Check interval: 120 seconds
2024-01-15 10:30:01,456 - INFO - Initial status check: 200
2024-01-15 10:30:01,457 - INFO - Next check in 120 seconds...
2024-01-15 10:32:01,789 - INFO - Status unchanged: 200
2024-01-15 10:32:01,790 - INFO - Next check in 120 seconds...
2024-01-15 10:34:02,123 - WARNING - Status changed from 200 to 503
2024-01-15 10:34:02,124 - INFO - Next check in 120 seconds...
```

## Files

- `ping_bot.py` - Core monitoring bot
- `dashboard.py` - Web dashboard server
- `templates/dashboard.html` - Dashboard web interface
- `requirements.txt` - Python dependencies
- `bot_config.json` - Configuration file (created automatically)
- `ping_bot.log` - Log file (created automatically)

## Requirements

- Python 3.6+
- requests library
- flask library (for dashboard)

## Security Note

The dashboard runs on `0.0.0.0:5000` by default, making it accessible from other devices on your network. For production use, consider:
- Adding authentication
- Using HTTPS
- Restricting access to localhost only 