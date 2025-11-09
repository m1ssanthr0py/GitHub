#!/usr/bin/env bash
# collect_sysinfo.sh
# Collect a broad set of machine information and write to a timestamped text file.
# Usage: ./collect_sysinfo.sh [output-file]
# If no output-file is provided, it writes to /tmp/machine_info_<HOST>_<YYYYmmdd-HHMMSS>.txt

set -euo pipefail

# Helpers
has_cmd() { command -v "$1" >/dev/null 2>&1; }
sep() { printf '\n%s\n\n' "==== $1 ====" >> "$OUT"; }
run() { printf '--- %s ---\n' "$1" >> "$OUT"; shift; "$@" >> "$OUT" 2>&1 || printf "(%s failed or unavailable)\n" "$1" >> "$OUT"; }

TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
HOSTNAME="$(hostname -s 2>/dev/null || echo unknown)"
DEFAULT_OUT="/tmp/machine_info_${HOSTNAME}_${TIMESTAMP}.txt"
OUT="${1:-$DEFAULT_OUT}"

echo "Collecting system information to: $OUT"
echo "Run started: $(date -R)" > "$OUT"
echo "Host: $HOSTNAME" >> "$OUT"
echo "User: $(whoami)" >> "$OUT"
echo

# Basic system
sep "Summary"
run "uname -a" uname -a
run "uptime" uptime
run "who -a" who -a
run "last -n 10" last -n 10 || true
run "hostnamectl" hostnamectl || true

# OS / Distro info
sep "OS / Distribution"
if [ -f /etc/os-release ]; then
  run "os-release" cat /etc/os-release
fi
if has_cmd lsb_release; then
  run "lsb_release -a" lsb_release -a
fi
if has_cmd sw_vers; then
  run "sw_vers" sw_vers
fi
run "kernel" uname -r

# Hardware
sep "Hardware"
run "lscpu" lscpu || true
run "cat /proc/cpuinfo" sed -n '1,200p' /proc/cpuinfo || true
if has_cmd dmidecode; then
  run "dmidecode (requires sudo)" dmidecode -t system || true
fi
if has_cmd lspci; then
  run "lspci -vv" lspci -vv || true
fi
if has_cmd lsusb; then
  run "lsusb -v" lsusb -v || true
fi
run "free -h" free -h || true
run "df -h" df -h
run "lsblk -f" lsblk -f || true

# Memory / Swap
sep "Memory & Swap"
run "cat /proc/meminfo" sed -n '1,120p' /proc/meminfo || true
run "swapon --show" swapon --show || true

# Disk usage & SMART (if available)
sep "Disk & SMART"
run "df -hT" df -hT
if has_cmd smartctl; then
  run "smartctl -a for /dev/sda" smartctl -a /dev/sda || true
fi

# Networking
sep "Networking"
if has_cmd ip; then
  run "ip addr" ip addr
  run "ip -6 addr" ip -6 addr || true
  run "ip route" ip route
  run "ip -6 route" ip -6 route || true
else
  run "ifconfig -a" ifconfig -a || true
  run "route -n" route -n || true
fi
run "netstat -tnlp (if netstat present)" netstat -tnlp || true
run "ss -tunap" ss -tunap || true
run "cat /etc/hosts" cat /etc/hosts || true
run "resolv.conf" cat /etc/resolv.conf || true
run "iptables-save (requires sudo)" iptables-save || true
if has_cmd nft; then
  run "nft list ruleset" nft list ruleset || true
fi
if has_cmd firewall-cmd; then
  run "firewall-cmd --state" firewall-cmd --state || true
  run "firewall-cmd --list-all" firewall-cmd --list-all || true
fi
if has_cmd ufw; then
  run "ufw status verbose" ufw status verbose || true
fi

# Services & processes
sep "Services & Processes"
run "ps aux --sort=-%mem | head -n 25" ps aux --sort=-%mem | head -n 25
if has_cmd systemctl; then
  run "systemctl list-units --type=service --state=running" systemctl list-units --type=service --state=running
  run "systemctl --failed" systemctl --failed || true
fi
run "top snapshot (non-interactive - 1 iteration)" top -b -n 1 | head -n 50 || true

# Installed packages (best-effort)
sep "Installed Packages"
if has_cmd dpkg; then
  run "dpkg -l | head -n 200" dpkg -l | head -n 200
elif has_cmd rpm; then
  run "rpm -qa | head -n 200" rpm -qa | head -n 200
elif has_cmd pacman; then
  run "pacman -Qe | head -n 200" pacman -Qe | head -n 200
