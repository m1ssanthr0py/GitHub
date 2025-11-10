#!/usr/bin/env python3
"""
C2 Network Utility Client
Specialized client for network operations and route management
Can be used to discover network configuration and update routing
"""

import subprocess
import json
import platform
import os
import sys
import socket
import re

def get_network_info():
    """Get comprehensive network information without interactive terminal"""
    network_info = {
        'system': platform.system(),
        'interfaces': {},
        'routes': {},
        'connectivity': {}
    }
    
    try:
        # Method 1: Use socket to get primary IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        network_info['primary_ip'] = primary_ip
    except:
        network_info['primary_ip'] = 'Unknown'
    
    # System-specific network commands
    if platform.system().lower() == 'linux':
        network_info.update(get_linux_network_info())
    elif platform.system().lower() == 'darwin':  # macOS
        network_info.update(get_macos_network_info())
    elif platform.system().lower() == 'windows':
        network_info.update(get_windows_network_info())
    
    return network_info

def run_command_safe(command):
    """Run command safely and return result"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def get_linux_network_info():
    """Get Linux-specific network information"""
    info = {}
    
    # Get interfaces with ip command
    cmd_result = run_command_safe("ip addr show")
    if cmd_result['success']:
        info['ip_addr'] = parse_linux_interfaces(cmd_result['stdout'])
    
    # Get routing table
    cmd_result = run_command_safe("ip route show")
    if cmd_result['success']:
        info['routes'] = parse_linux_routes(cmd_result['stdout'])
    
    # Alternative: ifconfig if ip not available
    cmd_result = run_command_safe("ifconfig")
    if cmd_result['success']:
        info['ifconfig'] = parse_ifconfig_output(cmd_result['stdout'])
    
    # Get default gateway
    cmd_result = run_command_safe("ip route show default")
    if cmd_result['success']:
        info['default_gateway'] = cmd_result['stdout'].strip()
    
    return info

def get_macos_network_info():
    """Get macOS-specific network information"""
    info = {}
    
    # Get interfaces
    cmd_result = run_command_safe("ifconfig")
    if cmd_result['success']:
        info['interfaces'] = parse_ifconfig_output(cmd_result['stdout'])
    
    # Get routing table
    cmd_result = run_command_safe("netstat -rn")
    if cmd_result['success']:
        info['routes'] = parse_macos_routes(cmd_result['stdout'])
    
    # Get default gateway
    cmd_result = run_command_safe("route -n get default")
    if cmd_result['success']:
        info['default_gateway'] = cmd_result['stdout'].strip()
    
    return info

def get_windows_network_info():
    """Get Windows-specific network information"""
    info = {}
    
    # Get interfaces
    cmd_result = run_command_safe("ipconfig /all")
    if cmd_result['success']:
        info['interfaces'] = parse_windows_ipconfig(cmd_result['stdout'])
    
    # Get routing table
    cmd_result = run_command_safe("route print")
    if cmd_result['success']:
        info['routes'] = parse_windows_routes(cmd_result['stdout'])
    
    return info

def parse_linux_interfaces(output):
    """Parse Linux ip addr show output"""
    interfaces = {}
    current_interface = None
    
    for line in output.split('\n'):
        line = line.strip()
        
        # Interface line (e.g., "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>")
        if re.match(r'^\d+:', line):
            parts = line.split(':')
            if len(parts) >= 2:
                current_interface = parts[1].strip()
                interfaces[current_interface] = {'ips': [], 'status': 'unknown'}
                
                if 'UP' in line:
                    interfaces[current_interface]['status'] = 'up'
        
        # IP address line (e.g., "inet 192.168.1.100/24")
        elif 'inet ' in line and current_interface:
            ip_match = re.search(r'inet (\S+)', line)
            if ip_match:
                interfaces[current_interface]['ips'].append(ip_match.group(1))
    
    return interfaces

def parse_linux_routes(output):
    """Parse Linux ip route show output"""
    routes = []
    for line in output.split('\n'):
        line = line.strip()
        if line:
            routes.append(line)
    return routes

def parse_ifconfig_output(output):
    """Parse ifconfig output (Linux/macOS)"""
    interfaces = {}
    current_interface = None
    
    for line in output.split('\n'):
        # Interface line (starts with interface name)
        if re.match(r'^[a-zA-Z0-9]+:', line):
            current_interface = line.split(':')[0]
            interfaces[current_interface] = {'ips': [], 'status': 'unknown'}
            
            if 'UP' in line:
                interfaces[current_interface]['status'] = 'up'
        
        # IP address line
        elif 'inet ' in line and current_interface:
            ip_match = re.search(r'inet (\S+)', line)
            if ip_match:
                ip_addr = ip_match.group(1)
                interfaces[current_interface]['ips'].append(ip_addr)
    
    return interfaces

def parse_macos_routes(output):
    """Parse macOS netstat -rn output"""
    routes = []
    lines = output.split('\n')
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('Routing') and not line.startswith('Destination'):
            routes.append(line)
    
    return routes

def parse_windows_ipconfig(output):
    """Parse Windows ipconfig /all output"""
    interfaces = {}
    current_interface = None
    
    for line in output.split('\n'):
        line = line.strip()
        
        # Interface line
        if 'adapter' in line.lower():
            current_interface = line
            interfaces[current_interface] = {'ips': [], 'status': 'unknown'}
        
        # IP address line
        elif 'IPv4 Address' in line and current_interface:
            ip_match = re.search(r': (\S+)', line)
            if ip_match:
                interfaces[current_interface]['ips'].append(ip_match.group(1))
    
    return interfaces

def parse_windows_routes(output):
    """Parse Windows route print output"""
    routes = []
    in_route_table = False
    
    for line in output.split('\n'):
        line = line.strip()
        
        if 'Network Destination' in line:
            in_route_table = True
            continue
        
        if in_route_table and line and not line.startswith('='):
            routes.append(line)
    
    return routes

def add_route_linux(destination, gateway, interface=None):
    """Add route on Linux"""
    cmd = f"ip route add {destination}"
    if gateway:
        cmd += f" via {gateway}"
    if interface:
        cmd += f" dev {interface}"
    
    return run_command_safe(cmd)

def add_route_macos(destination, gateway, interface=None):
    """Add route on macOS"""
    cmd = f"route add {destination}"
    if gateway:
        cmd += f" {gateway}"
    if interface:
        cmd += f" -interface {interface}"
    
    return run_command_safe(cmd)

def add_route_windows(destination, gateway, interface=None):
    """Add route on Windows"""
    cmd = f"route add {destination}"
    if gateway:
        cmd += f" {gateway}"
    if interface:
        cmd += f" if {interface}"
    
    return run_command_safe(cmd)

def add_route(destination, gateway, interface=None):
    """Add route based on operating system"""
    system = platform.system().lower()
    
    if system == 'linux':
        return add_route_linux(destination, gateway, interface)
    elif system == 'darwin':
        return add_route_macos(destination, gateway, interface)
    elif system == 'windows':
        return add_route_windows(destination, gateway, interface)
    else:
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Unsupported operating system: {system}',
            'returncode': -1
        }

def test_connectivity(host, port=8888):
    """Test connectivity to a host and port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        return {
            'host': host,
            'port': port,
            'reachable': result == 0,
            'error': None if result == 0 else f"Connection failed (error {result})"
        }
    except Exception as e:
        return {
            'host': host,
            'port': port,
            'reachable': False,
            'error': str(e)
        }

