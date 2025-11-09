import socket
import subprocess
import sys
import os

# --- Configuration ---
HOST = '192.168.210.120'
PORT = 65432        # The port used by the server

def is_safe_command(command):
    """Check if the command is safe to execute."""
    # Define allowed commands
    safe_commands = ['ls', 'pwd', 'whoami', 'date', 'uname', 'id']
    
    # Get the base command (first word)
    base_command = command.strip().split()[0] if command.strip() else ""
    
    # Allow safe system commands
    if base_command in safe_commands:
        return True
    
    # Allow ls with flags and paths
    if base_command == 'ls' or command.startswith('ls '):
        return True
    
    # Allow pwd variations
    if base_command == 'pwd':
        return True
    
    # Add your custom commands here
    if command.startswith('echo ') or command.startswith('cat '):
        return True
    
    # Allow collect_sysinfo.sh command
    if command == 'collect_sysinfo':
        return True
    
    return False

def collect_system_info():
    """Execute collect_sysinfo.sh and save output to /tmp/"""
    try:
        # Check if collect_sysinfo.sh exists in current directory
        script_path = './collect_sysinfo.sh'
        if not os.path.exists(script_path):
            return "Error: collect_sysinfo.sh not found in current directory"
        
        # Make sure the script is executable
        os.chmod(script_path, 0o755)
        
        # Execute the script and capture output
        result = subprocess.run(
            [script_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Save output to /tmp/sysinfo.txt
            output_file = '/tmp/sysinfo.txt'
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            
            return f"System info collected successfully and saved to {output_file}\n{result.stdout}"
        else:
            return f"Error running collect_sysinfo.sh: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "Error: collect_sysinfo.sh timed out (60 seconds)"
    except Exception as e:
        return f"Error collecting system info: {str(e)}"

def execute_command(command):
    """Execute a system command and return the result."""
    # Handle special collect_sysinfo command
    if command == 'collect_sysinfo':
        return collect_system_info()
    
    # Validate command first
    if not is_safe_command(command):
        return f"Error: Command '{command}' is not allowed"
    
    try:
        # Execute the command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30  # Increased timeout
        )
        
        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\nError: {result.stderr}"
            
        return output if output else "Command executed successfully (no output)"
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (30 seconds)"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def run_client():
    """Connects to the server and sends user commands."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"Attempting to connect to {HOST}:{PORT}...")
            
            # Connect to the server
            s.connect((HOST, PORT))
            print("Successfully connected to the server!")
            print("Type 'quit' or 'exit' to close the connection.")
            print("Type 'collect_sysinfo' to run system info collection.\n")
            
            while True:
                try:
                    # Ask user for command
                    command = input("Enter command: ").strip()
                    
                    # Handle quit commands
                    if command.lower() in ['quit', 'exit', '']:
                        print("Closing connection...")
                        break
                    
                    print(f"SENDING COMMAND: {command}")
                    
                    # Send command to server
                    s.sendall(command.encode('utf-8'))
                    
                    # Receive response from server
                    response = s.recv(4096).decode('utf-8')
                    print(f"SERVER RESPONSE:\n{response}\n")
                    
                except KeyboardInterrupt:
                    print("\nInterrupted by user. Closing connection...")
                    break
                except Exception as e:
                    print(f"Error: {str(e)}")
                    break

    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running.")
    except Exception as e:
        print(f"An error occurred in the client: {e}")
    finally:
        print("Client connection closed.")

if __name__ == '__main__':
    run_client()