else
  printf "No known package manager detected or insufficient permissions.\n" >> "$OUT"
fi

# Users, groups, sudoers
sep "Users & Sudoers"
run "getent passwd" getent passwd || cat /etc/passwd >> "$OUT" 2>/dev/null || true
run "getent group" getent group || cat /etc/group >> "$OUT" 2>/dev/null || true
if [ -f /etc/sudoers ]; then
  run "/etc/sudoers" sed -n '1,200p' /etc/sudoers || true
fi
if [ -d /etc/sudoers.d ]; then
  run "/etc/sudoers.d" ls -la /etc/sudoers.d || true
fi

# Scheduled jobs / cron
sep "Scheduled Jobs"
if has_cmd crontab; then
  run "crontab -l for current user" crontab -l || true
fi
run "system crontabs /etc/cron*" ls -la /etc/cron* || true

# SSH, keys, auth
sep "SSH & Auth"
if [ -d /etc/ssh ]; then
  run "sshd_config" sed -n '1,200p' /etc/ssh/sshd_config || true
fi
if [ -d ~/.ssh ]; then
  run "User .ssh files" ls -la ~/.ssh || true
  run "User authorized_keys" sed -n '1,200p' ~/.ssh/authorized_keys || true
fi

# Docker / containers (if installed)
sep "Containers / Virtualization"
if has_cmd docker; then
  run "docker version" docker version || true
  run "docker info" docker info || true
  run "docker ps -a" docker ps -a || true
fi
if has_cmd podman; then
  run "podman ps -a" podman ps -a || true
fi
if has_cmd virsh; then
  run "virsh list --all" virsh list --all || true
fi

# Security / logs (best-effort, might need sudo)
sep "Security & Logs"
if has_cmd journalctl; then
  run "journalctl -n 200 --no-pager" journalctl -n 200 --no-pager || true
else
  run "dmesg (last kernel messages)" dmesg | tail -n 200 || true
  if [ -f /var/log/syslog ]; then
    run "syslog last 200 lines" tail -n 200 /var/log/syslog || true
  elif [ -f /var/log/messages ]; then
    run "messages last 200 lines" tail -n 200 /var/log/messages || true
  fi
fi
if has_cmd ausearch; then
  run "audit logs (ausearch -m USER_LOGIN -ts today)" ausearch -m USER_LOGIN -ts today || true
fi

# Open ports / listening sockets
sep "Open Ports / Listening Sockets"
if has_cmd ss; then
  run "ss -ltnp" ss -ltnp || true
elif has_cmd netstat; then
  run "netstat -ltnp" netstat -ltnp || true
fi

# Routing & ARP / Neighbor tables
sep "Routing & ARP/Neighbors"
if has_cmd ip; then
  run "ip neigh" ip neigh || true
  run "ip -6 neigh" ip -6 neigh || true
fi
if has_cmd arp; then
  run "arp -an" arp -an || true
fi

# Mounted filesystems & fstab
sep "Mounts & FSTAB"
run "mount" mount || true
if [ -f /etc/fstab ]; then
  run "/etc/fstab" sed -n '1,200p' /etc/fstab || true
fi

# Kernel params
sep "Kernel & Sysctl"
run "sysctl -a | head -n 200" sysctl -a | head -n 200 || true

# Useful config files
sep "Useful Configuration Files (if present)"
for f in /etc/hosts /etc/resolv.conf /etc/hostname /etc/issue; do
  if [ -f "$f" ]; then
    run "cat $f" cat "$f"
  fi
done

# Optional: capture a small packet summary (requires tcpdump & sudo)
sep "Packet Capture Summary (requires sudo & tcpdump)"
if has_cmd tcpdump && [ "$(id -u)" -eq 0 ]; then
  # brief packet capture: 10 seconds or 100 packets, whichever comes first
  run "tcpdump -nn -c 100 -s 128 -w - 'not port 22' | tcpdump -nn -r - -c 20" bash -c "timeout 10 tcpdump -nn -c 100 -s 128 -w - 'not port 22' 2>/dev/null | tcpdump -nn -r - - -c 20" || true
else
  printf "tcpdump not run: either not installed or not running as root.\n" >> "$OUT"
fi

# Final notes
sep "Notes"
printf "Script generated on: %s\n" "$(date -R)" >> "$OUT"
printf "\nEnd of report\n" >> "$OUT"

echo "Done. Output written to: $OUT"
echo "Tip: inspect the output with less, or compress it: gzip -9 \"$OUT\""
