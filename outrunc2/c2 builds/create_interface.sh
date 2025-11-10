#!/usr/bin/env bash
# Network Interface Creation and Configuration Script
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

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root for interface creation"
        print_status "Try: sudo $0"
        exit 1
    fi
}

# Function to create a bridge interface
create_bridge() {
    local bridge_name="${1:-br0}"
    local ip_addr="${2:-192.168.100.1/24}"
    
    print_status "Creating bridge interface: $bridge_name"
    
    # Create bridge
    if command -v brctl &> /dev/null; then
        brctl addbr "$bridge_name" || print_error "Failed to create bridge with brctl"
    elif command -v ip &> /dev/null; then
        ip link add name "$bridge_name" type bridge || print_error "Failed to create bridge with ip"
    else
        print_error "Neither brctl nor ip command available"
        return 1
    fi
    
    # Bring interface up
    ip link set dev "$bridge_name" up
    
    # Assign IP address
    if [ ! -z "$ip_addr" ]; then
        ip addr add "$ip_addr" dev "$bridge_name"
        print_success "Bridge $bridge_name created with IP $ip_addr"
    else
        print_success "Bridge $bridge_name created without IP"
    fi
}

# Function to create a TAP interface
create_tap() {
    local tap_name="${1:-tap0}"
    local ip_addr="${2:-192.168.101.1/24}"
    
    print_status "Creating TAP interface: $tap_name"
    
    if command -v tunctl &> /dev/null; then
        tunctl -t "$tap_name" -u $(whoami)
    elif command -v ip &> /dev/null; then
        ip tuntap add dev "$tap_name" mode tap
    else
        print_error "Neither tunctl nor ip tuntap available"
        return 1
    fi
    
    # Bring interface up
    ip link set dev "$tap_name" up
    
    # Assign IP address
    if [ ! -z "$ip_addr" ]; then
        ip addr add "$ip_addr" dev "$tap_name"
        print_success "TAP interface $tap_name created with IP $ip_addr"
    else
        print_success "TAP interface $tap_name created without IP"
    fi
}

# Function to create a TUN interface
create_tun() {
    local tun_name="${1:-tun0}"
    local ip_addr="${2:-10.0.0.1/24}"
    
    print_status "Creating TUN interface: $tun_name"
    
    if command -v tunctl &> /dev/null; then
        tunctl -t "$tun_name" -u $(whoami)
    elif command -v ip &> /dev/null; then
        ip tuntap add dev "$tun_name" mode tun
    else
        print_error "Neither tunctl nor ip tuntap available"
        return 1
    fi
    
    # Bring interface up
    ip link set dev "$tun_name" up
    
    # Assign IP address
    if [ ! -z "$ip_addr" ]; then
        ip addr add "$ip_addr" dev "$tun_name"
        print_success "TUN interface $tun_name created with IP $ip_addr"
    else
        print_success "TUN interface $tun_name created without IP"
    fi
}

# Function to create a VLAN interface
create_vlan() {
    local parent_interface="${1:-eth0}"
    local vlan_id="${2:-100}"
    local ip_addr="${3:-192.168.${vlan_id}.1/24}"
    local vlan_name="${parent_interface}.${vlan_id}"
    
    print_status "Creating VLAN interface: $vlan_name on $parent_interface"
    
    # Check if parent interface exists
    if ! ip link show "$parent_interface" &>/dev/null; then
        print_error "Parent interface $parent_interface does not exist"
        return 1
    fi
    
    # Create VLAN interface
    ip link add link "$parent_interface" name "$vlan_name" type vlan id "$vlan_id"
    
    # Bring interface up
    ip link set dev "$vlan_name" up
    
    # Assign IP address
    if [ ! -z "$ip_addr" ]; then
        ip addr add "$ip_addr" dev "$vlan_name"
        print_success "VLAN interface $vlan_name created with IP $ip_addr"
    else
        print_success "VLAN interface $vlan_name created without IP"
    fi
}

