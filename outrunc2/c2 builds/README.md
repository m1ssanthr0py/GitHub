# Malformed Labs C2 System

A basic Command and Control (C2) system for lab environments with secure client-server communication.

## Overview

This C2 system consists of:
- **C2 Server** (`c2server.py`) - Central command and control server
- **C2 Client** (`c2client.py`) - Agent that runs on target systems
- **Deployment Script** (`deploy_c2.sh`) - Automated deployment to Docker containers

## Features

### Server Features
- **Multi-client support** with unique client IDs
- **Interactive console** for command management
- **Authentication** with token-based security
- **Real-time communication** with JSON message protocol
- **Client information tracking** (hostname, OS, architecture, etc.)
- **Command execution logging**
- **Heartbeat monitoring** for client status

### Client Features
- **Automatic reconnection** handling
- **System information reporting**
- **Command execution** with safety filters
- **Timeout protection** (30-second command limit)
- **Cross-platform support** (Linux, Windows, macOS)
- **Periodic heartbeat** to maintain connection

### Security Features
- **Token-based authentication**
- **Command filtering** to block dangerous operations
- **Execution timeouts** to prevent hanging processes
- **Logging** of all activities

## Quick Start

### 1. Start the C2 Server

```bash
cd "/Users/maladmin/Documents/GitHub/outrunc2/c2 builds"
python3 c2server.py
```

The server will start on `0.0.0.0:8888` and display an interactive console.

### 2. Deploy Clients to Lab Containers

```bash
./deploy_c2.sh
```

This will automatically deploy the C2 client to all lab containers (`linux_endpoint1`, `linux_endpoint2`, `linux_endpoint3`).

### 3. Manage Clients

Use the server console commands:

```
C2> list                           # List connected clients
C2> send <client_id> whoami        # Send command to specific client
C2> broadcast uptime               # Send command to all clients
C2> quit                           # Stop server
```

## Manual Client Installation

To manually run a client:

```bash
# Connect to default server (192.168.210.13:8888)
python3 c2client.py

# Connect to custom server
python3 c2client.py <server_ip> <server_port>
```

## Network Configuration

- **Server:** Runs on the web server container (`192.168.210.13:8888`)
- **Clients:** Connect from lab endpoints (`192.168.210.10-12`)
- **Protocol:** TCP with JSON message framing
- **Authentication:** Shared token (`malformed_labs_2025`)

## Command Examples

### Server Console Commands

```bash
# List all connected clients
C2> list

# Send commands to specific clients
C2> send a1b2c3d4 ls -la
C2> send a1b2c3d4 ps aux
C2> send a1b2c3d4 cat /etc/hostname

# Broadcast commands to all clients
C2> broadcast whoami
C2> broadcast uname -a
C2> broadcast df -h
```

### Available Client Commands

The clients can execute most standard Linux/Unix commands:
- `ls`, `ps`, `whoami`, `pwd`, `uname`
- `cat`, `head`, `tail`, `grep`
- `netstat`, `ss`, `ifconfig`, `ip`
- `uptime`, `df`, `free`, `top`

**Blocked commands** (for safety):
- `rm -rf`, `mkfs`, `dd if=`, `format`
- Fork bombs and other dangerous operations

## Log Files

- **Server logs:** `c2server.log` (in server directory)
- **Client logs:** `/tmp/c2client.log` (on each client container)

## Monitoring

### Check Client Status
```bash
# View client logs
docker exec linux_endpoint1 cat /tmp/c2client.log

# Check if client is running
docker exec linux_endpoint1 ps aux | grep c2client
```

### Stop Clients
```bash
# Stop client on specific container
docker exec linux_endpoint1 pkill -f c2client.py

# Stop all clients
for container in linux_endpoint1 linux_endpoint2 linux_endpoint3; do
    docker exec $container pkill -f c2client.py
done
```

## Integration with Web Dashboard

The C2 system is designed to work alongside the Outrun web dashboard:
- **Web Dashboard:** `http://localhost:8080` (monitoring and system info)
- **C2 Server:** `192.168.210.13:8888` (command and control)

## Security Considerations

⚠️ **This is a basic C2 for lab environments only!**

For production use, implement:
- **Strong encryption** (TLS/SSL)
- **Certificate-based authentication**
- **Command whitelisting** instead of blacklisting
- **Encrypted command channels**
- **Access logging and monitoring**
- **Network segmentation**

## Troubleshooting

### Client Won't Connect
1. Verify server is running: `netstat -tlnp | grep 8888`
2. Check network connectivity: `ping 192.168.210.13`
3. Verify authentication token matches
4. Check firewall settings

### Commands Not Executing
1. Check client logs: `docker exec <container> cat /tmp/c2client.log`
2. Verify command syntax
3. Check if command is blocked by safety filter
4. Ensure command completes within 30-second timeout

### Server Console Not Responding
1. Check server logs: `cat c2server.log`
2. Restart server if needed
3. Verify no other process is using port 8888

## File Structure

```
c2 builds/
├── c2server.py       # Main C2 server
├── c2client.py       # C2 client agent
├── deploy_c2.sh      # Deployment script
├── c2server.log      # Server logs (created when running)
└── README.md         # This file
```

## License

Educational use only. Part of Malformed Labs infrastructure.

---

**Happy commanding! 🔥**