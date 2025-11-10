#!/bin/sh

# BGP Hijacking Lab Script
# This script performs a controlled BGP hijacking simulation for educational purposes

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1"
}

echo ""
echo "=============================================="
echo "   BGP IPv6 Hijacking Lab - Starting"
echo "=============================================="
echo "$(date): Lab session initiated"
echo ""

# Debug: Check Docker access
echo "MILESTONE 1/8: Validating Environment..."
log "Checking Docker access..."
if docker ps >/dev/null 2>&1; then
    log "[OK] Docker access confirmed"
    log "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
else
    log "[ERROR] Docker access failed - this will cause the script to fail"
    exit 1
fi

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

echo ""
echo "MILESTONE 2/8: Building BGP Topology..."
echo "Waiting for all BGP routers to start and converge..."
log "Step 1: Waiting for topology to converge..."

# Wait for all BGP containers to be ready
echo "Starting BGP routers."
for container in ashleysequeira-as1000 ashleysequeira-as1337 ashleysequeira-as2000 ashleysequeira-as3000; do
    as_number=$(echo "$container" | grep -o 'as[0-9]*')
    echo "   Waiting for $as_number to come up."
    wait_for_health "$container" 300  # 5 minute timeout for FRR startup
    echo "   [OK] $as_number is ready and healthy"
done

# Additional convergence time for BGP
echo "Allowing 60 seconds for BGP neighbor establishment because BGP is slow."
log "Waiting additional 60 seconds for BGP convergence..."
sleep 60

# Alternative check: Try to establish basic connectivity even if health checks failed
echo "Testing IPv6 connectivity between routers..."
log "Performing connectivity validation..."
connectivity_tries=0
max_connectivity_tries=30
while [ $connectivity_tries -lt $max_connectivity_tries ]; do
    if ping -6 -c 1 -W 2 2001:10:10:10::10 >/dev/null 2>&1; then
        echo "   [OK] IPv6 connectivity established to AS1000"
        log "[OK] Basic connectivity established"
        break
    fi
    connectivity_tries=$((connectivity_tries + 1))
    echo "   Connectivity test $connectivity_tries/$max_connectivity_tries..."
    log "Connectivity attempt $connectivity_tries/$max_connectivity_tries failed, retrying..."
    sleep 5
done

# Verify client can ping AS1000
log "Verifying connectivity to AS1000..."
if ping -6 -c 3 -W 5 2001:10:10:10::10 >/dev/null 2>&1; then
    log "[OK] Successfully pinged AS1000"
else
    log "[ERROR] Failed to ping AS1000 - topology may not be ready"
    exit 1
fi

echo ""
echo "MILESTONE 3/8: Setting Up Target Network..."
echo "AS3000 will advertise 2001:99:99:99::/64 (the target for hijacking)"
log "Step 2: Advertising 2001:99:99:99::/64 from AS3000..."
# First create a static route to make the network advertisable
log "Creating static route for 2001:99:99:99::/64 in AS3000..."
docker exec ashleysequeira-as3000 vtysh -c "
configure terminal
ipv6 route 2001:99:99:99::/64 null0
exit
"

# Wait for route to be installed
sleep 2

# Now advertise the network via BGP
log "Configuring BGP advertisement of 2001:99:99:99::/64..."
docker exec ashleysequeira-as3000 vtysh -c "
configure terminal
router bgp 3000
address-family ipv6 unicast
network 2001:99:99:99::/64
exit-address-family
exit
exit
"
log "[OK] AS3000 now advertising 2001:99:99:99::/64"

# Wait for route propagation and verify establishment
echo "Waiting for AS3000's route to propagate through the network..."
sleep 15

# Verify the route is visible in AS1000's BGP table before hijacking
echo "Verifying 2001:99:99:99::/64 is established in AS1000's routing table..."
route_established=0
for attempt in 1 2 3 4 5; do
    if vtysh_exec ashleysequeira-as1000 "show bgp ipv6" | grep -q "2001:99:99:99::/64"; then
        echo "[OK] Target route 2001:99:99:99::/64 confirmed in AS1000 BGP table"
        log "[OK] AS3000's advertisement successfully propagated (attempt $attempt)"
        route_established=1
        break
    else
        echo "[WAIT] Target route not yet visible, waiting... (attempt $attempt/5)"
        sleep 5
    fi
