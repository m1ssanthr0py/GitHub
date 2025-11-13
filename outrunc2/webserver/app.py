#!/usr/bin/env python3
from flask import Flask, render_template, jsonify, request
import os
import subprocess
import json
import socket
from datetime import datetime
from ping3 import ping, verbose_ping
import docker
import time
import threading
from collections import defaultdict

app = Flask(__name__)

# Connection monitoring storage
connected_clients = {}  # client_id -> {info, last_seen, status}
connection_events = []  # List of connection events with timestamps
client_commands = defaultdict(list)  # client_id -> [commands]
client_results = defaultdict(list)  # client_id -> [results]
connections_lock = threading.Lock()

# Initialize Docker client
try:
    # Try to connect to Docker using the Unix socket directly
    docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    # Test the connection
    docker_client.ping()
except Exception as e:
    try:
        # Fallback to default from_env method
        docker_client = docker.from_env()
        docker_client.ping()
    except Exception as e2:
        docker_client = None
        print(f"Warning: Could not connect to Docker: {e2}")

# Client container mapping
CLIENT_CONTAINERS = {
    'endpoint1': 'linux_endpoint1',
    'endpoint2': 'linux_endpoint2', 
    'endpoint3': 'linux_endpoint3'
}

def execute_command_on_client(container_name, command):
    """Execute a command on a specific client container"""
    try:
        # Use docker exec directly via subprocess as a more reliable method
        cmd = ['docker', 'exec', container_name, 'sh', '-c', command]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Command timed out after 30 seconds'}
    except FileNotFoundError:
        return {'success': False, 'error': 'Docker command not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_client_status():
    """Get status of all client containers"""
    clients = {}
    for client_name, container_name in CLIENT_CONTAINERS.items():
        try:
            # Use docker inspect to get container info
            cmd = ['docker', 'inspect', container_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                container_info = json.loads(result.stdout)[0]
                
                # Get container state
                state = container_info['State']
                running = state.get('Running', False)
                status = 'running' if running else state.get('Status', 'unknown')
                
                # Get IP address
                networks = container_info['NetworkSettings']['Networks']
                ip_address = 'N/A'
                if networks:
                    # Try to find lab_network first, then any network
                    for network_name, network_info in networks.items():
                        if 'lab_network' in network_name and network_info.get('IPAddress'):
                            ip_address = network_info['IPAddress']
                            break
                        elif network_info.get('IPAddress'):
                            ip_address = network_info['IPAddress']
                
                clients[client_name] = {
                    'container_name': container_name,
                    'status': status,
                    'running': running,
                    'ip_address': ip_address
                }
            else:
                clients[client_name] = {
                    'container_name': container_name,
                    'status': 'not_found',
                    'running': False,
                    'ip_address': 'N/A'
                }
        except Exception as e:
            clients[client_name] = {
                'container_name': container_name,
                'status': f'error: {str(e)}',
                'running': False,
                'ip_address': 'N/A'
            }
    
    return clients

def get_system_info():
    """Get basic system information"""
    try:
        # Get hostname
        try:
            hostname = subprocess.check_output(['hostname'], text=True).strip()
        except:
            hostname = socket.gethostname()
        
        # Get IP addresses with fallback methods
        ip_info = ""
        try:
            ip_info = subprocess.check_output(['ip', 'addr', 'show'], text=True)
        except FileNotFoundError:
            try:
                # Fallback to ifconfig
                ip_info = subprocess.check_output(['ifconfig'], text=True)
            except FileNotFoundError:
                # Simple socket-based approach
                try:
                    # Get container's IP by connecting to external host
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    ip_info = f"Container IP: {local_ip}\nHostname IP: {socket.gethostbyname(hostname)}"
                except Exception as sock_e:
                    ip_info = f"Network interface info unavailable: {str(sock_e)}"
        except Exception as e:
            ip_info = f"IP lookup error: {str(e)}"
        
        # Get uptime
        try:
            uptime = subprocess.check_output(['uptime'], text=True).strip()
        except FileNotFoundError:
            # Read from /proc/uptime if available
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    uptime = f"up {uptime_seconds/3600:.1f} hours"
            except:
                uptime = "uptime command not available"
        
        return {
            'hostname': hostname,
            'ip_info': ip_info,
            'uptime': uptime,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def ping_endpoints():
    """Test connectivity to other endpoints in the lab network using ICMP ping"""
    endpoints = {
        '192.168.210.10': 'linux_endpoint1 (Alpine)',
        '192.168.210.11': 'linux_endpoint2 (Alpine)', 
        '192.168.210.12': 'linux_endpoint3 (Alpine)'
    }
    results = {}
    
    for endpoint, description in endpoints.items():
        output_lines = [f"ICMP Ping to {description}"]
        success = False
        
        try:
            # Send 3 ICMP ping packets
            ping_times = []
            for i in range(3):
                response_time = ping(endpoint, timeout=2)
                if response_time is not None:
                    ping_times.append(response_time * 1000)  # Convert to milliseconds
                else:
                    ping_times.append(None)
            
            # Check results
            successful_pings = [t for t in ping_times if t is not None]
            
            if successful_pings:
                success = True
                avg_time = sum(successful_pings) / len(successful_pings)
                min_time = min(successful_pings)
                max_time = max(successful_pings)
                packet_loss = ((3 - len(successful_pings)) / 3) * 100
                
                output_lines.append(f"✓ {endpoint} is reachable")
                output_lines.append(f"   Packets: 3 sent, {len(successful_pings)} received, {packet_loss:.0f}% loss")
                output_lines.append(f"   RTT: min={min_time:.1f}ms, avg={avg_time:.1f}ms, max={max_time:.1f}ms")
            else:
                output_lines.append(f"✗ {endpoint} is unreachable")
                output_lines.append(f"   All 3 ICMP packets lost")
                
        except PermissionError:
            # ICMP requires root privileges, fall back to socket test
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((endpoint, 22))
                sock.close()
                
                if result in [0, 111]:  # Connected or connection refused (both mean reachable)
                    success = True
                    output_lines.append(f"✓ {endpoint} is reachable (TCP test)")
                    output_lines.append("   Note: ICMP requires root privileges")
                else:
                    output_lines.append(f"✗ {endpoint} appears unreachable")
                    output_lines.append(f"   TCP connection failed (code: {result})")
            except Exception as e:
                output_lines.append(f"✗ Network test failed: {str(e)}")
                
        except Exception as e:
            output_lines.append(f"✗ ICMP ping failed: {str(e)}")
            # Fallback to socket test
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((endpoint, 22))
                sock.close()
                
                if result in [0, 111]:
                    success = True
                    output_lines.append(f"✓ {endpoint} reachable via TCP fallback")
            except:
                pass
        
        results[endpoint] = {
            'success': success,
            'output': '\n'.join(output_lines)
        }
    
    return results

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/system')
def api_system():
    """API endpoint for system information"""
    return jsonify(get_system_info())

@app.route('/api/network')
def api_network():
    """API endpoint for network connectivity testing"""
    return jsonify(ping_endpoints())

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/terminal')
def terminal():
    """Terminal interface page"""
    return render_template('terminal.html')

@app.route('/about')
def about():
    """About page with theme information"""
    return render_template('about.html')

@app.route('/api/clients')
def api_clients():
    """API endpoint for client container status"""
    return jsonify(get_client_status())

@app.route('/api/clients/<client_name>/execute', methods=['POST'])
def api_client_execute(client_name):
    """Execute command on specific client container"""
    if client_name not in CLIENT_CONTAINERS:
        return jsonify({
            'success': False,
            'error': f'Unknown client: {client_name}. Available clients: {", ".join(CLIENT_CONTAINERS.keys())}'
        })
    
    data = request.get_json()
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({
            'success': False,
            'error': 'No command specified'
        })
    
    # Whitelist of safe commands for client containers
    safe_commands = {
        'whoami': 'whoami',
        'pwd': 'pwd', 
        'ls': 'ls -la',
        'date': 'date',
        'uptime': 'uptime',
        'ip addr': 'ip addr show',
        'ps': 'ps aux',
        'df': 'df -h',
        'free': 'free -h',
        'cat /etc/os-release': 'cat /etc/os-release',
        'hostname': 'hostname',
        'id': 'id',
        'env': 'env',
        'which python3': 'which python3',
        'python3 --version': 'python3 --version',
        'ping -c 3 8.8.8.8': 'ping -c 3 8.8.8.8',
        'netstat -tuln': 'netstat -tuln'
    }
    
    if command in safe_commands:
        container_name = CLIENT_CONTAINERS[client_name]
        result = execute_command_on_client(container_name, safe_commands[command])
        
        if result['success']:
            return jsonify({
                'success': True,
                'client': client_name,
                'container': container_name,
                'command': command,
                'stdout': result['stdout'],
                'stderr': result['stderr'] if result['stderr'] else None,
                'exit_code': result['exit_code']
            })
        else:
            return jsonify({
                'success': False,
                'client': client_name,
                'container': container_name,
                'error': result['error']
            })
    else:
        return jsonify({
            'success': False,
            'error': f'Command not allowed. Available commands: {", ".join(safe_commands.keys())}'
        })

@app.route('/api/clients/execute-all', methods=['POST'])
def api_clients_execute_all():
    """Execute command on all client containers"""
    data = request.get_json()
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({
            'success': False,
            'error': 'No command specified'
        })
    
    # Use the same safe commands whitelist
    safe_commands = {
        'whoami': 'whoami',
        'pwd': 'pwd', 
        'ls': 'ls -la',
        'date': 'date',
        'uptime': 'uptime',
        'ip addr': 'ip addr show',
        'ps': 'ps aux',
        'df': 'df -h',
        'free': 'free -h',
        'cat /etc/os-release': 'cat /etc/os-release',
        'hostname': 'hostname',
        'id': 'id',
        'env': 'env',
        'which python3': 'which python3',
        'python3 --version': 'python3 --version',
        'ping -c 3 8.8.8.8': 'ping -c 3 8.8.8.8',
        'netstat -tuln': 'netstat -tuln'
    }
    
    if command not in safe_commands:
        return jsonify({
            'success': False,
            'error': f'Command not allowed. Available commands: {", ".join(safe_commands.keys())}'
        })
    
    results = {}
    for client_name, container_name in CLIENT_CONTAINERS.items():
        result = execute_command_on_client(container_name, safe_commands[command])
        results[client_name] = {
            'container': container_name,
            'success': result['success'],
            'stdout': result['stdout'] if result['success'] else None,
            'stderr': result['stderr'] if result['success'] else None,
            'error': result['error'] if not result['success'] else None,
            'exit_code': result.get('exit_code', None)
        }
    
    return jsonify({
        'command': command,
        'results': results
    })

@app.route('/api/execute', methods=['POST'])
def api_execute():
    """Execute safe commands (limited for security)"""
    data = request.get_json()
    command = data.get('command', '').strip()
    
    # Whitelist of safe commands
    safe_commands = {
        'whoami': ['whoami'],
        'pwd': ['pwd'],
        'ls': ['ls', '-la'],
        'date': ['date'],
        'uptime': ['uptime'],
        'ip addr': ['ip', 'addr', 'show'],
        'ps': ['ps', 'aux'],
        'df': ['df', '-h'],
        'free': ['free', '-h']
    }
    
    if command in safe_commands:
        try:
            result = subprocess.run(
                safe_commands[command],
                capture_output=True,
                text=True,
                timeout=10
            )
            return jsonify({
                'success': True,
                'output': result.stdout,
                'error': result.stderr if result.stderr else None
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    else:
        return jsonify({
            'success': False,
            'error': f'Command not allowed. Available commands: {", ".join(safe_commands.keys())}'
        })

# ==== CLIENT CONNECTION MONITORING ENDPOINTS ====

def add_connection_event(event_type, client_id, details=""):
    """Add a connection event to the monitoring log"""
    with connections_lock:
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,  # 'connect', 'disconnect', 'heartbeat', 'command', 'register'
            'client_id': client_id,
            'details': details
        }
        connection_events.append(event)
        
        # Keep only last 100 events
        if len(connection_events) > 100:
            connection_events.pop(0)

@app.route('/api/register', methods=['POST'])
def api_register_client():
    """Register a new client connection"""
    data = request.get_json()
    if not data or 'client_id' not in data:
        return jsonify({'success': False, 'error': 'Invalid registration data'})
    
    client_id = data['client_id']
    
    with connections_lock:
        # Update client info
        connected_clients[client_id] = {
            'client_id': client_id,
            'hostname': data.get('hostname', 'unknown'),
            'os': data.get('os', 'unknown'),
            'arch': data.get('arch', 'unknown'),
            'user': data.get('user', 'unknown'),
            'pwd': data.get('pwd', 'unknown'),
            'local_ip': data.get('local_ip', request.remote_addr),
            'remote_ip': request.remote_addr,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'status': 'connected',
            'command_count': 0,
            'result_count': 0
        }
    
    # Log the registration event
    add_connection_event('register', client_id, f"New client from {request.remote_addr}")
    
    print(f"[+] Client registered: {client_id} from {request.remote_addr}")
    
    return jsonify({'success': True, 'message': 'Client registered successfully'})

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """Handle client heartbeat"""
    data = request.get_json()
    if not data or 'client_id' not in data:
        return jsonify({'success': False, 'error': 'Invalid heartbeat data'})
    
    client_id = data['client_id']
    
    with connections_lock:
        if client_id in connected_clients:
            connected_clients[client_id]['last_seen'] = datetime.now().isoformat()
            connected_clients[client_id]['status'] = 'connected'
        else:
            # Auto-register if not found
            connected_clients[client_id] = {
                'client_id': client_id,
                'hostname': 'unknown',
                'os': 'unknown',
                'remote_ip': request.remote_addr,
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'status': 'connected',
                'command_count': 0,
                'result_count': 0
            }
    
    # Log heartbeat (but only occasionally to avoid spam)
    if int(time.time()) % 30 == 0:  # Log every 30th heartbeat
        add_connection_event('heartbeat', client_id, "Client alive")
    
    return jsonify({'success': True})

@app.route('/api/clients/<client_id>', methods=['GET'])
def api_get_client_commands(client_id):
    """Get pending commands for a specific client"""
    with connections_lock:
        commands = client_commands.get(client_id, [])
        # Mark commands as delivered
        client_commands[client_id] = []
    
    return jsonify({
        'success': True,
        'commands': commands
    })

@app.route('/api/clients/<client_id>/command', methods=['POST'])
def api_send_client_command(client_id):
    """Send a command to a specific client"""
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({'success': False, 'error': 'No command provided'})
    
    command_id = f"cmd-{int(time.time())}-{client_id}"
    command_data = {
        'id': command_id,
        'command': data['command'],
        'timestamp': datetime.now().isoformat()
    }
    
    with connections_lock:
        client_commands[client_id].append(command_data)
        if client_id in connected_clients:
            connected_clients[client_id]['command_count'] += 1
    
    add_connection_event('command', client_id, f"Sent: {data['command']}")
    
    return jsonify({'success': True, 'command_id': command_id})

@app.route('/api/results', methods=['POST'])
def api_receive_results():
    """Receive command results from clients"""
    data = request.get_json()
    if not data or 'client_id' not in data:
        return jsonify({'success': False, 'error': 'Invalid result data'})
    
    client_id = data['client_id']
    command_id = data.get('command_id', 'unknown')
    result = data.get('result', {})
    
    result_data = {
        'command_id': command_id,
        'timestamp': datetime.now().isoformat(),
        'result': result,
        'client_id': client_id
    }
    
    with connections_lock:
        client_results[client_id].append(result_data)
        if client_id in connected_clients:
            connected_clients[client_id]['result_count'] += 1
            connected_clients[client_id]['last_seen'] = datetime.now().isoformat()
    
    add_connection_event('result', client_id, f"Command result received")
    
    return jsonify({'success': True})

@app.route('/api/connections')
def api_connections():
    """Get current client connections and events"""
    with connections_lock:
        # Clean up stale connections (no heartbeat in 5 minutes)
        current_time = datetime.now()
        stale_clients = []
        
        for client_id, info in connected_clients.items():
            last_seen = datetime.fromisoformat(info['last_seen'])
            if (current_time - last_seen).seconds > 300:  # 5 minutes
                info['status'] = 'disconnected'
                stale_clients.append(client_id)
        
        # Log disconnections
        for client_id in stale_clients:
            add_connection_event('disconnect', client_id, "Connection timeout")
        
        return jsonify({
            'success': True,
            'clients': dict(connected_clients),
            'events': connection_events[-20:],  # Last 20 events
            'total_clients': len(connected_clients),
            'active_clients': len([c for c in connected_clients.values() if c['status'] == 'connected']),
            'total_events': len(connection_events)
        })

@app.route('/api/client/<client_id>/results')
def api_client_results(client_id):
    """Get results for a specific client"""
    with connections_lock:
        results = client_results.get(client_id, [])
    
    return jsonify({
        'success': True,
        'client_id': client_id,
        'results': results[-10:]  # Last 10 results
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("[*] Starting Malformed Labs C2 Server")
    print("[*] Connection monitoring enabled")
    print("[*] Access dashboard at http://0.0.0.0:8080")
    
    app.run(host='0.0.0.0', port=8080, debug=True)