# Function to create a dummy interface
create_dummy() {
    local dummy_name="${1:-dummy0}"
    local ip_addr="${2:-172.16.0.1/24}"
    
    print_status "Creating dummy interface: $dummy_name"
    
    # Load dummy module if needed
    modprobe dummy 2>/dev/null || true
    
    # Create dummy interface
    ip link add "$dummy_name" type dummy
    
    # Bring interface up
    ip link set dev "$dummy_name" up
    
    # Assign IP address
    if [ ! -z "$ip_addr" ]; then
        ip addr add "$ip_addr" dev "$dummy_name"
        print_success "Dummy interface $dummy_name created with IP $ip_addr"
    else
        print_success "Dummy interface $dummy_name created without IP"
    fi
}

# Function to configure existing interface
configure_interface() {
    local interface="${1}"
    local ip_addr="${2}"
    local gateway="${3}"
    
    if [ -z "$interface" ] || [ -z "$ip_addr" ]; then
        print_error "Interface name and IP address required"
        return 1
    fi
    
    print_status "Configuring interface: $interface"
    
    # Check if interface exists
    if ! ip link show "$interface" &>/dev/null; then
        print_error "Interface $interface does not exist"
        return 1
    fi
    
    # Bring interface up
    ip link set dev "$interface" up
    
    # Clear existing IP addresses
    ip addr flush dev "$interface" 2>/dev/null || true
    
    # Assign new IP address
    ip addr add "$ip_addr" dev "$interface"
    
    # Set gateway if provided
    if [ ! -z "$gateway" ]; then
        ip route add default via "$gateway" dev "$interface" 2>/dev/null || print_warning "Could not set default gateway"
    fi
    
    print_success "Interface $interface configured with IP $ip_addr"
}

# Function to show interface status
show_interfaces() {
    print_status "Current network interfaces:"
    ip addr show
    echo ""
    print_status "Routing table:"
    ip route show
}

# Function to cleanup interfaces
cleanup_interfaces() {
    print_status "Cleaning up created interfaces..."
    
    # List of common test interface patterns
    PATTERNS="tap[0-9]+ tun[0-9]+ br[0-9]+ dummy[0-9]+ .*\.[0-9]+"
    
    for pattern in $PATTERNS; do
        for interface in $(ip link show | grep -oE "$pattern" 2>/dev/null || true); do
            print_status "Removing interface: $interface"
            ip link delete "$interface" 2>/dev/null || true
        done
    done
    
    print_success "Cleanup completed"
}

# Function to enable IP forwarding
enable_forwarding() {
    print_status "Enabling IP forwarding..."
    echo 1 > /proc/sys/net/ipv4/ip_forward
    echo 1 > /proc/sys/net/ipv6/conf/all/forwarding 2>/dev/null || true
    print_success "IP forwarding enabled"
}

# Function to setup NAT
setup_nat() {
    local internal_interface="${1:-br0}"
    local external_interface="${2:-eth0}"
    
    print_status "Setting up NAT from $internal_interface to $external_interface"
    
    # Enable forwarding
    enable_forwarding
    
    # Setup iptables rules
    if command -v iptables &> /dev/null; then
        iptables -t nat -A POSTROUTING -o "$external_interface" -j MASQUERADE
        iptables -A FORWARD -i "$internal_interface" -o "$external_interface" -j ACCEPT
        iptables -A FORWARD -i "$external_interface" -o "$internal_interface" -m state --state RELATED,ESTABLISHED -j ACCEPT
        print_success "NAT configured"
    else
        print_error "iptables not available"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "=== Network Interface Creation Script ==="
    echo "1. Create Bridge Interface"
    echo "2. Create TAP Interface"  
    echo "3. Create TUN Interface"
    echo "4. Create VLAN Interface"
    echo "5. Create Dummy Interface"
    echo "6. Configure Existing Interface"
    echo "7. Show Interface Status"
    echo "8. Enable IP Forwarding"
    echo "9. Setup NAT"
    echo "10. Cleanup Test Interfaces"
    echo "0. Exit"
    echo ""
}

