// Outrun Lab Terminal JavaScript

class OutrunTerminal {
    constructor() {
        this.systemInfo = document.getElementById('systemInfo');
        this.networkStatus = document.getElementById('networkStatus');
        this.terminalOutput = document.getElementById('terminalOutput');
        this.commandSelect = document.getElementById('commandSelect');
        this.executeBtn = document.getElementById('executeBtn');
        
        this.init();
    }
    
    init() {
        this.loadSystemInfo();
        this.loadNetworkStatus();
        this.setupEventListeners();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.loadSystemInfo();
            this.loadNetworkStatus();
        }, 30000);
    }
    
    setupEventListeners() {
        this.executeBtn.addEventListener('click', () => this.executeCommand());
        this.commandSelect.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.executeCommand();
            }
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
    }, 1000);
});