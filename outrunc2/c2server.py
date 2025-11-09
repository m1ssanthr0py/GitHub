import socket
import argparse
import time
import sys
import os # Imported for file operations

# --- Configuration ---
HOST = '0.0.0.0' 
PORT = 65432     # Port for the server to listen on.

def run_server(verbose_heartbeat):
    """
    Initializes and runs a simple TCP server that handles specific commands
    and echoes other messages.
    """
    # Define the command prefix for saving files
    FILE_CMD_PREFIX = "SAVE_FILE:"
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Reusing the address prevents "Address already in use" errors immediately after shutdown
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            s.bind((HOST, PORT))
            print(f"Server starting up on {HOST}:{PORT}")
            
            # Listen for incoming connections (increased backlog to 5)
            s.listen(5) 
            
            print("Waiting for a client connection...")
            
            # Main loop to accept connections
            while True:
                # This call blocks until a client connects
                conn, addr = s.accept()
                
                with conn:
                    print(f"\n[INFO] Connection established from: {addr[0]}:{addr[1]}")
                    
                    # Command handling loop for the connected client
                    while True:
                        # Receive data from the client (increased buffer to 4096 bytes)
                        data = conn.recv(4096) 
                        
                        if not data:
                            print(f"[INFO] Client {addr[0]}:{addr[1]} disconnected.")
                            break
                        
                        # Decode the bytes to a clean string, converting to uppercase for command matching
                        message = data.decode('utf-8').strip()
                        message_upper = message.upper() # Use for command matching

                        if not message:
                            continue

                        # --- Command Processing Logic ---
                        response_text = ""
                        
                        # 1. HANDLE FILE TRANSFER COMMAND
                        if message_upper.startswith(FILE_CMD_PREFIX):
                            try:
                                # Strip the command prefix and find the separator '|'
                                file_data = message[len(FILE_CMD_PREFIX):].strip()
                                separator_index = file_data.find('|')

                                if separator_index == -1:
                                    response_text = "ERROR: File command missing filename or content separator (|)."
                                else:
                                    filename = file_data[:separator_index].strip()
                                    content = file_data[separator_index+1:].lstrip()

                                    # Simple validation to prevent path traversal/empty name
                                    if not filename or '..' in filename:
                                        response_text = "ERROR: Invalid filename."
                                    else:
                                        with open(filename, 'w') as f:
                                            f.write(content)
                                        
                                        response_text = f"SUCCESS: File '{filename}' ({len(content)} bytes) saved on server."
                                        print(f"[FILE TRANSFER] Successfully saved file: {filename}")

                            except Exception as e:
                                response_text = f"ERROR saving file: {e}"
                                print(f"[FILE TRANSFER ERROR] {e}")

                        # 2. HANDLE HEARTBEAT COMMAND
                        elif message_upper == 'HEARTBEAT':
                            response_text = "ACK_HEARTBEAT"
                            if verbose_heartbeat:
                                print(f"[HEARTBEAT] Received from {addr[0]}. Responding with ACK.")
                            else:
                                # Quiet indicator restored
                                sys.stdout.write('.')
                                sys.stdout.flush()
                        
                        # 3. HANDLE GET_TIME COMMAND
                        elif message_upper == 'GET_TIME':
                            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                            response_text = f"CURRENT_TIME: {current_time}"
                            print(f"[COMMAND] Sent time: {current_time}")

                        # 4. HANDLE ECHO (Unrecognized Message)
                        else:
                            # Echo back any unrecognized message
                            response_text = f"ECHO: {message}"
                            print(f"[RECEIVED] Unknown command/message: {message}")
                        
                        
                        # Send the determined response back to the client
                        response = response_text.encode('utf-8')
                        conn.sendall(response)

    except KeyboardInterrupt:
        print("\n[INFO] Server shutting down gracefully.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        # Ensure the script exits cleanly on error
        sys.exit(1)


if __name__ == '__main__':
    # Parse command line arguments to enable optional heartbeat logging
    parser = argparse.ArgumentParser(description="Simple TCP Echo/Command Server.")
    parser.add_argument(
        '--verbose-heartbeat', 
        action='store_true', 
        help="Display detailed output for received HEARTBEAT commands."
    )
    args = parser.parse_args()
    
    # Run the server with the parsed argument
    run_server(args.verbose_heartbeat)