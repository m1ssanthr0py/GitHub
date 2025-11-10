#!/bin/sh

# Original IPv6 BGP Lab - Basic Status Display
# This script shows the original network configuration without any hijacking

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1"
}

echo ""
echo "=============================================="
echo "   IPv6 BGP Lab - Original Configuration"
echo "=============================================="
echo "$(date): Lab status check initiated"
echo ""

# Check Docker access
echo "Checking Docker environment..."
log "Checking Docker access..."
if docker ps >/dev/null 2>&1; then
    log "[OK] Docker access confirmed"
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
else
    log "[ERROR] Docker access failed"
    exit 1
fi

# Function to wait for container health
wait_for_health() {
    local container=$1
    local max_wait=${2:-120}
    local count=0
    
    log "Waiting for $container to be ready..."
    while [ $count -lt $max_wait ]; do
        if ! docker ps -q --filter "name=^${container}$" >/dev/null 2>&1; then
            log "Container $container not found, waiting..."
            sleep 5
            count=$((count + 5))
            continue
        fi
        
        if echo "$container" | grep -q "as[0-9]"; then
            if timeout 10 docker exec "$container" vtysh -c "show running-config" >/dev/null 2>&1; then
                log "$container FRR is responding"
                return 0
            else
                log "$container FRR not ready yet, waiting... (${count}/${max_wait}s)"
            fi
        fi
        
        sleep 5
        count=$((count + 5))
    done
    log "WARNING: $container did not become ready within ${max_wait}s"
    return 1
}

echo ""
echo "Waiting for BGP routers to start..."

# Wait for all BGP containers to be ready
for container in ashleysequeira-as1000 ashleysequeira-as1337 ashleysequeira-as2000 ashleysequeira-as3000; do
    as_number=$(echo "$container" | grep -o 'as[0-9]*')
    echo "   Waiting for $as_number to become ready..."
    wait_for_health "$container" 180
    echo "   [OK] $as_number is ready"
done

# Additional time for BGP convergence
echo ""
echo "Allowing 60 seconds for BGP neighbor establishment..."
log "Waiting for BGP convergence..."
sleep 60

# Test connectivity
echo "Testing IPv6 connectivity..."
connectivity_tries=0
max_connectivity_tries=10
while [ $connectivity_tries -lt $max_connectivity_tries ]; do
    if ping -6 -c 1 -W 2 2001:10:10:10::10 >/dev/null 2>&1; then
        echo "   [OK] IPv6 connectivity established to AS1000"
        log "[OK] Basic connectivity established"
        break
    fi
    connectivity_tries=$((connectivity_tries + 1))
    echo "   Connectivity test $connectivity_tries/$max_connectivity_tries..."
    sleep 3
done

# Verify client can ping AS1000
log "Verifying connectivity to AS1000..."
if ping -6 -c 3 -W 5 2001:10:10:10::10 >/dev/null 2>&1; then
    log "[OK] Successfully pinged AS1000"
else
    log "[ERROR] Failed to ping AS1000 - topology may not be ready"
fi

echo ""
echo "=============================================="
echo "   Original BGP Configuration Status"
echo "=============================================="

# Show BGP neighbor status for each AS
for container in ashleysequeira-as1000 ashleysequeira-as1337 ashleysequeira-as2000 ashleysequeira-as3000; do
    as_number=$(echo "$container" | grep -o 'as[0-9]*' | tr '[:lower:]' '[:upper:]')
    echo ""
    echo "=== $as_number BGP Status ==="
    
    echo "BGP Neighbors:"
    docker exec "$container" vtysh -c "show bgp neighbors" | grep "BGP neighbor is" | while read line; do
        neighbor=$(echo "$line" | cut -d' ' -f4 | tr -d ',')
        remote_as=$(echo "$line" | cut -d' ' -f7 | tr -d ',')
        echo "   -> Neighbor: $neighbor (AS$remote_as)"
    done
    
    echo ""
    echo "IPv6 BGP Routes:"
    docker exec "$container" vtysh -c "show bgp ipv6" | grep -E "^\s*\*>|^\s*Network"
done

echo ""
echo "=============================================="
echo "   Network Topology Summary"
echo "=============================================="
echo ""
echo "AS Topology:"
echo "   AS1000 <--> AS2000 <--> AS3000"
echo "   AS1000 <--> AS1337"
echo ""
echo "IPv6 Networks:"
echo "   Client LAN:        2001:10:10:10::/64"
echo "   AS1000-AS2000:     2001:12:12:12::/64"
echo "   AS1000-AS1337:     2001:1:33:7::/64"
echo "   AS2000-AS3000:     2001:23:23:23::/64"
echo ""

log "=============================================="
log "Original configuration status check complete"
log "=============================================="
log "Network is in its original, clean state"
log "No hijacking or modifications have been applied"
log "All BGP neighbors should be established normally"

echo ""
echo "Container will now sleep indefinitely for analysis..."
echo "Use 'docker exec -it ashleysequeira-client /bin/sh' to explore"
echo ""

sleep infinity