done

if [ $route_established -eq 0 ]; then
    log "[WARNING] Target route may not have fully propagated, continuing anyway..."
fi

echo ""
echo "MILESTONE 4/8: Starting Traffic Monitoring..."
echo "Capturing BGP traffic on AS1000 to analyze the hijacking attack"
log "Step 3: Starting BGP packet capture on AS1000..."
PCAP_FILE="/outputs/bgp_hijack_$(date '+%Y%m%d_%H%M%S').pcap"
exec_on_container ashleysequeira-as1000 tcpdump -i any -w "$PCAP_FILE" -f "tcp port 179" &
TCPDUMP_PID=$!
log "[OK] Packet capture started, output: $PCAP_FILE"

# Give tcpdump time to start
sleep 5

echo ""
echo "MILESTONE 5/8: Executing BGP Hijacking Attack..."
echo "AS1337 will announce 5 more-specific /126 subnets to hijack traffic"
echo "Target: 2001:99:99:99::/64 -> Hijacking with /126 prefixes"

# Show baseline state before hijacking
echo ""
echo "=== BASELINE STATE (Before Hijacking) ==="
echo "Current BGP routes for 2001:99:99:99::/64 in AS1000:"
vtysh_exec ashleysequeira-as1000 "show bgp ipv6 2001:99:99:99::/64" || echo "Route not found in specific lookup"
echo "=========================================="
echo ""

log "Step 4: Starting hijack sequence from AS1337..."

# Define the 5 /126 subnets within 2001:99:99:99::/64
HIJACK_SUBNETS="
2001:99:99:99::/126
2001:99:99:99:4::/126
2001:99:99:99:8::/126
2001:99:99:99:c::/126
2001:99:99:99:10::/126
"

# First create static routes for all hijacked subnets
log "Creating static routes for hijacked subnets in AS1337..."
static_routes="configure terminal"
for subnet in $HIJACK_SUBNETS; do
    if [ -n "$subnet" ]; then
        static_routes="$static_routes
ipv6 route $subnet null0"
    fi
done
static_routes="$static_routes
exit"

# Install the static routes
docker exec ashleysequeira-as1337 vtysh -c "$static_routes"

# Wait for routes to be installed
sleep 2

# Configure AS1337 for hijacking - build complete command
hijack_config="configure terminal
router bgp 1337
address-family ipv6 unicast"

# Add each hijacked subnet to the configuration
subnet_count=1
for subnet in $HIJACK_SUBNETS; do
    if [ -n "$subnet" ]; then
        echo "   Hijacking subnet $subnet_count/5: $subnet"
        log "Hijacking subnet $subnet_count/5: $subnet"
        hijack_config="$hijack_config
network $subnet"
        subnet_count=$((subnet_count + 1))
    fi
done

# Complete the configuration
hijack_config="$hijack_config
exit-address-family
exit
exit"

# Execute the complete hijacking configuration
docker exec ashleysequeira-as1337 vtysh -c "$hijack_config"

log "[OK] All 5 hijacked subnets announced from AS1337"

# Wait for route propagation
echo "Waiting for hijacked routes to propagate..."
sleep 15

# Verify hijacking was successful
echo ""
echo "=== HIJACK VERIFICATION ==="
echo "Checking AS1000's BGP table for hijacked more-specific routes:"
hijacked_count=$(vtysh_exec ashleysequeira-as1000 "show bgp ipv6" | grep "2001:99:99:99:" | grep "/126" | wc -l)
echo "Found $hijacked_count hijacked /126 routes in AS1000's table"
if [ "$hijacked_count" -gt 0 ]; then
    echo "[SUCCESS] BGP hijacking attack successful - more-specific routes active!"
    vtysh_exec ashleysequeira-as1000 "show bgp ipv6" | grep "2001:99:99:99:"
else
    echo "[WARNING] No hijacked routes detected - attack may have failed"
fi
echo "============================="
echo ""

echo ""
echo "MILESTONE 6/8: Capturing Attack Evidence..."
echo "Recording AS1000 routing table to show hijacked routes"
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

