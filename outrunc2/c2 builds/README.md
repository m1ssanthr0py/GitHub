# C2 Server and Client

A secure Command and Control (C2) system with encrypted communication, file transfer capabilities, and heartbeat monitoring.

## Features

### Server Features
- ✅ **Encrypted Communication**: All data encrypted using Fernet (AES 128 in CBC mode)
- ✅ **Heartbeat Monitoring**: Receives heartbeat every 5 minutes from clients
- ✅ **Command Execution**: Send commands to clients and see output in real-time
- ✅ **File Transfer**: Encrypted file upload/download between server and clients
- ✅ **Multi-client Support**: Handle multiple clients simultaneously
- ✅ **Interactive CLI**: Command-line interface for server management

### Client Features  
- ✅ **Auto-reconnection**: Automatically reconnects to server if connection drops
- ✅ **Cross-platform**: Works on Windows, Linux, and macOS
- ✅ **System Information**: Sends detailed system info to server
- ✅ **Background Operation**: Runs silently in background
- ✅ **Secure Communication**: End-to-end encryption

## Installation

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **For Docker containers**, the requirements are already installed via the docker-compose.yaml

## Usage

### Starting the Server

```bash
# Start server with default password
python3 c2server.py

# Start server with custom password
python3 c2server.py mypassword123
```

The server will start on `0.0.0.0:8888` by default.

### Server Commands

Once the server is running, you can use these commands:

```bash
# List all connected clients
list

# Send command to specific client
cmd <client_id> <command>
# Example: cmd 192.168.210.10:54321 whoami

# Send command to all clients
broadcast <command>
# Example: broadcast ls -la

# Upload file to client
upload <client_id> <filepath>
# Example: upload 192.168.210.10:54321 ./uploads/script.py

# Show help
help

# Exit server
quit
```

### Starting the Client

```bash
# Connect client to server
python3 c2client.py <server_ip> <server_port> <password>

# Example:
python3 c2client.py 192.168.210.1 8888 mypassword123
```

### Running in Docker Containers

The docker-compose.yaml already includes Python3, so you can run the client directly:

```bash
# Enter container
docker exec -it linux_endpoint1 sh

# Install dependencies (Alpine)
pip install cryptography psutil

# Run client
python3 c2client.py 192.168.210.1 8888 mypassword123
```

## Security Features

### Encryption
- **Algorithm**: Fernet (AES 128 in CBC mode with HMAC-SHA256 for authentication)
- **Key Derivation**: PBKDF2 with SHA256, 100,000 iterations
- **Password Protection**: Server and clients must use the same password

### Network Security
- **Custom Network**: Uses dedicated bridge network (192.168.210.0/24)
- **Port Control**: Configurable listening port
- **Connection Timeout**: Automatic client disconnection after 6 minutes without heartbeat

## File Structure

```
c2 builds/
├── c2server.py          # Main server application
├── c2client.py          # Client application
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── downloads/          # Server downloads from clients (auto-created)
└── uploads/            # Files to upload to clients (create manually)
```

## Network Architecture

```
Server (192.168.210.1:8888)
    ↕️ [Encrypted Communication]
├── Client 1 (192.168.210.10) - Alpine Linux
├── Client 2 (192.168.210.11) - Ubuntu  
└── Client 3 (192.168.210.12) - CentOS
```

## Example Workflow

1. **Start Server**:
   ```bash
   python3 c2server.py secretpassword
   ```

2. **Deploy Clients** (in each container):
   ```bash
   pip install cryptography psutil
   python3 c2client.py 192.168.210.1 8888 secretpassword
   ```

3. **Server Operations**:
   ```bash
   # Check connected clients
   list
   
   # Get system info from all clients
   broadcast uname -a
   
   # Check specific client
   cmd 192.168.210.10:54321 ps aux
   
   # Upload script to client
   upload 192.168.210.10:54321 ./uploads/script.py
   ```

## Troubleshooting

### Connection Issues
- Check firewall settings
- Verify network connectivity: `ping 192.168.210.1`
- Ensure correct password on both server and client
- Check if port 8888 is available: `netstat -an | grep 8888`

### Container Issues
- Make sure containers are on the same network
- Verify Python3 is installed: `python3 --version`
- Check dependencies: `pip list | grep cryptography`

### Encryption Issues
- Ensure both server and client use the same password
- Check for typos in the password
- Restart both server and client if key issues persist

## Security Considerations

⚠️ **For Educational/Lab Use Only**

This C2 system is designed for educational purposes and lab environments. Do not use in production or for malicious purposes.

### Recommendations for Lab Use
- Use strong, unique passwords
- Run in isolated network environments
- Monitor all communications
- Regular security updates of dependencies
- Use firewall rules to restrict access

## License

This project is for educational purposes only. Use responsibly and in compliance with all applicable laws and regulations.