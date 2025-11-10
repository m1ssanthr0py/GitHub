#!/usr/bin/env python3
"""
Network Configuration Helper for C2 Client
Helps determine the correct IP address for remote clients to connect to the C2 server
"""

import subprocess
import json
import os
import sys
import socket

def get_network_interfaces():
    """Get network interface information"""
    interfaces = {}
    
    try:
        # Try to get IP addresses using different methods
        
        # Method 1: hostname -I (Linux/macOS)
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            if result.returncode == 0:
                ips = result.stdout.strip().split()
                interfaces['hostname_I'] = ips
        except:
            pass
        
        # Method 2: ifconfig (macOS/Linux)
        try:
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            if result.returncode == 0:
                interfaces['ifconfig_available'] = True
        except:
            interfaces['ifconfig_available'] = False
        
        # Method 3: ip addr (Linux)
        try:
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
            if result.returncode == 0:
                interfaces['ip_addr_available'] = True
        except:
            interfaces['ip_addr_available'] = False
            
        # Method 4: Python socket method
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            interfaces['socket_method'] = local_ip
        except:
            pass
            
    except Exception as e:
        interfaces['error'] = str(e)
    
    return interfaces

def update_config_file(host_ip):
    """Update the configuration file with the correct host IP"""
    config_file = 'c2_config.json'
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update the server host
            config['server']['host'] = host_ip
            
            # Update the first network option
            for option in config.get('network_options', []):
                if 'YOUR_DOCKER_HOST_IP' in option['host']:
                    option['host'] = host_ip
            
            # Write back to file
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            print(f"[SUCCESS] Updated {config_file} with host IP: {host_ip}")
            return True
        else:
            print(f"[ERROR] Configuration file not found: {config_file}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error updating config file: {e}")
        return False

def main():
    print("=== C2 Network Configuration Helper ===\n")
    
    # Get network information
    interfaces = get_network_interfaces()
    
    print("Network Interface Information:")
    print("-" * 40)
    
    recommended_ips = []
    
    if 'socket_method' in interfaces:
        ip = interfaces['socket_method']
        print(f"[DETECTED] Primary IP: {ip}")
        recommended_ips.append(ip)
    
    if 'hostname_I' in interfaces:
        for ip in interfaces['hostname_I']:
            if ip not in recommended_ips:
                print(f"[FOUND] Additional IP found: {ip}")
                recommended_ips.append(ip)
    
    print(f"\n[INFO] Available IP addresses: {', '.join(recommended_ips) if recommended_ips else 'None detected'}")
    
    # Docker-specific guidance
    print("\n[DOCKER] Network Guidance:")
    print("-" * 40)
    print("The C2 server is running inside Docker with these network settings:")
    print("  - Container IP: 192.168.210.13 (internal Docker network)")
    print("  - Exposed Port: 8888 (mapped to host)")
    print("  - Internal Network: 192.168.210.0/24")
    
    print(f"\n[REMOTE] For REMOTE clients to connect:")
    print("  [REQUIRED] Use the Docker HOST machine's IP address")
    print("  [REQUIRED] Connect to port 8888 (the exposed port)")
    print("  [WARNING] Do NOT use 192.168.210.13 (that's internal only)")
    
    # Interactive configuration
    if recommended_ips:
        print(f"\n[CONFIG] Configuration Options:")
        for i, ip in enumerate(recommended_ips, 1):
            print(f"  {i}. Use {ip}")
        print(f"  {len(recommended_ips) + 1}. Enter custom IP")
        print(f"  {len(recommended_ips) + 2}. Skip configuration")
        
        try:
            choice = input(f"\nSelect option (1-{len(recommended_ips) + 2}): ").strip()
            
            if choice.isdigit():
                choice = int(choice)
                
                if 1 <= choice <= len(recommended_ips):
                    selected_ip = recommended_ips[choice - 1]
                    if update_config_file(selected_ip):
                        print(f"\n[SUCCESS] Configuration complete!")
                        print(f"   Remote clients should now connect to: {selected_ip}:8888")
                        
                elif choice == len(recommended_ips) + 1:
                    custom_ip = input("Enter custom IP address: ").strip()
                    if custom_ip:
                        if update_config_file(custom_ip):
                            print(f"\n[SUCCESS] Configuration complete!")
                            print(f"   Remote clients should now connect to: {custom_ip}:8888")
                        
                elif choice == len(recommended_ips) + 2:
                    print("\n[SKIP] Skipping automatic configuration")
                    
        except KeyboardInterrupt:
            print("\n\n[CANCELLED] Configuration cancelled")
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")
    
    print(f"\n[MANUAL] Manual Configuration:")
    print("  1. Edit c2_config.json")
    print("  2. Replace 'YOUR_DOCKER_HOST_IP' with your Docker host's IP")
    print("  3. Run: python3 c2client_config.py")
    
    print(f"\n[TEST] Testing Connection:")
    print("  python3 c2client_config.py    (uses config file)")
    print("  python3 c2client.py <host_ip> 8888    (direct)")

if __name__ == "__main__":
    main()