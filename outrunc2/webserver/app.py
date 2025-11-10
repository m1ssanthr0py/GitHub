#!/usr/bin/env python3
"""
Outrun Themed Web Server
A cyberpunk/synthwave styled web interface for the lab environment
"""

from flask import Flask, render_template, jsonify, request
import os
import subprocess
import json
import socket
from datetime import datetime
from ping3 import ping, verbose_ping

app = Flask(__name__)

def get_system_info():
    """Get basic system information"""
    try:
        # Get hostname
        hostname = subprocess.check_output(['hostname'], text=True).strip()
        
        # Get IP addresses
        ip_info = subprocess.check_output(['ip', 'addr', 'show'], text=True)
        
        # Get uptime
        uptime = subprocess.check_output(['uptime'], text=True).strip()
        
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
        '192.168.210.11': 'linux_endpoint2 (Ubuntu)', 
        '192.168.210.12': 'linux_endpoint3 (CentOS)'
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

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    app.run(host='0.0.0.0', port=8080, debug=True)