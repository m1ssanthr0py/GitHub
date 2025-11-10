# Simple C2 - Malformed Labs Command & Control

A lightweight, educational Command & Control (C2) framework built in Python for cybersecurity labs and research environments.

## 🚀 Quick Start

### 1. Clean Setup
```bash
# Full cleanup and restart of the entire infrastructure
./restart_c2.sh
```

### 2. Manual Setup
```bash
# Clean up existing services
./cleanup_c2.sh

# Start Docker lab environment
cd "../client lab setup"
docker-compose up -d

# Deploy C2 infrastructure
cd "../simple c2"
./deploy_c2.sh

# Use the console
python3 c2console.py localhost 8889
```

## 📁 Files Overview

### Core Components
- **`c2server_daemon.py`** - Main C2 server daemon with management interface
- **`c2client.py`** - C2 client agent for endpoints  
- **`c2console.py`** - Interactive console for managing operations

### Management Scripts
- **`restart_c2.sh`** - Complete infrastructure restart (recommended)
- **`cleanup_c2.sh`** - Stop all C2 services and clean up
- **`deploy_c2.sh`** - Deploy C2 clients to lab containers

## 🎮 Console Commands

Once connected to the console (`python3 c2console.py localhost 8889`):

| Command | Description | Example |
|---------|-------------|---------|
| `list` | Show connected clients | `list` |
| `send <id> <cmd>` | Execute command on specific client | `send abc123 whoami` |
| `broadcast <cmd>` | Execute command on all clients | `broadcast uptime` |
| `stats` | Show server statistics | `stats` |
| `help` | Display help message | `help` |
| `quit` | Exit console | `quit` |

## 🔧 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   C2 Console    │    │   C2 Server      │    │   C2 Clients    │
│   (Port 8889)   │◄──►│   (Port 8888)    │◄──►│  (Endpoints)    │
│                 │    │                  │    │                 │
│ • Interactive   │    │ • Client Management │ │ • Command Exec  │
│ • Command Send  │    │ • Authentication    │ │ • Heartbeats    │
│ • Status View   │    │ • Multi-threaded    │ │ • Auto-reconnect│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🌐 Network Configuration

- **C2 Server**: `192.168.210.13:8888` (Internal Docker network)
- **Management**: `localhost:8889` (Exposed to host)
- **Web Interface**: `localhost:8080` (Outrun dashboard)

### Docker Network Layout
```
192.168.210.0/24 (lab_network)
├── 192.168.210.10 - linux_endpoint1 (Alpine)
├── 192.168.210.11 - linux_endpoint2 (Ubuntu) 
├── 192.168.210.12 - linux_endpoint3 (CentOS)
└── 192.168.210.13 - outrun_webserver (C2 Server)
```

## 🔐 Security Features

- **Token Authentication**: Clients must authenticate with shared token
- **Encrypted Communication**: JSON message protocol with length prefixes
- **Client Isolation**: Each client operates in separate thread
- **Heartbeat Monitoring**: Automatic connection health checks

## 📊 Monitoring

### Check Status
```bash
# View server logs
docker exec outrun_webserver cat /tmp/c2server_daemon.log

# Check client logs
docker exec linux_endpoint1 cat /tmp/c2client.log
docker exec linux_endpoint2 cat /tmp/c2client.log

# Network status
docker exec outrun_webserver netstat -tlnp | grep -E "888[89]"
```

### Web Dashboard
Visit `http://localhost:8080` for the Outrun-themed network monitoring dashboard.

## 🛡️ Lab Environment

This C2 framework is designed for:
- **Cybersecurity Education**: Learn C2 concepts safely
- **Red Team Training**: Practice attack scenarios
- **Blue Team Defense**: Understand C2 communications
- **Research & Development**: Test detection mechanisms

### Supported Platforms
- ✅ Alpine Linux (linux_endpoint1)
- ✅ Ubuntu Latest (linux_endpoint2)  
- ✅ CentOS 7 (linux_endpoint3)
- ✅ Python 3.6+ required

## 🚨 Legal Notice

**FOR EDUCATIONAL AND AUTHORIZED TESTING ONLY**

This software is intended solely for:
- Educational purposes in controlled environments
- Authorized penetration testing with explicit permission
- Cybersecurity research in isolated lab networks

**Unauthorized use of this software is strictly prohibited and may violate applicable laws.**

## 🔧 Troubleshooting

### Common Issues

**Console won't connect:**
```bash
# Check if ports are exposed
docker ps | grep outrun_webserver
# Should show: 0.0.0.0:8889->8889/tcp
```

**No clients connecting:**
```bash
# Check authentication token match
grep "auth_token" c2client.py c2server_daemon.py
# Both should show: malformed_labs_c2_2024
```

**Server won't start:**
```bash
# Clean restart everything
./restart_c2.sh
```

### Debug Mode
```bash
# Run daemon interactively to see output
docker exec -it outrun_webserver python3 /tmp/c2server_daemon.py
```

## 📈 Example Session

```bash
$ ./restart_c2.sh
🎉 SUCCESS! C2 infrastructure is fully operational!

$ python3 c2console.py localhost 8889
✅ Connected to C2 Management Server at localhost:8889

🔥 C2> stats
📊 Server Statistics:
🔄 Status: running
👥 Connected clients: 2
⏰ Uptime: 0h 2m 15s
📨 Total commands sent: 0

🔥 C2> list
📡 Connected Clients (2):
🤖 ID: abc12345
   📍 Address: 192.168.210.10:45678
   💻 Host: endpoint1 (Alpine Linux)
   👤 User: root

🤖 ID: def67890  
   📍 Address: 192.168.210.11:54321
   💻 Host: endpoint2 (Ubuntu)
   👤 User: root

🔥 C2> broadcast whoami
📢 Command broadcast to 2 clients: whoami

🔥 C2> quit
👋 Goodbye!
```

---

**Malformed Labs - Cybersecurity Education & Research**