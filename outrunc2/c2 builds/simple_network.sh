#!/usr/bin/env bash
# Simple Network Interface Setup Script (Works without special modules)
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Simple Network Interface Setup"
print_status "Working with existing interfaces..."

# Find available network interfaces
print_status "Available network interfaces:"
INTERFACES=$(ip link show | grep -E "^[0-9]+:" | awk -F': ' '{print $2}' | grep -v lo)

for iface in $INTERFACES; do
    echo "  - $iface"
done

# Try to find a working interface that's not loopback
WORKING_INTERFACE=""
for iface in $INTERFACES; do
    if ip link show "$iface" | grep -q "UP"; then
        WORKING_INTERFACE="$iface"
        break
    fi
done

if [ -z "$WORKING_INTERFACE" ]; then
    # No UP interface found, try to bring one up
    for iface in $INTERFACES; do
        print_status "Attempting to bring up interface: $iface"
        if ip link set dev "$iface" up 2>/dev/null; then
            WORKING_INTERFACE="$iface"
            print_success "Interface $iface brought up"
            break
        fi
    done
fi

if [ -z "$WORKING_INTERFACE" ]; then
    print_error "No working network interface found"
    exit 1
fi

print_success "Using interface: $WORKING_INTERFACE"

# Create a virtual interface using namespace (if supported)
VETH_NAME="veth-test"
VETH_PEER="veth-peer"

print_status "Attempting to create virtual ethernet pair..."

if ip link add "$VETH_NAME" type veth peer name "$VETH_PEER" 2>/dev/null; then
    print_success "Virtual ethernet pair created: $VETH_NAME <-> $VETH_PEER"
    
    # Bring up both interfaces
    ip link set dev "$VETH_NAME" up
    ip link set dev "$VETH_PEER" up
    
    # Assign IP addresses
    ip addr add 192.168.100.1/30 dev "$VETH_NAME" 2>/dev/null || print_warning "Could not assign IP to $VETH_NAME"
    ip addr add 192.168.100.2/30 dev "$VETH_PEER" 2>/dev/null || print_warning "Could not assign IP to $VETH_PEER"
    
    print_success "Virtual network created successfully!"
    
    # Show the interfaces
    print_status "Virtual interface status:"
    ip addr show "$VETH_NAME" 2>/dev/null || true
    ip addr show "$VETH_PEER" 2>/dev/null || true
    
    # Test connectivity
    print_status "Testing connectivity between virtual interfaces..."
    if ping -c 1 -W 1 192.168.100.2 &>/dev/null; then
        print_success "Virtual network connectivity test passed!"
    else
        print_warning "Connectivity test failed"
    fi
    
else
    print_warning "Could not create virtual ethernet pair"
    print_status "Working with existing interface: $WORKING_INTERFACE"
    
    # Just configure the existing interface with an additional IP
    TEST_IP="192.168.99.100/24"
    print_status "Adding test IP $TEST_IP to $WORKING_INTERFACE"
    
    if ip addr add "$TEST_IP" dev "$WORKING_INTERFACE" 2>/dev/null; then
        print_success "Test IP added successfully"
        
        # Test the new IP
        if ping -c 1 -W 1 192.168.99.100 &>/dev/null; then
            print_success "Test IP is responding"
        else
            print_warning "Test IP ping failed"
        fi
    else
        print_warning "Could not add test IP (may already exist)"
    fi
fi

# Show all interface status
print_status "Current network configuration:"
ip addr show | grep -E "(inet |UP|DOWN)" | head -20

# Show routing
print_status "Routing table:"
ip route show | head -10

# Test external connectivity if possible
print_status "Testing external connectivity..."
if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    print_success "External connectivity OK"
elif ping -c 1 -W 2 1.1.1.1 &>/dev/null; then
    print_success "External connectivity OK (via 1.1.1.1)"
else
    print_warning "External connectivity test failed"
fi

# Create a simple network namespace test if supported
print_status "Testing network namespace support..."
NS_NAME="test-ns"

if ip netns add "$NS_NAME" 2>/dev/null; then
    print_success "Network namespace '$NS_NAME' created"
    
    # Create loopback in namespace
    ip netns exec "$NS_NAME" ip link set dev lo up
    
    # Test namespace
    if ip netns exec "$NS_NAME" ping -c 1 127.0.0.1 &>/dev/null; then
        print_success "Network namespace is functional"
    fi
    
    # Cleanup namespace
    ip netns delete "$NS_NAME" 2>/dev/null || true
    print_status "Cleaned up test namespace"
else
    print_warning "Network namespace creation not supported or insufficient privileges"
fi

print_success "Network interface setup completed!"

# Show summary
echo ""
print_status "=== SUMMARY ==="
print_status "Available tools:"
for tool in ip ping netstat ss iptables nmap curl wget; do
    if command -v "$tool" &>/dev/null; then
        print_success "$tool: available"
    else
        print_warning "$tool: not found"
    fi
done

print_status "Network setup complete. You now have working network interfaces for testing."