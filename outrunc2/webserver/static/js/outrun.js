// Outrun Lab Terminal JavaScript

class OutrunTerminal {
    constructor() {
        this.systemInfo = document.getElementById('systemInfo');
        this.networkStatus = document.getElementById('networkStatus');
        this.terminalOutput = document.getElementById('terminalOutput');
        this.commandSelect = document.getElementById('commandSelect');
        this.executeBtn = document.getElementById('executeBtn');
        
        // Client management elements
        this.clientStatus = document.getElementById('clientStatus');
        this.clientOutput = document.getElementById('clientOutput');
        this.clientCommandSelect = document.getElementById('clientCommandSelect');
        this.executeOnAllBtn = document.getElementById('executeOnAllBtn');
        this.clientBtns = document.querySelectorAll('.client-btn');
        
        this.init();
    }
    
    init() {
        this.loadSystemInfo();
        this.loadNetworkStatus();
        this.loadClientStatus();
        this.setupEventListeners();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.loadSystemInfo();
            this.loadNetworkStatus();
            this.loadClientStatus();
        }, 30000);
    }
    
    setupEventListeners() {
        // Server terminal events
        this.executeBtn.addEventListener('click', () => this.executeCommand());
        this.commandSelect.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.executeCommand();
            }
        });
        
        // Client management events
        this.executeOnAllBtn.addEventListener('click', () => this.executeOnAllClients());
        this.clientCommandSelect.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.executeOnAllClients();
            }
        });
        
        // Individual client buttons
        this.clientBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const client = e.target.getAttribute('data-client');
                this.executeOnClient(client);
            });
        });
    }
    
    async loadSystemInfo() {
        try {
            const response = await fetch('/api/system');
            const data = await response.json();
            
            if (data.error) {
                this.systemInfo.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                return;
            }
            
            const html = `
                <div class="system-data">
                    <div><strong>Hostname:</strong> ${data.hostname}</div>
                    <div><strong>Timestamp:</strong> ${new Date(data.timestamp).toLocaleString()}</div>
                    <div><strong>Uptime:</strong></div>
                    <pre>${data.uptime}</pre>
                </div>
            `;
            this.systemInfo.innerHTML = html;
        } catch (error) {
            this.systemInfo.innerHTML = `<div class="error">Failed to load system info: ${error.message}</div>`;
        }
    }
    
    async loadNetworkStatus() {
        try {
            const response = await fetch('/api/network');
            const data = await response.json();
            
            let html = '<div class="endpoints">';
            
            Object.entries(data).forEach(([endpoint, result]) => {
                const status = result.success ? 'online' : 'offline';
                const statusText = result.success ? 'ONLINE' : 'OFFLINE';
                
                html += `
                    <div class="endpoint ${status}">
                        <div class="endpoint-header">
                            ${endpoint} - ${statusText}
                        </div>
                        <div class="endpoint-details">
                            <pre>${result.output}</pre>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            this.networkStatus.innerHTML = html;
        } catch (error) {
            this.networkStatus.innerHTML = `<div class="error">Failed to load network status: ${error.message}</div>`;
        }
    }

    async loadClientStatus() {
        try {
            const response = await fetch('/api/clients');
            const data = await response.json();
            
            if (data.error) {
                this.clientStatus.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                return;
            }
            
            let html = '<div class="client-info">';
            
            Object.entries(data).forEach(([clientName, info]) => {
                const statusClass = info.running ? 'online' : 'offline';
                const statusText = info.running ? 'ONLINE' : 'OFFLINE';
                
                html += `
                    <div class="client-item ${statusClass}">
                        <div class="client-name">${clientName.toUpperCase()}</div>
                        <div class="client-details">
                            Status: ${statusText}<br>
                            Container: ${info.container_name}<br>
                            IP: ${info.ip_address}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            this.clientStatus.innerHTML = html;
        } catch (error) {
            this.clientStatus.innerHTML = `<div class="error">Failed to load client status: ${error.message}</div>`;
        }
    }

    async executeOnAllClients() {
        const command = this.clientCommandSelect.value;
        if (!command) return;
        
        // Add command to client output
        this.addClientLine(`c2@malformed:~$ Executing "${command}" on all clients`, 'command');
        
        try {
            const response = await fetch('/api/clients/execute-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command })
            });
            
            const data = await response.json();
            
            if (data.results) {
                Object.entries(data.results).forEach(([clientName, result]) => {
                    if (result.success) {
                        this.addClientLine(`[${clientName.toUpperCase()}] Success:`, 'success-header');
                        if (result.stdout) {
                            this.addClientLine(result.stdout, 'success-output');
                        }
                        if (result.stderr) {
                            this.addClientLine(`stderr: ${result.stderr}`, 'warning-output');
                        }
                    } else {
                        this.addClientLine(`[${clientName.toUpperCase()}] Error:`, 'error-header');
                        this.addClientLine(result.error, 'error-output');
                    }
                });
            } else {
                this.addClientLine(`Error: ${data.error}`, 'error-output');
            }
        } catch (error) {
            this.addClientLine(`Network error: ${error.message}`, 'error-output');
        }
        
        // Clear selection
        this.clientCommandSelect.value = '';
        
        // Scroll to bottom
        this.clientOutput.scrollTop = this.clientOutput.scrollHeight;
    }

    async executeOnClient(clientName) {
        const command = this.clientCommandSelect.value;
        if (!command) return;
        
        // Add command to client output
        this.addClientLine(`c2@malformed:~$ Executing "${command}" on ${clientName.toUpperCase()}`, 'command');
        
        try {
            const response = await fetch(`/api/clients/${clientName}/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addClientLine(`[${clientName.toUpperCase()}] Success:`, 'success-header');
                if (data.stdout) {
                    this.addClientLine(data.stdout, 'success-output');
                }
                if (data.stderr) {
                    this.addClientLine(`stderr: ${data.stderr}`, 'warning-output');
                }
            } else {
                this.addClientLine(`[${clientName.toUpperCase()}] Error:`, 'error-header');
                this.addClientLine(data.error, 'error-output');
            }
        } catch (error) {
            this.addClientLine(`Network error: ${error.message}`, 'error-output');
        }
        
        // Clear selection
        this.clientCommandSelect.value = '';
        
        // Scroll to bottom
        this.clientOutput.scrollTop = this.clientOutput.scrollHeight;
    }

    addClientLine(text, type = 'output') {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        
        if (type === 'command') {
            line.innerHTML = `<span class="prompt">c2@malformed:~$</span> <span class="command">${text.replace('c2@malformed:~$ ', '')}</span>`;
        } else if (type === 'error-header') {
            line.innerHTML = `<span style="color: #FF0099; font-weight: bold;">${text}</span>`;
        } else if (type === 'error-output') {
            line.innerHTML = `<pre style="color: #FF0099; margin: 0; white-space: pre-wrap; padding-left: 20px;">${text}</pre>`;
        } else if (type === 'success-header') {
            line.innerHTML = `<span style="color: #00FFFF; font-weight: bold;">${text}</span>`;
        } else if (type === 'success-output') {
            line.innerHTML = `<pre style="color: #00FFFF; margin: 0; white-space: pre-wrap; padding-left: 20px;">${text}</pre>`;
        } else if (type === 'warning-output') {
            line.innerHTML = `<pre style="color: #FFAA00; margin: 0; white-space: pre-wrap; padding-left: 20px;">${text}</pre>`;
        } else {
            line.innerHTML = `<pre style="color: #00FFFF; margin: 0; white-space: pre-wrap;">${text}</pre>`;
        }
        
        this.clientOutput.appendChild(line);
        
        // Limit client output history to last 100 lines
        const lines = this.clientOutput.querySelectorAll('.terminal-line');
        if (lines.length > 100) {
            lines[0].remove();
        }
    }

    async executeCommand() {
        const command = this.commandSelect.value;
        if (!command) return;
        
        // Add command to terminal output
        this.addTerminalLine(`root@malformed:~$ ${command}`, 'command');
        
        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command })
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (data.output) {
                    this.addTerminalLine(data.output, 'output');
                }
                if (data.error) {
                    this.addTerminalLine(`stderr: ${data.error}`, 'error');
                }
            } else {
                this.addTerminalLine(`Error: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addTerminalLine(`Network error: ${error.message}`, 'error');
        }
        
        // Clear selection
        this.commandSelect.value = '';
        
        // Scroll to bottom
        this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
    }
    
    addTerminalLine(text, type = 'output') {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        
        if (type === 'command') {
            line.innerHTML = `<span class="prompt">root@malformed:~$</span> <span class="command">${text.replace('root@malformed:~$ ', '')}</span>`;
        } else if (type === 'error') {
            line.innerHTML = `<span style="color: #FF0099;">${text}</span>`;
        } else {
            line.innerHTML = `<pre style="color: #00FFFF; margin: 0; white-space: pre-wrap;">${text}</pre>`;
        }
        
        this.terminalOutput.appendChild(line);
        
        // Limit terminal history to last 50 lines
        const lines = this.terminalOutput.querySelectorAll('.terminal-line');
        if (lines.length > 50) {
            lines[0].remove();
        }
    }
    
    // Add some visual effects
    createGlitchEffect() {
        const elements = document.querySelectorAll('.neon-text');
        elements.forEach(element => {
            setInterval(() => {
                if (Math.random() < 0.1) { // 10% chance
                    element.style.textShadow = '2px 0 #FF0099, -2px 0 #00FFFF';
                    setTimeout(() => {
                        element.style.textShadow = '0 0 5px #FF0099, 0 0 10px #FF0099, 0 0 15px #FF0099, 0 0 20px #FF0099';
                    }, 100);
                }
            }, 3000);
        });
    }
}

// Matrix-style background effect
function createMatrixEffect() {
    const canvas = document.createElement('canvas');
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '-2';
    canvas.style.opacity = '0.1';
    document.body.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
    const columns = Math.floor(canvas.width / 20);
    const drops = new Array(columns).fill(0);
    
    function draw() {
        ctx.fillStyle = 'rgba(5, 5, 5, 0.05)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#00FFFF';
        ctx.font = '15px monospace';
        
        for (let i = 0; i < drops.length; i++) {
            const text = chars[Math.floor(Math.random() * chars.length)];
            ctx.fillText(text, i * 20, drops[i] * 20);
            
            if (drops[i] * 20 > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }
    
    setInterval(draw, 100);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const terminal = new OutrunTerminal();
    terminal.createGlitchEffect();
    createMatrixEffect();
    
    // Add some startup messages
    setTimeout(() => {
        terminal.addTerminalLine('Malformed Labs C2 Terminal v2.0.85 initialized...', 'output');
        terminal.addTerminalLine('Cyberdeck connected to neural network...', 'output');
        terminal.addTerminalLine('All systems nominal. Ready for input.', 'output');
        
        // Add client management startup message
        terminal.addClientLine('Client management system online...', 'output');
        terminal.addClientLine('Scanning for connected endpoints...', 'output');
        terminal.addClientLine('Ready to execute commands on client machines.', 'output');
    }, 1000);
});