#!/bin/bash
# Quick installer for Docker containers

echo "[+] C2 Client Quick Installer for Containers"
echo "============================================="

# Create working directory
mkdir -p /tmp/c2client
cd /tmp/c2client

# Install dependencies based on OS
if command -v apk > /dev/null; then
    echo "[+] Installing dependencies for Alpine..."
    apk add --no-cache python3-dev gcc musl-dev libffi-dev openssl-dev curl
    pip3 install --upgrade pip
elif command -v apt-get > /dev/null; then
    echo "[+] Installing dependencies for Ubuntu..."
    apt-get update
    apt-get install -y python3-dev gcc libffi-dev libssl-dev curl
    pip3 install --upgrade pip
elif command -v yum > /dev/null; then
    echo "[+] Installing dependencies for CentOS..."
    yum install -y python3-devel gcc openssl-devel libffi-devel curl
    pip3 install --upgrade pip
fi

# Install Python packages
echo "[+] Installing Python packages..."
pip3 install cryptography==41.0.7 psutil==5.9.6

echo "[+] Installation complete!"
echo ""
echo "Usage:"
echo "  python3 c2client.py <server_ip> <port> <password>"
echo ""
echo "Example:"
echo "  python3 c2client.py 192.168.210.1 8888 mypassword"