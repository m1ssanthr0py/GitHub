#!/bin/bash
"""
Deploy Updated C2 Server (Persistent Mode)
"""

echo "=== Deploying Persistent C2 Server ==="

# Stop any existing server processes
echo "Stopping existing C2 server processes..."
docker exec outrun_webserver pkill -f c2server_daemon.py 2>/dev/null || true

# Copy updated server
echo "Copying updated server daemon..."
docker cp c2server_daemon.py outrun_webserver:/tmp/

# Start the new persistent server in background
echo "Starting persistent C2 server..."
docker exec -d outrun_webserver sh -c "cd /tmp && python3 c2server_daemon.py > c2server.log 2>&1 &"

# Give it a moment to start
sleep 3

# Check if it's running
echo "Checking server status..."
if docker exec outrun_webserver netstat -tlnp | grep -q ":8888"; then
    echo "[SUCCESS] Persistent C2 server is running on port 8888"
    echo ""
    echo "Server features:"
    echo "  - No timeout disconnections"
    echo "  - OS-level keep-alive enabled"
    echo "  - Persistent connections until shutdown"
    echo ""
    echo "To check server logs:"
    echo "  docker exec outrun_webserver cat /tmp/c2server.log"
    echo ""
    echo "To stop server:"
    echo "  docker exec outrun_webserver pkill -f c2server_daemon.py"
else
    echo "[ERROR] Server may not have started properly"
    echo "Check logs with: docker exec outrun_webserver cat /tmp/c2server.log"
fi

echo ""
echo "Deployment complete!"