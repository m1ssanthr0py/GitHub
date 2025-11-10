# OUTRUN Themed Web Server

A cyberpunk/synthwave-styled web interface for the lab environment with the classic Outrun aesthetic.

## Color Palette

| Color           | Hex       | Description                 |
| :-------------- | :-------- | :-------------------------- |
| Neon Cyan       | `#00FFFF` | Gridlines and reflections   |
| Electric Indigo | `#6600FF` | Core glow                   |
| Laser Pink      | `#FF0099` | Accent for UI or highlights |
| Cosmic Purple   | `#2E003E` | Background depth            |
| Jet Black       | `#050505` | Base neutral tone           |

## Features

- **Outrun-themed UI** with neon colors, grid overlays, and animated effects
- **System Information Display** showing hostname, uptime, and system stats
- **Network Connectivity Testing** to ping other endpoints in the lab
- **Interactive Terminal** with safe command execution
- **Real-time Updates** with auto-refresh every 30 seconds
- **Responsive Design** that works on desktop and mobile
- **Cyberpunk Effects** including scanner lines and matrix-style background

## Running the Web Server

### With Docker Compose (Recommended)

The web server is already integrated into the docker-compose.yaml file:

```bash
cd "/Users/maladmin/Documents/GitHub/outrunc2/client lab setup"
docker-compose up -d
```

The web server will be available at:
- **http://localhost:8080** (from host machine)
- **http://192.168.210.13:8080** (from within the lab network)

### Standalone Docker

```bash
cd /Users/maladmin/Documents/GitHub/outrunc2/webserver
docker build -t outrun-webserver .
docker run -p 8080:8080 outrun-webserver
```

### Local Development

```bash
cd /Users/maladmin/Documents/GitHub/outrunc2/webserver
pip install -r requirements.txt
python app.py
```

## API Endpoints

- `GET /` - Main dashboard
- `GET /terminal` - Full terminal interface
- `GET /api/system` - System information (JSON)
- `GET /api/network` - Network connectivity status (JSON)
- `POST /api/execute` - Execute safe commands (JSON)
- `GET /health` - Health check endpoint

## Network Configuration

The web server is configured to run on the lab network:
- **Container Name**: `outrun_webserver`
- **IP Address**: `192.168.210.13`
- **Hostname**: `outrun-server`
- **Port**: `8080`

## Available Commands

The terminal interface supports these safe commands:
- `whoami` - Show current user
- `pwd` - Print working directory
- `ls` - List directory contents
- `date` - Show current date/time
- `uptime` - Show system uptime
- `ip addr` - Show network interfaces
- `ps` - Show running processes
- `df` - Show disk usage
- `free` - Show memory usage

## Security Notes

- Only whitelisted commands can be executed
- All commands have timeouts to prevent hanging
- No shell access or dangerous commands allowed
- Running in isolated Docker container

## Troubleshooting

### Container won't start
```bash
# Check container logs
docker logs outrun_webserver

# Rebuild if needed
docker-compose build webserver
```

### Can't access from browser
1. Check if port 8080 is exposed: `docker ps`
2. Verify container is running: `docker-compose ps`
3. Check health status: `curl http://localhost:8080/health`

### Network connectivity issues
- Ensure all containers are on the same network
- Check IP addresses with `docker network inspect clientlabsetup_lab_network`

## Customization

### Adding New Commands
Edit `app.py` and add to the `safe_commands` dictionary:

```python
safe_commands = {
    'your_command': ['command', 'args'],
    # ...
}
```

### Styling Changes
Modify `/static/css/outrun.css` to adjust colors, animations, or layout.

### Additional Pages
Create new templates in `/templates/` and add routes in `app.py`.

## File Structure

```
webserver/
├── Dockerfile
├── requirements.txt
├── app.py                 # Main Flask application
├── templates/
│   ├── index.html         # Dashboard page
│   └── terminal.html      # Terminal page
└── static/
    ├── css/
    │   └── outrun.css     # Outrun theme styles
    └── js/
        └── outrun.js      # Interactive functionality
```

Enjoy your retro-futuristic lab interface! 🌆🏎️💜