def find_docker_host_candidates():
    """Find potential Docker host IP addresses"""
    candidates = []
    
    # Get network info
    network_info = get_network_info()
    
    # Add primary IP
    if 'primary_ip' in network_info:
        candidates.append(network_info['primary_ip'])
    
    # Add IPs from interfaces
    for interface_name, interface_info in network_info.get('interfaces', {}).items():
        if isinstance(interface_info, dict) and 'ips' in interface_info:
            for ip in interface_info['ips']:
                # Clean IP (remove subnet mask if present)
                ip_clean = ip.split('/')[0]
                if ip_clean not in candidates and not ip_clean.startswith('127.'):
                    candidates.append(ip_clean)
    
    return candidates

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("=== C2 Network Utility ===")
        print("Usage:")
        print("  python3 c2_network_util.py info                     # Show network info")
        print("  python3 c2_network_util.py route <dest> <gateway>   # Add route")
        print("  python3 c2_network_util.py test <host> [port]       # Test connectivity")
        print("  python3 c2_network_util.py docker                   # Find Docker host IPs")
        print("  python3 c2_network_util.py config <host_ip>         # Update C2 config")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'info':
        print("=== Network Information ===")
        network_info = get_network_info()
        print(json.dumps(network_info, indent=2))
        
    elif command == 'route':
        if len(sys.argv) < 4:
            print("Usage: python3 c2_network_util.py route <destination> <gateway>")
            return
        
        destination = sys.argv[2]
        gateway = sys.argv[3]
        interface = sys.argv[4] if len(sys.argv) > 4 else None
        
        print(f"Adding route: {destination} via {gateway}")
        result = add_route(destination, gateway, interface)
        
        if result['success']:
            print("[SUCCESS] Route added successfully")
        else:
            print(f"[ERROR] Failed to add route: {result['stderr']}")
        
    elif command == 'test':
        if len(sys.argv) < 3:
            print("Usage: python3 c2_network_util.py test <host> [port]")
            return
        
        host = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 8888
        
        print(f"Testing connectivity to {host}:{port}")
        result = test_connectivity(host, port)
        
        if result['reachable']:
            print("[SUCCESS] Connection successful")
        else:
            print(f"[ERROR] Connection failed: {result['error']}")
        
    elif command == 'docker':
        print("=== Docker Host IP Discovery ===")
        candidates = find_docker_host_candidates()
        
        print("Potential Docker host IP addresses:")
        for i, ip in enumerate(candidates, 1):
            connectivity = test_connectivity(ip, 8888)
            status = "[REACHABLE]" if connectivity['reachable'] else "[NOT REACHABLE]"
            print(f"  {i}. {ip} - {status}")
        
        print(f"\nTo use one of these IPs:")
        print(f"  python3 c2_network_util.py config <ip_address>")
        print(f"  python3 c2client.py <ip_address> 8888")
        
    elif command == 'config':
        if len(sys.argv) < 3:
            print("Usage: python3 c2_network_util.py config <host_ip>")
            return
        
        host_ip = sys.argv[2]
        config_file = 'c2_config.json'
        
        # Test connectivity first
        print(f"Testing connectivity to {host_ip}:8888...")
        connectivity = test_connectivity(host_ip, 8888)
        
        if connectivity['reachable']:
            print("[SUCCESS] Host is reachable")
        else:
            print(f"[WARNING] Host not reachable - {connectivity['error']}")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
        
        # Update config file
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                config['server']['host'] = host_ip
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
                
                print(f"[SUCCESS] Updated {config_file} with host IP: {host_ip}")
                print(f"   Now run: python3 c2client_config.py")
            else:
                print(f"[ERROR] Config file not found: {config_file}")
        
        except Exception as e:
            print(f"[ERROR] Error updating config: {e}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()