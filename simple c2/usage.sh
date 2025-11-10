#!/bin/bash

# Malformed Labs Simple C2 - Quick Usage Guide

echo "======================================================"
echo "🔥 SIMPLE C2 - QUICK USAGE GUIDE 🔥"
echo "======================================================"
echo

echo "📂 Current Directory: $(pwd)"
echo "📁 Available Files:"
ls -la *.py *.sh 2>/dev/null | grep -E '\.(py|sh)$' | awk '{print "   " $9 " (" $5 " bytes)"}'

echo
echo "🚀 QUICK COMMANDS:"
echo
echo "1️⃣  Full Restart (Recommended):"
echo "   ./restart_c2.sh"
echo
echo "2️⃣  Manual Steps:"
echo "   ./cleanup_c2.sh                    # Clean up everything"
echo "   cd '../client lab setup'"
echo "   docker-compose up -d               # Start containers"
echo "   cd '../simple c2'"  
echo "   ./deploy_c2.sh                     # Deploy C2 infrastructure"
echo
echo "3️⃣  Use C2 Console:"
echo "   python3 c2console.py localhost 8889"
echo
echo "4️⃣  Check Status:"
echo "   docker ps                          # View running containers"
echo "   docker exec outrun_webserver netstat -tlnp | grep 888"
echo
echo "📊 MONITORING:"
echo "   🌐 Web Dashboard: http://localhost:8080"
echo "   📡 C2 Server Logs: docker exec outrun_webserver cat /tmp/c2server_daemon.log"
echo "   🤖 Client Logs: docker exec linux_endpoint1 cat /tmp/c2client.log"
echo

echo "🎮 CONSOLE COMMANDS (once connected):"
echo "   list                    # Show connected clients"
echo "   stats                   # Server statistics"  
echo "   broadcast whoami        # Run command on all clients"
echo "   send <id> <command>     # Run command on specific client"
echo "   help                    # Show all commands"
echo "   quit                    # Exit console"
echo

echo "🛠️  TROUBLESHOOTING:"
echo "   • Console won't connect? → Check ports: docker ps | grep 8889"
echo "   • No clients? → Check logs and restart: ./restart_c2.sh"
echo "   • Server issues? → Full cleanup: ./cleanup_c2.sh"
echo

echo "⚠️  REMEMBER: This is for educational/authorized testing only!"
echo
echo "======================================================"