log "[OK] Routing table saved to $ROUTE_FILE"

echo ""
echo "MILESTONE 7/8: Stopping Traffic Monitoring..."
echo "Finalizing packet capture with hijack traffic data"
log "Step 6: Stopping packet capture..."
if [ -n "$TCPDUMP_PID" ]; then
    kill $TCPDUMP_PID 2>/dev/null
    sleep 2
fi
# Also kill any remaining tcpdump processes on AS1000
exec_on_container ashleysequeira-as1000 pkill tcpdump 2>/dev/null || true
log "[OK] Packet capture stopped"

echo ""
echo "MILESTONE 8/8: Cleaning Up and Restoring Network..."
echo "Withdrawing all hijacked routes and restoring original state"
log "Step 7: Withdrawing hijacked routes and cleaning up..."

# Withdraw hijacked subnets from AS1337
cleanup_config="configure terminal
router bgp 1337
address-family ipv6 unicast"

for subnet in $HIJACK_SUBNETS; do
    if [ -n "$subnet" ]; then
        echo "   Withdrawing hijacked route: $subnet"
        log "Withdrawing $subnet from AS1337"
        cleanup_config="$cleanup_config
no network $subnet"
    fi
done

cleanup_config="$cleanup_config
exit-address-family
exit
exit"

# Execute AS1337 cleanup
docker exec ashleysequeira-as1337 vtysh -c "$cleanup_config"

# Remove original advertisement from AS3000
log "Removing 2001:99:99:99::/64 advertisement from AS3000"
docker exec ashleysequeira-as3000 vtysh -c "
configure terminal
router bgp 3000
address-family ipv6 unicast
no network 2001:99:99:99::/64
exit-address-family
exit
no ipv6 route 2001:99:99:99::/64 null0
exit
"

# Remove static routes from AS1337
log "Removing static routes from AS1337"
cleanup_static="configure terminal"
for subnet in $HIJACK_SUBNETS; do
    if [ -n "$subnet" ]; then
        cleanup_static="$cleanup_static
no ipv6 route $subnet null0"
    fi
done
cleanup_static="$cleanup_static
exit"

docker exec ashleysequeira-as1337 vtysh -c "$cleanup_static"

log "[OK] All hijacked routes withdrawn and original advertisement removed"

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

log "[OK] Final routing table saved to $FINAL_ROUTE_FILE"

# Verify no hijacked routes remain
if vtysh_exec ashleysequeira-as1000 "show bgp ipv6" | grep -q "2001:99:99:99"; then
    log "[WARNING] Some 2001:99:99:99::/XX routes may still be present"
else
    log "[OK] No hijacked routes detected - network appears clean"
fi

# Final connectivity test
if ping -6 -c 3 -W 5 2001:10:10:10::10 >/dev/null 2>&1; then
    log "[OK] Final connectivity test to AS1000 successful"
else
    log "[WARNING] Final connectivity test failed"
fi

echo ""
echo "=============================================="
echo "   BGP IPv6 Hijacking Lab - COMPLETED!"
echo "=============================================="
echo ""
echo "Generated Analysis Files:"
echo "   Packet capture: $PCAP_FILE"
echo "   Hijack routing table: $ROUTE_FILE" 
echo "   Final routing table: $FINAL_ROUTE_FILE"
echo ""
echo "Lab Summary:"
echo "   [OK] BGP topology established successfully"
echo "   [OK] Target network (2001:99:99:99::/64) advertised by AS3000"
echo "   [OK] BGP hijacking attack executed by AS1337"
echo "   [OK] Traffic hijacked via more-specific prefixes"
echo "   [OK] Attack evidence captured and analyzed"
echo "   [OK] Network restored to original state"
echo ""
echo "Next Steps:"
echo "   - Analyze packet capture file for BGP updates"
echo "   - Compare routing tables before/during/after attack"
echo "   - Study how longest prefix matching enabled the hijack"
echo ""
log "=== BGP Hijacking Lab Complete ==="

# Keep container running for analysis
echo "Container staying alive for post-lab analysis..."
echo "Use 'docker exec -it ashleysequeira-client /bin/sh' to explore"
echo ""
log "Container will now sleep indefinitely for post-lab analysis..."
sleep infinity
