#!/bin/sh

# BGP Hijacking Lab Script
# This script performs a controlled BGP hijacking simulation for educational purposes

echo "=== BGP Hijacking Lab Starting ==="
echo "$(date): Script initiated"

# Debug: Check Docker access
log "Checking Docker access..."
if docker ps >/dev/null 2>&1; then
    log "✓ Docker access confirmed"
    log "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
else
    log "✗ Docker access failed - this will cause the script to fail"
    exit 1
fi

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1"
}

# Function to execute command on a container via docker exec
exec_on_container() {
    local container=$1
    shift
    docker exec "$container" "$@"
}

# Function to execute vtysh command on FRR container
vtysh_exec() {
    local container=$1
    local cmd=$2
    log "Executing on $container: $cmd"
    
    # Try multiple times with increasing timeouts
    local attempts=0
    local max_attempts=3
    
    while [ $attempts -lt $max_attempts ]; do
        attempts=$((attempts + 1))
        local timeout_val=$((30 + (attempts * 10)))
        
        if timeout $timeout_val docker exec "$container" vtysh -c "$cmd" 2>/dev/null; then
            return 0
        else
            log "Attempt $attempts/$max_attempts failed on $container: $cmd"
            if [ $attempts -lt $max_attempts ]; then
                sleep $((attempts * 5))
            fi
        fi
    done
    
    log "All attempts failed on $container: $cmd"
    return 1
}

# Function to wait for container health or FRR readiness
wait_for_health() {
    local container=$1
    local max_wait=${2:-180}
    local count=0
    
    log "Waiting for $container to be ready..."
    while [ $count -lt $max_wait ]; do
        # Check if container exists first
        if ! docker ps -q --filter "name=^${container}$" >/dev/null 2>&1; then
            log "Container $container not found, waiting..."
            sleep 10
            count=$((count + 10))
            continue
        fi
        
        # For FRR containers, check if vtysh is responding instead of health status
        if echo "$container" | grep -q "as[0-9]"; then
            if timeout 10 docker exec "$container" vtysh -c "show running-config" >/dev/null 2>&1; then
                log "$container FRR is responding"
                return 0
            else
                log "$container FRR not ready yet, waiting... (${count}/${max_wait}s)"
            fi
        else
            local status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
            log "$container status: $status"
            
            if echo "$status" | grep -q "healthy"; then
                log "$container is healthy"
                return 0
            fi
        fi
        
        sleep 10
        count=$((count + 10))
    done
    log "WARNING: $container did not become ready within ${max_wait}s"
    return 1
}

# 1. Wait for topology to build and converge
log "Step 1: Waiting for topology to converge..."

# Wait for all BGP containers to be ready
for container in ashleysequeira-as1000 ashleysequeira-as1337 ashleysequeira-as2000 ashleysequeira-as3000; do
    wait_for_health "$container" 300  # 5 minute timeout for FRR startup
done

# Additional convergence time for BGP
log "Waiting additional 60 seconds for BGP convergence..."
sleep 60

# Alternative check: Try to establish basic connectivity even if health checks failed
log "Performing connectivity validation..."
connectivity_tries=0
max_connectivity_tries=30
while [ $connectivity_tries -lt $max_connectivity_tries ]; do
    if ping -6 -c 1 -W 2 2001:10:10:10::10 >/dev/null 2>&1; then
        log "✓ Basic connectivity established"
        break
    fi
    connectivity_tries=$((connectivity_tries + 1))
    log "Connectivity attempt $connectivity_tries/$max_connectivity_tries failed, retrying..."
    sleep 5
done

# Verify client can ping AS1000
log "Verifying connectivity to AS1000..."
if ping -6 -c 3 -W 5 2001:10:10:10::10 >/dev/null 2>&1; then
    log "✓ Successfully pinged AS1000"
else
    log "✗ Failed to ping AS1000 - topology may not be ready"
    exit 1
fi

