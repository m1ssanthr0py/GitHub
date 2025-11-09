import os
import subprocess
import time
import yaml

#!/usr/bin/env python3

def create_docker_compose():
    """Create a docker-compose.yml file with Alpine containers"""
    compose_config = {
        'version': '3.8',
        'services': {
            'alpine1': {
                'build': {
                    'context': '.',
                    'dockerfile': 'Dockerfile.alpine'
                },
                'container_name': 'alpine_container_1',
                'networks': ['bridge_network'],
                'command': 'sleep infinity'
            },
            'alpine2': {
                'build': {
                    'context': '.',
                    'dockerfile': 'Dockerfile.alpine'
                },
                'container_name': 'alpine_container_2',
                'networks': ['bridge_network'],
                'command': 'sleep infinity'
            }
        },
        'networks': {
            'bridge_network': {
                'driver': 'bridge',
                'ipam': {
                    'config': [
                        {'subnet': '172.20.0.0/16'}
                    ]
                }
            }
        }
    }
    
    with open('docker-compose.yml', 'w') as f:
        yaml.dump(compose_config, f, default_flow_style=False)
    
    print("✓ docker-compose.yml created")

def create_dockerfile():
    """Create Dockerfile for Alpine Linux"""
    dockerfile_content = """FROM alpine:latest

RUN apk update && apk add --no-cache \
    iputils \
    net-tools \
    curl \
    bash

WORKDIR /app
CMD ["sleep", "infinity"]
"""
    
    with open('Dockerfile.alpine', 'w') as f:
        f.write(dockerfile_content)
    
    print("✓ Dockerfile.alpine created")

def run_command(cmd, description):
    """Run shell command and return result"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True, result.stdout
        else:
            print(f"✗ {description} failed: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"✗ Error during {description}: {str(e)}")
        return False, str(e)

def ping_test():
    """Perform ping tests between containers"""
    print("\n" + "="*50)
    print("PING TEST RESULTS")
    print("="*50)
    
    containers = ['alpine_container_1', 'alpine_container_2']
    
    for i, source in enumerate(containers):
        for j, target in enumerate(containers):
            if i != j:
                cmd = f"docker exec {source} ping -c 3 {target}"
                success, output = run_command(cmd, f"Ping from {source} to {target}")
                
                if success:
                    # Extract ping statistics
                    lines = output.split('\n')
                    for line in lines:
                        if 'packets transmitted' in line:
                            print(f"📊 {source} → {target}: {line.strip()}")
                        elif 'round-trip' in line or 'rtt' in line:
                            print(f"⏱️  Timing: {line.strip()}")
                else:
                    print(f"❌ Ping failed from {source} to {target}")
                print("-" * 40)

def get_container_ips():
    """Get and display container IP addresses"""
    print("\n📍 Container IP Addresses:")
    containers = ['alpine_container_1', 'alpine_container_2']
    
    for container in containers:
        cmd = f"docker inspect -f '{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}' {container}"
        success, ip = run_command(cmd, f"Getting IP for {container}")
        if success:
            print(f"   {container}: {ip.strip()}")

def main():
    print("🐳 Docker Alpine Lab Setup")
    print("="*40)
    
    # Create necessary files
    create_dockerfile()
    create_docker_compose()
    
    # Build and start containers
    run_command("docker-compose down", "Stopping existing containers")
    run_command("docker-compose build", "Building Alpine images")
    run_command("docker-compose up -d", "Starting containers")
    
    # Wait for containers to be ready
    print("\n⏳ Waiting for containers to be ready...")
    time.sleep(5)
    
    # Get container information
    get_container_ips()
    
    # Run ping tests
    ping_test()
    
    print("\n🎉 Lab setup complete!")
    print("💡 To clean up, run: docker-compose down")

if __name__ == "__main__":
    main()