#!/usr/bin/env python3
"""
Simple Network Route Manager
Lightweight script for managing routes to C2 server without interactive terminal
"""

import subprocess
import platform
import sys
import socket

def run_cmd(cmd):
    """Run command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except:
        return False, "", "Command failed"

def get_my_ip():
    """Get this machine's IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unknown"

def show_routes():
    """Show current routing table"""
    system = platform.system().lower()
    
    if system == "linux":
        success, out, err = run_cmd("ip route show")
    elif system == "darwin":  # macOS
        success, out, err = run_cmd("netstat -rn")
    elif system == "windows":
        success, out, err = run_cmd("route print")
    else:
        return False, "Unsupported OS"
    
    if success:
        return True, out
    else:
        return False, err

def add_c2_route(c2_server_network, gateway_ip):
    """Add route to C2 server network"""
    system = platform.system().lower()
    
    if system == "linux":
        cmd = f"ip route add {c2_server_network} via {gateway_ip}"
    elif system == "darwin":  # macOS
        cmd = f"route add {c2_server_network} {gateway_ip}"
    elif system == "windows":
        cmd = f"route add {c2_server_network} {gateway_ip}"
    else:
        return False, "Unsupported OS"
    
    success, out, err = run_cmd(cmd)
    return success, out if success else err

def test_c2_connection(host, port=8888):
    """Test if we can reach the C2 server"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("=== C2 Route Manager ===")
        print("Usage:")
        print("  python3 route_manager.py info                          # Show network info")
        print("  python3 route_manager.py routes                       # Show routes") 
        print("  python3 route_manager.py add <network> <gateway>      # Add route")
        print("  python3 route_manager.py test <c2_host> [port]        # Test C2 connection")
        print("  python3 route_manager.py quick                        # Quick C2 setup")
        print("")
        print("Examples:")
        print("  python3 route_manager.py add 192.168.210.0/24 192.168.1.1")
        print("  python3 route_manager.py test 192.168.1.100 8888")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "info":
        my_ip = get_my_ip()
        system = platform.system()
        print(f"System: {system}")
        print(f"My IP: {my_ip}")
        
    elif cmd == "routes":
        success, output = show_routes()
        if success:
            print("Current routes:")
            print(output)
        else:
            print(f"Error: {output}")
            
    elif cmd == "add":
        if len(sys.argv) < 4:
            print("Usage: python3 route_manager.py add <network> <gateway>")
            print("Example: python3 route_manager.py add 192.168.210.0/24 192.168.1.1")
            return
            
        network = sys.argv[2]
        gateway = sys.argv[3]
        
        print(f"Adding route: {network} via {gateway}")
        success, message = add_c2_route(network, gateway)
        
        if success:
            print("[SUCCESS] Route added successfully")
        else:
            print(f"[ERROR] Failed: {message}")
            
    elif cmd == "test":
        if len(sys.argv) < 3:
            print("Usage: python3 route_manager.py test <host> [port]")
            return
            
        host = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 8888
        
        print(f"Testing connection to {host}:{port}...")
        
        if test_c2_connection(host, port):
            print("[SUCCESS] Connection successful!")
        else:
            print("[ERROR] Connection failed!")
            print(f"Possible solutions:")
            print(f"1. Verify C2 server is running on {host}:{port}")
            print(f"2. Check if you need to add a route:")
            print(f"   python3 route_manager.py add 192.168.210.0/24 <your_gateway>")
            print(f"3. Try connecting to Docker host IP instead of container IP")
            
    elif cmd == "quick":
        print("=== Quick C2 Setup ===")
        
        my_ip = get_my_ip()
        print(f"Your IP: {my_ip}")
        
        # Common Docker networks to try
        docker_networks = [
            "192.168.210.0/24",  # Your C2 network
            "172.17.0.0/16",     # Default Docker bridge
            "172.18.0.0/16",     # Docker compose networks
            "10.0.0.0/8"         # Private networks
        ]
        
        # Try to determine gateway (usually .1 of your network)
        ip_parts = my_ip.split('.')
        if len(ip_parts) == 4:
            gateway = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1"
            print(f"Likely gateway: {gateway}")
            
            print(f"\nTesting common C2 server addresses:")
            
            # Test common C2 server locations
            test_hosts = [
                my_ip.rsplit('.', 1)[0] + ".1",    # Gateway
                "192.168.210.13",                   # Your C2 container
                my_ip,                              # This machine
                "localhost"                         # Local
            ]
            
            for host in test_hosts:
                if test_c2_connection(host, 8888):
                    print(f"[FOUND] C2 server at: {host}:8888")
                else:
                    print(f"[NOT FOUND] No C2 server at: {host}:8888")
            
            print(f"\nTo add route to C2 network:")
            print(f"sudo python3 route_manager.py add 192.168.210.0/24 {gateway}")
        
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()