# 2. Advertise 2001:99:99:99::/64 from AS3000
log "Step 2: Advertising 2001:99:99:99::/64 from AS3000..."
vtysh_exec ashleysequeira-as3000 "configure terminal"
vtysh_exec ashleysequeira-as3000 "router bgp 3000"
vtysh_exec ashleysequeira-as3000 "address-family ipv6"
vtysh_exec ashleysequeira-as3000 "network 2001:99:99:99::/64"
vtysh_exec ashleysequeira-as3000 "exit"
vtysh_exec ashleysequeira-as3000 "exit"
vtysh_exec ashleysequeira-as3000 "exit"
log "✓ AS3000 now advertising 2001:99:99:99::/64"

# Wait for route propagation
sleep 10

# 3. Start BGP-only packet capture on AS1000
log "Step 3: Starting BGP packet capture on AS1000..."
PCAP_FILE="/outputs/bgp_hijack_$(date '+%Y%m%d_%H%M%S').pcap"
exec_on_container ashleysequeira-as1000 tcpdump -i any -w "$PCAP_FILE" -f "tcp port 179" &
TCPDUMP_PID=$!
log "✓ Packet capture started, output: $PCAP_FILE"

# Give tcpdump time to start
sleep 5

# 4. From AS1337, announce the first 5 /126 subnets inside the /64
log "Step 4: Starting hijack sequence from AS1337..."

# Define the 5 /126 subnets within 2001:99:99:99::/64
HIJACK_SUBNETS="
2001:99:99:99::/126
2001:99:99:99:4::/126
2001:99:99:99:8::/126
2001:99:99:99:c::/126
2001:99:99:99:10::/126
"

# Configure AS1337 for hijacking
vtysh_exec ashleysequeira-as1337 "configure terminal"
vtysh_exec ashleysequeira-as1337 "router bgp 1337"
vtysh_exec ashleysequeira-as1337 "address-family ipv6"

# Announce each subnet with 1 second delay
subnet_count=1
for subnet in $HIJACK_SUBNETS; do
    if [ -n "$subnet" ]; then
        log "Hijacking subnet $subnet_count/5: $subnet"
        vtysh_exec ashleysequeira-as1337 "network $subnet"
        subnet_count=$((subnet_count + 1))
        sleep 1
    fi
done

vtysh_exec ashleysequeira-as1337 "exit"
vtysh_exec ashleysequeira-as1337 "exit"
vtysh_exec ashleysequeira-as1337 "exit"

log "✓ All 5 hijacked subnets announced from AS1337"

# Wait for route propagation
sleep 15

# 5. Show routing table for AS1000 and output to file
log "Step 5: Capturing AS1000 routing table..."
ROUTE_FILE="/outputs/as1000_routing_table_$(date '+%Y%m%d_%H%M%S').txt"

echo "=== AS1000 IPv6 Routing Table - During Hijack ===" > "$ROUTE_FILE"
echo "Timestamp: $(date)" >> "$ROUTE_FILE"
echo "" >> "$ROUTE_FILE"

# Get BGP table
echo "--- BGP IPv6 Table ---" >> "$ROUTE_FILE"
vtysh_exec ashleysequeira-as1000 "show bgp ipv6" >> "$ROUTE_FILE"
echo "" >> "$ROUTE_FILE"

# Get IPv6 routing table
echo "--- IPv6 Routing Table ---" >> "$ROUTE_FILE"
vtysh_exec ashleysequeira-as1000 "show ipv6 route" >> "$ROUTE_FILE"

# Also display on screen
log "AS1000 Routing Table (BGP IPv6):"
vtysh_exec ashleysequeira-as1000 "show bgp ipv6"

log "✓ Routing table saved to $ROUTE_FILE"

# 6. Stop packet capture on AS1000
log "Step 6: Stopping packet capture..."
if [ -n "$TCPDUMP_PID" ]; then
    kill $TCPDUMP_PID 2>/dev/null
    sleep 2
