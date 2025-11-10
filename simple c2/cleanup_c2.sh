#!/bin/bash

# Malformed Labs C2 Cleanup Script
# Stops all C2 services, kills processes, and cleans up containers

echo "======================================================"
echo "🧹 MALFORMED LABS C2 CLEANUP SCRIPT 🧹"
echo "======================================================"
echo

# Function to print status messages
print_status() {
    echo "🔄 $1"
}

print_success() {
    echo "✅ $1"
}

print_error() {
    echo "❌ $1"
}

# Stop C2 clients in all containers
print_status "Stopping C2 clients in endpoint containers..."

for container in linux_endpoint1 linux_endpoint2 linux_endpoint3; do
    if docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
        print_status "Stopping C2 client in $container..."
        
        # Kill Python processes (C2 clients)
        docker exec $container sh -c "ps aux | grep 'python.*c2client' | grep -v grep | awk '{print \$2}' | xargs kill -9 2>/dev/null || true" 2>/dev/null || true
        
        # Remove C2 client files
        docker exec $container rm -f /tmp/c2client.py /tmp/c2client.log 2>/dev/null || true
        
        print_success "Cleaned up $container"
    else
        print_error "$container is not running"
    fi
done

# Stop C2 server in webserver container
print_status "Stopping C2 server daemon..."

if docker ps --format "table {{.Names}}" | grep -q "^outrun_webserver$"; then
    # Kill C2 server processes
    docker exec outrun_webserver sh -c "ps aux | grep 'python.*c2server_daemon' | grep -v grep | awk '{print \$2}' | xargs kill -9 2>/dev/null || true" 2>/dev/null || true
    
    # Kill any processes using C2 ports
    docker exec outrun_webserver sh -c "netstat -tlnp 2>/dev/null | grep -E ':888[89]' | awk '{print \$NF}' | cut -d'/' -f1 | xargs kill -9 2>/dev/null || true" 2>/dev/null || true
    
    # Remove C2 server files
    docker exec outrun_webserver rm -f /tmp/c2server_daemon.py /tmp/c2server_daemon.log /tmp/c2console.py 2>/dev/null || true
    
    print_success "Stopped C2 server daemon"
else
    print_error "outrun_webserver is not running"
fi

# Stop and remove all containers
print_status "Stopping all lab containers..."

# Get the directory of docker-compose.yml
COMPOSE_DIR="/Users/maladmin/Documents/GitHub/outrunc2/client lab setup"

if [ -f "$COMPOSE_DIR/docker-compose.yaml" ]; then
    cd "$COMPOSE_DIR"
    docker-compose down --remove-orphans 2>/dev/null || true
    print_success "Stopped all containers with docker-compose"
else
    # Fallback: stop containers individually
    for container in outrun_webserver linux_endpoint1 linux_endpoint2 linux_endpoint3; do
        if docker ps -a --format "table {{.Names}}" | grep -q "^${container}$"; then
            docker stop $container 2>/dev/null || true
            docker rm $container 2>/dev/null || true
            print_success "Stopped and removed $container"
        fi
    done
fi

# Remove C2 network if it exists
print_status "Cleaning up Docker networks..."
if docker network ls | grep -q "client_lab_setup_outrun_net"; then
    docker network rm client_lab_setup_outrun_net 2>/dev/null || true
    print_success "Removed client_lab_setup_outrun_net network"
fi

# Clean up any dangling processes on host
print_status "Cleaning up local processes..."
pkill -f "c2console.py" 2>/dev/null || true
pkill -f "c2server.py" 2>/dev/null || true

# Remove temporary files
print_status "Cleaning up temporary files..."
rm -f /tmp/c2*.log /tmp/c2*.pid 2>/dev/null || true

# Show final status
print_status "Checking cleanup status..."

echo
echo "📊 CLEANUP SUMMARY:"
echo "├─ Running containers: $(docker ps --format "table {{.Names}}" | grep -E "(endpoint|webserver)" | wc -l | tr -d ' ')"
echo "├─ C2 related processes: $(ps aux | grep -E "(c2server|c2client|c2console)" | grep -v grep | wc -l | tr -d ' ')"
echo "└─ Open ports 8888/8889: $(netstat -tln 2>/dev/null | grep -E ':888[89]' | wc -l | tr -d ' ')"

echo
print_success "C2 infrastructure cleanup complete!"
echo

echo "🚀 NEXT STEPS:"
echo "1. cd '/Users/maladmin/Documents/GitHub/outrunc2/client lab setup'"
echo "2. docker-compose up -d"
echo "3. cd '../simple c2' && ./deploy_c2.sh"
echo "4. Test with: python3 c2console.py localhost 8889"
echo

echo "======================================================"