#!/usr/bin/env bash
# Cleanup script to remove everything created by folders.sh

# Get the current working directory
CURRENT_DIR="$(pwd)"
BGP_LAB_DIR="$CURRENT_DIR/docker-bgp"

echo "BGP Lab Cleanup Script"
echo "====================="

# Check if the directory exists
if [ ! -d "$BGP_LAB_DIR" ]; then
    echo "BGP lab directory not found at: $BGP_LAB_DIR"
    echo "Nothing to clean up."
    exit 0
fi

echo "Found BGP lab directory at: $BGP_LAB_DIR"
echo

# Show what will be deleted
echo "The following directory and all its contents will be PERMANENTLY deleted:"
echo "$BGP_LAB_DIR"
echo

# Show the structure that will be deleted
echo "Directory structure to be removed:"
if command -v tree >/dev/null 2>&1; then
    tree "$BGP_LAB_DIR"
else
    find "$BGP_LAB_DIR" | sort
fi
echo

# Confirmation prompt
read -p "Are you sure you want to delete the entire BGP lab directory? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Double confirmation for safety
echo "WARNING: This action cannot be undone!"
read -p "Type 'DELETE' to confirm permanent deletion: " confirm

if [ "$confirm" != "DELETE" ]; then
    echo "Cleanup cancelled. Directory not deleted."
    exit 0
fi

# Perform the deletion
echo "Removing BGP lab directory..."
rm -rf "$BGP_LAB_DIR"

# Verify deletion
if [ ! -d "$BGP_LAB_DIR" ]; then
    echo "✅ BGP lab directory successfully removed!"
    echo "All files and directories created by folders.sh have been deleted."
else
    echo "❌ Error: Failed to remove BGP lab directory."
    echo "Please check permissions and try again."
    exit 1
fi

echo "Cleanup completed successfully!"