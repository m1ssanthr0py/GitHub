#!/bin/bash
# Setup script for C2 client in containers

echo "[+] C2 Client Setup Script"
echo "[+] Installing Python dependencies..."

# Detect OS and install accordingly
if command -v apk > /dev/null; then
    # Alpine Linux
    echo "[+] Detected Alpine Linux"
    apk add --no-cache python3-dev gcc musl-dev libffi-dev openssl-dev
    pip3 install --upgrade pip
    pip3 install cryptography psutil
elif command -v apt-get > /dev/null; then
    # Ubuntu/Debian
    echo "[+] Detected Ubuntu/Debian"
    apt-get update
    apt-get install -y python3-dev gcc libffi-dev libssl-dev
    pip3 install --upgrade pip
    pip3 install cryptography psutil
elif command -v yum > /dev/null; then
    # CentOS/RHEL
    echo "[+] Detected CentOS/RHEL"
    yum install -y python3-devel gcc openssl-devel libffi-devel
    pip3 install --upgrade pip
    pip3 install cryptography psutil
else
    echo "[ERROR] Unsupported operating system"
    exit 1
fi

echo "[+] Dependencies installed successfully!"
echo "[+] You can now run the C2 client:"
echo "    python3 c2client.py <server_ip> <port> <password>"
echo ""
echo "Example:"
echo "    python3 c2client.py 192.168.210.1 8888 mypassword"