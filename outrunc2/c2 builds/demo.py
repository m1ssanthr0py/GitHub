#!/usr/bin/env python3
"""
C2 Demo Script - Automated demo of C2 server and client functionality
"""

import subprocess
import time
import threading
import os
import sys

def run_server_demo():
    """Run server in demo mode"""
    print("[DEMO] Starting C2 Server...")
    
    # Start server in background
    server_process = subprocess.Popen([
        sys.executable, 'c2server.py', 'demo123'
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
    
    return server_process

def run_client_demo(server_ip="127.0.0.1", server_port="8888"):
    """Run client in demo mode"""
    time.sleep(2)  # Wait for server to start
    
    print(f"[DEMO] Starting C2 Client connecting to {server_ip}:{server_port}")
    
    # Start client
    client_process = subprocess.Popen([
        sys.executable, 'c2client.py', server_ip, server_port, 'demo123'
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
    
    return client_process

def main():
    print("=" * 60)
    print("C2 Server & Client Demo")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "client":
        # Run only client (for container demo)
        server_ip = sys.argv[2] if len(sys.argv) > 2 else "192.168.210.1"
        server_port = sys.argv[3] if len(sys.argv) > 3 else "8888"
        
        print(f"[DEMO] Client-only mode - connecting to {server_ip}:{server_port}")
        client_process = run_client_demo(server_ip, server_port)
        
        try:
            client_process.wait()
        except KeyboardInterrupt:
            print("\n[DEMO] Stopping client...")
            client_process.terminate()
            
    else:
        # Run both server and client (local demo)
        print("[DEMO] Starting local demo (server + client)")
        
        try:
            # Start server
            server_process = run_server_demo()
            time.sleep(3)
            
            # Start client
            client_process = run_client_demo()
            
            print("\n[DEMO] Both server and client are running!")
            print("[DEMO] You can now:")
            print("  1. Switch to the server terminal")
            print("  2. Try commands like: list, cmd <client_id> whoami, broadcast ls")
            print("  3. Press Ctrl+C to stop the demo")
            
            # Wait for processes
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n[DEMO] Stopping demo...")
            
            # Kill processes
            try:
                server_process.terminate()
                client_process.terminate()
                time.sleep(2)
                server_process.kill()
                client_process.kill()
            except:
                pass
                
    print("[DEMO] Demo complete!")

if __name__ == "__main__":
    main()