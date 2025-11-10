#!/usr/bin/env bash
# Network testing script for penetration testing
set -e

echo "=== Network Testing Script ==="
echo "Starting network reconnaissance and testing..."
echo ""

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

# Basic network information
print_status "Gathering basic network information..."
echo "Hostname: $(hostname)"
echo "Current user: $(whoami)"
echo "User ID: $(id)"
echo ""

# Network interfaces
print_status "Network interfaces:"
if command -v ip &> /dev/null; then
    ip addr show
elif command -v ifconfig &> /dev/null; then
    ifconfig
else
    print_error "Neither 'ip' nor 'ifconfig' command found"
fi
echo ""

# Routing table
print_status "Routing table:"
if command -v ip &> /dev/null; then
    ip route show
elif command -v route &> /dev/null; then
    route -n
else
    print_error "No routing command found"
fi
echo ""

# DNS configuration
print_status "DNS configuration:"
if [ -f /etc/resolv.conf ]; then
    cat /etc/resolv.conf
else
    print_error "/etc/resolv.conf not found"
fi
echo ""

# ARP table
print_status "ARP table:"
if command -v arp &> /dev/null; then
    arp -a
else
    print_error "ARP command not found"
fi
echo ""

# Active connections
print_status "Active network connections:"
if command -v netstat &> /dev/null; then
    netstat -tulnp 2>/dev/null | head -20
elif command -v ss &> /dev/null; then
    ss -tulnp | head -20
else
    print_error "Neither 'netstat' nor 'ss' command found"
fi
echo ""

# Listening services
print_status "Listening services:"
if command -v netstat &> /dev/null; then
    netstat -tlnp 2>/dev/null
elif command -v ss &> /dev/null; then
    ss -tlnp
else
    print_error "No network stat command found"
fi
echo ""

# Test connectivity to common services
print_status "Testing connectivity..."

# Test DNS resolution
if command -v nslookup &> /dev/null; then
    echo "DNS test (google.com):"
    nslookup google.com || print_warning "DNS lookup failed"
elif command -v dig &> /dev/null; then
    echo "DNS test (google.com):"
    dig google.com +short || print_warning "DNS lookup failed"
fi
echo ""

# Test ping connectivity
if command -v ping &> /dev/null; then
    echo "Ping test (8.8.8.8):"
    ping -c 3 8.8.8.8 || print_warning "Ping test failed"
    echo ""
    
    echo "Ping test (google.com):"
    ping -c 3 google.com || print_warning "Ping to google.com failed"
fi
echo ""

# Test HTTP connectivity
if command -v curl &> /dev/null; then
    echo "HTTP connectivity test:"
    curl -I --connect-timeout 5 http://google.com || print_warning "HTTP test failed"
    echo ""
    
    echo "HTTPS connectivity test:"
    curl -I --connect-timeout 5 https://google.com || print_warning "HTTPS test failed"
elif command -v wget &> /dev/null; then
    echo "HTTP connectivity test:"
    wget --spider --timeout=5 http://google.com || print_warning "HTTP test failed"
fi
echo ""

# Port scanning local machine
print_status "Scanning local open ports..."
if command -v nmap &> /dev/null; then
    nmap -sT -O localhost 2>/dev/null || nmap localhost 2>/dev/null
else
    print_warning "nmap not available, using basic port check"
    for port in 21 22 23 25 53 80 110 143 443 993 995 8080 8443; do
        if command -v nc &> /dev/null; then
            if nc -z localhost $port 2>/dev/null; then
                print_success "Port $port is open"
            fi
        elif command -v telnet &> /dev/null; then
            timeout 2 telnet localhost $port &>/dev/null && print_success "Port $port is open"
        fi
    done
fi
echo ""

# Network discovery on local subnet
print_status "Network discovery (local subnet)..."
if command -v nmap &> /dev/null; then
    # Get local network
    LOCAL_NET=$(ip route | grep -E "192\.168\.|10\.|172\." | grep "/" | head -1 | awk '{print $1}')
    if [ ! -z "$LOCAL_NET" ]; then
        echo "Scanning network: $LOCAL_NET"
        nmap -sn $LOCAL_NET 2>/dev/null | grep -E "Nmap scan report|MAC Address"
    fi
fi
echo ""

# Check for proxy settings
print_status "Checking proxy settings..."
env | grep -i proxy || print_status "No proxy environment variables set"
echo ""

# Firewall rules (if accessible)
print_status "Firewall information:"
if command -v iptables &> /dev/null; then
    iptables -L 2>/dev/null || print_warning "Cannot access iptables (insufficient privileges)"
elif command -v ufw &> /dev/null; then
    ufw status 2>/dev/null || print_warning "Cannot access ufw status"
fi
echo ""

# Network tools availability
print_status "Available network tools:"
TOOLS="ping nslookup dig curl wget nc telnet nmap netstat ss iptables tcpdump wireshark"
for tool in $TOOLS; do
    if command -v $tool &> /dev/null; then
        print_success "$tool is available"
    else
        print_warning "$tool is not available"
    fi
done

echo ""
print_success "Network testing completed!"