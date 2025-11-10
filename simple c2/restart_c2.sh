#!/bin/bash

# Malformed Labs C2 Full Restart Script
# Complete cleanup and restart of the entire C2 infrastructure

echo "======================================================"
echo "🔄 MALFORMED LABS C2 FULL RESTART 🔄"
echo "======================================================"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="/Users/maladmin/Documents/GitHub/outrunc2/client lab setup"

# Step 1: Cleanup
echo "🧹 Step 1: Cleaning up existing infrastructure..."
"$SCRIPT_DIR/cleanup_c2.sh"

echo
echo "⏱️  Waiting 5 seconds for cleanup to complete..."
sleep 5

# Step 2: Start containers
echo "🚀 Step 2: Starting Docker containers..."
cd "$COMPOSE_DIR"
if docker-compose up -d; then
    echo "✅ Containers started successfully"
else
    echo "❌ Failed to start containers"
    exit 1
fi

echo
echo "⏱️  Waiting 10 seconds for containers to initialize..."
sleep 10

# Step 3: Deploy C2 infrastructure
echo "📡 Step 3: Deploying C2 server and clients..."
cd "$SCRIPT_DIR"

# Copy and start C2 daemon
if docker cp c2server_daemon.py outrun_webserver:/tmp/; then
    echo "✅ C2 daemon copied to webserver"
else
    echo "❌ Failed to copy C2 daemon"
    exit 1
fi

# Start the daemon
if docker exec -d outrun_webserver sh -c "cd /tmp && nohup python3 c2server_daemon.py > c2server_daemon.log 2>&1 &"; then
    echo "✅ C2 daemon started"
else
    echo "❌ Failed to start C2 daemon"
    exit 1
fi

echo "⏱️  Waiting 5 seconds for daemon to start..."
sleep 5

# Deploy clients
if ./deploy_c2.sh; then
    echo "✅ C2 clients deployed"
else
    echo "❌ Failed to deploy C2 clients"
    exit 1
fi

echo
echo "⏱️  Waiting 10 seconds for clients to connect..."
sleep 10

# Step 4: Verify deployment
echo "🔍 Step 4: Verifying deployment..."

# Check if daemon is running
if docker exec outrun_webserver netstat -tln | grep -E ':888[89]' >/dev/null; then
    echo "✅ C2 server ports are open"
else
    echo "❌ C2 server ports not accessible"
    exit 1
fi

# Check client connections
CLIENT_COUNT=$(docker exec outrun_webserver python3 -c "
import socket, json
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 8889))
    request = {'type': 'server_stats'}
    data = json.dumps(request).encode('utf-8')
    sock.send(len(data).to_bytes(4, 'big'))
    sock.send(data)
    length_bytes = sock.recv(4)
    length = int.from_bytes(length_bytes, 'big')
    response_data = sock.recv(length)
    response = json.loads(response_data.decode('utf-8'))
    print(response['stats']['client_count'])
    sock.close()
except:
    print('0')
" 2>/dev/null)

echo
echo "📊 DEPLOYMENT STATUS:"
echo "├─ C2 Server: $(docker exec outrun_webserver netstat -tln | grep ':8888' >/dev/null && echo 'Running' || echo 'Not Running')"
echo "├─ Management Interface: $(docker exec outrun_webserver netstat -tln | grep ':8889' >/dev/null && echo 'Running' || echo 'Not Running')"
echo "├─ Connected Clients: $CLIENT_COUNT"
echo "└─ Web Interface: http://localhost:8080"

if [ "$CLIENT_COUNT" -gt 0 ]; then
    echo
    echo "🎉 SUCCESS! C2 infrastructure is fully operational!"
    echo
    echo "🖥️  To use the C2 console:"
    echo "   python3 c2console.py localhost 8889"
    echo
    echo "📋 Available console commands:"
    echo "   list                    - Show connected clients"
    echo "   send <id> <command>     - Send command to specific client"
    echo "   broadcast <command>     - Send command to all clients"
    echo "   stats                   - Show server statistics"
else
    echo
    echo "⚠️  Warning: No clients connected yet. Check logs:"
    echo "   docker exec linux_endpoint1 cat /tmp/c2client.log"
    echo "   docker exec outrun_webserver cat /tmp/c2server_daemon.log"
fi

echo
echo "======================================================"