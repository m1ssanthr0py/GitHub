#!/usr/bin/env bash
# Create necessary folders for BGP lab environment

# Get the current user's home directory
USER_HOME="$HOME"
BGP_LAB_DIR="$USER_HOME/docker-bgp"

echo "Creating BGP lab directory structure at: $BGP_LAB_DIR"

# Create main directory
mkdir -p "$BGP_LAB_DIR"

# Create docker-compose.yml
cat > "$BGP_LAB_DIR/docker-compose.yml" << 'EOF'
version: '3.8'
services:
  # Add your BGP lab services here
  # Example structure for FRRouting containers
EOF

# Create client directory with Dockerfile
mkdir -p "$BGP_LAB_DIR/client"
cat > "$BGP_LAB_DIR/client/Dockerfile" << 'EOF'
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y \
    iputils-ping \
    traceroute \
    curl \
    tcpdump \
    net-tools
CMD ["/bin/bash"]
EOF

# List of AS directories to create
as_dirs=("as1000" "as2000" "as3000" "as1337")

# Loop through each AS directory and create it
for as_dir in "${as_dirs[@]}"; do
    echo "Creating directory: $as_dir"
    mkdir -p "$BGP_LAB_DIR/$as_dir"
    
    # Create frr.conf for each AS
    cat > "$BGP_LAB_DIR/$as_dir/frr.conf" << EOF
! FRRouting configuration for $as_dir
hostname $as_dir
!
! BGP configuration will be added here
!
EOF
done

# Create special structure for as1000 (with Dockerfile and frr_patches)
echo "Creating special structure for as1000"
mkdir -p "$BGP_LAB_DIR/as1000/frr_patches"

cat > "$BGP_LAB_DIR/as1000/Dockerfile" << 'EOF'
FROM frrouting/frr:latest
COPY frr.conf /etc/frr/frr.conf
COPY frr_patches/ /etc/frr/patches/
RUN chown frr:frr /etc/frr/frr.conf
CMD ["/usr/lib/frr/docker-start"]
EOF

# Create a sample patch file
cat > "$BGP_LAB_DIR/as1000/frr_patches/sample.patch" << 'EOF'
# Sample FRR patch file
# Add your BGP patches here
EOF

echo "BGP lab directory structure created successfully!"
echo "Directory structure:"
tree "$BGP_LAB_DIR" 2>/dev/null || find "$BGP_LAB_DIR" -type d | sort 