# Parse command line arguments
if [ $# -gt 0 ]; then
    case "$1" in
        "bridge")
            check_root
            create_bridge "$2" "$3"
            ;;
        "tap")
            check_root
            create_tap "$2" "$3"
            ;;
        "tun")
            check_root  
            create_tun "$2" "$3"
            ;;
        "vlan")
            check_root
            create_vlan "$2" "$3" "$4"
            ;;
        "dummy")
            check_root
            create_dummy "$2" "$3"
            ;;
        "config")
            check_root
            configure_interface "$2" "$3" "$4"
            ;;
        "show")
            show_interfaces
            ;;
        "forward")
            check_root
            enable_forwarding
            ;;
        "nat")
            check_root
            setup_nat "$2" "$3"
            ;;
        "cleanup")
            check_root
            cleanup_interfaces
            ;;
        *)
            echo "Usage: $0 {bridge|tap|tun|vlan|dummy|config|show|forward|nat|cleanup} [options]"
            echo ""
            echo "Examples:"
            echo "  $0 bridge br0 192.168.1.1/24"
            echo "  $0 tap tap0 192.168.2.1/24"  
            echo "  $0 vlan eth0 100 192.168.100.1/24"
            echo "  $0 config eth0 192.168.1.100/24 192.168.1.1"
            echo "  $0 nat br0 eth0"
            exit 1
            ;;
    esac
else
    # Interactive mode
    while true; do
        show_menu
        read -p "Select option (0-10): " choice
        
        case $choice in
            1)
                check_root
                read -p "Bridge name [br0]: " name
                name=${name:-br0}
                read -p "IP address [192.168.100.1/24]: " ip
                ip=${ip:-192.168.100.1/24}
                create_bridge "$name" "$ip"
                ;;
            2)
                check_root
                read -p "TAP name [tap0]: " name
                name=${name:-tap0}
                read -p "IP address [192.168.101.1/24]: " ip
                ip=${ip:-192.168.101.1/24}
                create_tap "$name" "$ip"
                ;;
            3)
                check_root
                read -p "TUN name [tun0]: " name
                name=${name:-tun0}
                read -p "IP address [10.0.0.1/24]: " ip
                ip=${ip:-10.0.0.1/24}
                create_tun "$name" "$ip"
                ;;
            4)
                check_root
                read -p "Parent interface [eth0]: " parent
                parent=${parent:-eth0}
                read -p "VLAN ID [100]: " vlan_id
                vlan_id=${vlan_id:-100}
                read -p "IP address [192.168.${vlan_id}.1/24]: " ip
                ip=${ip:-192.168.${vlan_id}.1/24}
                create_vlan "$parent" "$vlan_id" "$ip"
                ;;
            5)
                check_root
                read -p "Dummy name [dummy0]: " name
                name=${name:-dummy0}
                read -p "IP address [172.16.0.1/24]: " ip
                ip=${ip:-172.16.0.1/24}
                create_dummy "$name" "$ip"
                ;;
            6)
                check_root
                read -p "Interface name: " interface
                read -p "IP address: " ip
                read -p "Gateway (optional): " gateway
                configure_interface "$interface" "$ip" "$gateway"
                ;;
            7)
                show_interfaces
                ;;
            8)
                check_root
                enable_forwarding
                ;;
            9)
                check_root
                read -p "Internal interface [br0]: " internal
                internal=${internal:-br0}
                read -p "External interface [eth0]: " external  
                external=${external:-eth0}
                setup_nat "$internal" "$external"
                ;;
            10)
                check_root
                cleanup_interfaces
                ;;
            0)
                print_success "Exiting..."
                exit 0
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
fi