fi
# Also kill any remaining tcpdump processes on AS1000
exec_on_container ashleysequeira-as1000 pkill tcpdump 2>/dev/null || true
log "✓ Packet capture stopped"

# 7. Withdraw hijacked routes and remove original advertisement
log "Step 7: Withdrawing hijacked routes and cleaning up..."

# Withdraw hijacked subnets from AS1337
vtysh_exec ashleysequeira-as1337 "configure terminal"
vtysh_exec ashleysequeira-as1337 "router bgp 1337"
vtysh_exec ashleysequeira-as1337 "address-family ipv6"

for subnet in $HIJACK_SUBNETS; do
    if [ -n "$subnet" ]; then
        log "Withdrawing $subnet from AS1337"
        vtysh_exec ashleysequeira-as1337 "no network $subnet"
    fi
done

vtysh_exec ashleysequeira-as1337 "exit"
vtysh_exec ashleysequeira-as1337 "exit"
vtysh_exec ashleysequeira-as1337 "exit"

# Remove original advertisement from AS3000
log "Removing 2001:99:99:99::/64 advertisement from AS3000"
vtysh_exec ashleysequeira-as3000 "configure terminal"
vtysh_exec ashleysequeira-as3000 "router bgp 3000"
vtysh_exec ashleysequeira-as3000 "address-family ipv6"
vtysh_exec ashleysequeira-as3000 "no network 2001:99:99:99::/64"
vtysh_exec ashleysequeira-as3000 "exit"
vtysh_exec ashleysequeira-as3000 "exit"
vtysh_exec ashleysequeira-as3000 "exit"

log "✓ All hijacked routes withdrawn and original advertisement removed"

# Wait for route withdrawal propagation
sleep 15

# 8. Verify network is back to original state
log "Step 8: Verifying network returned to original state..."

FINAL_ROUTE_FILE="/outputs/as1000_final_routing_table_$(date '+%Y%m%d_%H%M%S').txt"

echo "=== AS1000 IPv6 Routing Table - After Cleanup ===" > "$FINAL_ROUTE_FILE"
echo "Timestamp: $(date)" >> "$FINAL_ROUTE_FILE"
echo "" >> "$FINAL_ROUTE_FILE"

echo "--- BGP IPv6 Table ---" >> "$FINAL_ROUTE_FILE"
vtysh_exec ashleysequeira-as1000 "show bgp ipv6" >> "$FINAL_ROUTE_FILE"
echo "" >> "$FINAL_ROUTE_FILE"

echo "--- IPv6 Routing Table ---" >> "$FINAL_ROUTE_FILE"
vtysh_exec ashleysequeira-as1000 "show ipv6 route" >> "$FINAL_ROUTE_FILE"

log "Final AS1000 Routing Table (BGP IPv6):"
vtysh_exec ashleysequeira-as1000 "show bgp ipv6"

log "✓ Final routing table saved to $FINAL_ROUTE_FILE"

# Verify no hijacked routes remain
if vtysh_exec ashleysequeira-as1000 "show bgp ipv6" | grep -q "2001:99:99:99"; then
    log "⚠ WARNING: Some 2001:99:99:99::/XX routes may still be present"
else
    log "✓ No hijacked routes detected - network appears clean"
fi

# Final connectivity test
if ping -6 -c 3 -W 5 2001:10:10:10::10 >/dev/null 2>&1; then
    log "✓ Final connectivity test to AS1000 successful"
else
    log "⚠ WARNING: Final connectivity test failed"
fi

log "=== BGP Hijacking Lab Complete ==="
log "Files generated:"
log "  - Packet capture: $PCAP_FILE"
log "  - Hijack routing table: $ROUTE_FILE" 
log "  - Final routing table: $FINAL_ROUTE_FILE"

# Keep container running for analysis
log "Container will now sleep indefinitely for post-lab analysis..."
sleep infinity
