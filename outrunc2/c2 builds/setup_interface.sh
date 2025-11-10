#!/usr/bin/env bash
# Simple Network Interface Creation Script (Non-interactive)
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

# Default values
INTERFACE_NAME="${1:-test0}"
IP_ADDRESS="${2:-192.168.200.1/24}"
INTERFACE_TYPE="${3:-dummy}"

print_status "Creating network interface: $INTERFACE_NAME"
print_status "IP Address: $IP_ADDRESS" 
print_status "Interface Type: $INTERFACE_TYPE"

# Check if we have sufficient privileges
if [ "$EUID" -ne 0 ]; then
    print_warning "Not running as root - some operations may fail"
fi

# Function to create dummy interface (works without special hardware)
create_dummy_interface() {
    local name="$1"
    local ip="$2"
    
    print_status "Creating dummy interface: $name"
    
    # Load dummy module if available
    modprobe dummy 2>/dev/null || print_warning "Could not load dummy module"
    
    # Create dummy interface
    if ip link add "$name" type dummy 2>/dev/null; then
        print_success "Dummy interface $name created"
    else
        print_error "Failed to create dummy interface"
        return 1
    fi
    
    # Bring interface up
    if ip link set dev "$name" up 2>/dev/null; then
        print_success "Interface $name brought up"
    else
        print_error "Failed to bring interface up"
        return 1
    fi
    
    # Assign IP address
    if ip addr add "$ip" dev "$name" 2>/dev/null; then
        print_success "IP address $ip assigned to $name"
    else
        print_error "Failed to assign IP address"
        return 1
    fi
    
    # Show interface status
    print_status "Interface status:"
    ip addr show "$name" 2>/dev/null || true
}

# Function to create bridge interface
create_bridge_interface() {
    local name="$1"
    local ip="$2"
    
    print_status "Creating bridge interface: $name"
    
    # Create bridge
    if ip link add name "$name" type bridge 2>/dev/null; then
        print_success "Bridge interface $name created"
    else
        print_error "Failed to create bridge interface"
        return 1
    fi
    
    # Bring interface up
    if ip link set dev "$name" up 2>/dev/null; then
        print_success "Interface $name brought up"
    else
        print_error "Failed to bring interface up"
        return 1
    fi
    
    # Assign IP address
    if ip addr add "$ip" dev "$name" 2>/dev/null; then
        print_success "IP address $ip assigned to $name"
    else
        print_error "Failed to assign IP address"
        return 1
    fi
    
    # Show interface status
    print_status "Interface status:"
    ip addr show "$name" 2>/dev/null || true
}

# Function to create TAP interface
create_tap_interface() {
    local name="$1"
    local ip="$2"
    
    print_status "Creating TAP interface: $name"
    
    # Create TAP interface
    if ip tuntap add dev "$name" mode tap 2>/dev/null; then
        print_success "TAP interface $name created"
    else
        print_error "Failed to create TAP interface"
        return 1
    fi
    
    # Bring interface up
    if ip link set dev "$name" up 2>/dev/null; then
        print_success "Interface $name brought up"
    else
        print_error "Failed to bring interface up"
        return 1
    fi
    
    # Assign IP address
    if ip addr add "$ip" dev "$name" 2>/dev/null; then
        print_success "IP address $ip assigned to $name"
    else
        print_error "Failed to assign IP address"
        return 1
    fi
    
    # Show interface status
    print_status "Interface status:"
    ip addr show "$name" 2>/dev/null || true
}

# Function to configure existing interface
configure_existing_interface() {
    local name="$1"
    local ip="$2"
    
    print_status "Configuring existing interface: $name"
    
    # Check if interface exists
    if ! ip link show "$name" &>/dev/null; then
        print_error "Interface $name does not exist"
        return 1
    fi
    
    # Bring interface up
    if ip link set dev "$name" up 2>/dev/null; then
        print_success "Interface $name brought up"
    else
        print_warning "Could not bring interface up"
    fi
    
    # Add IP address (don't flush existing ones)
    if ip addr add "$ip" dev "$name" 2>/dev/null; then
        print_success "IP address $ip added to $name"
    else
        print_warning "Could not add IP address (may already exist)"
    fi
    
    # Show interface status
    print_status "Interface status:"
    ip addr show "$name" 2>/dev/null || true
}

# Main execution
case "$INTERFACE_TYPE" in
    "dummy")
        create_dummy_interface "$INTERFACE_NAME" "$IP_ADDRESS"
        ;;
    "bridge")
        create_bridge_interface "$INTERFACE_NAME" "$IP_ADDRESS"
        ;;
    "tap")
        create_tap_interface "$INTERFACE_NAME" "$IP_ADDRESS"
        ;;
    "config")
        configure_existing_interface "$INTERFACE_NAME" "$IP_ADDRESS"
        ;;
    *)
        print_status "Unknown interface type '$INTERFACE_TYPE', defaulting to dummy"
        create_dummy_interface "$INTERFACE_NAME" "$IP_ADDRESS"
        ;;
esac

# Test the interface
print_status "Testing interface connectivity..."
if ping -c 1 -W 1 "${IP_ADDRESS%/*}" &>/dev/null; then
    print_success "Interface is responding to ping"
else
    print_warning "Interface ping test failed"
fi

# Show routing table
print_status "Current routing table:"
ip route show 2>/dev/null || route -n 2>/dev/null || print_warning "Could not show routes"

# Enable IP forwarding if running as root
if [ "$EUID" -eq 0 ]; then
    print_status "Enabling IP forwarding..."
    echo 1 > /proc/sys/net/ipv4/ip_forward 2>/dev/null || print_warning "Could not enable IP forwarding"
    print_success "IP forwarding enabled"
fi

print_success "Network interface setup completed!"

# Usage information
print_status "Usage examples:"
echo "  $0                                    # Creates test0 dummy interface with 192.168.200.1/24"
echo "  $0 myif 10.0.0.1/24 bridge          # Creates bridge interface"
echo "  $0 tap1 172.16.1.1/24 tap           # Creates TAP interface" 
echo "  $0 eth0 192.168.1.100/24 config     # Configures existing interface"