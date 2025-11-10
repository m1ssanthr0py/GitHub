#!/usr/bin/env bash
# bootstrap_build_capture.sh
# Build/start the docker-bgp lab, set client default route, then ping AS3000 from Client
# while capturing ICMPv6 on AS1000. PCAP is written directly to ./captures on the host.

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
ROOT_DIR="${ROOT_DIR:-docker-bgp}"

CLIENT_NAME="ashleysequeira-client"
AS1000_NAME="ashleysequeira-as1000"
AS1337_NAME="ashleysequeira-as1337"
AS2000_NAME="ashleysequeira-as2000"
AS3000_NAME="ashleysequeira-as3000"

AS1000_LAN_IP="2001:10:10:10::10"
CLIENT_LAN_IP="2001:10:10:10::99"
AS1000_1000_2000_IP="2001:12:12:12::10"
AS2000_1000_2000_IP="2001:12:12:12::20"
AS1000_1000_1337_IP="2001:1:33:7::10"
AS1337_1000_1337_IP="2001:1:33:7::40"
AS2000_2000_3000_IP="2001:23:23:23::20"
AS3000_2000_3000_IP="2001:23:23:23::30"

# Only ping AS3000; override with: TARGET_IPV6=<addr> ./bootstrap_build_capture.sh
TARGET_IPV6="${TARGET_IPV6:-$AS3000_2000_3000_IP}"

ASN_1000=1000
ASN_1337=1337
ASN_2000=2000
ASN_3000=3000

# ----- Host capture directory mapped into AS1000 -----
HOST_CAP_DIR="${HOST_CAP_DIR:-${PROJECT_ROOT}/captures}"
CONTAINER_CAP_DIR="/captures"
STAMP="$(date +%Y%m%d-%H%M%S)"
PCAP_IN_AS1000="${CONTAINER_CAP_DIR}/client-to-as3000-${STAMP}-on-as1000.pcap"
PID_AS1000="/tmp/tcpdump-as1000.pid"

FORCE_OVERWRITE=false

# ---------- helpers ----------
have() { command -v "$1" >/dev/null 2>&1; }
die() { echo "ERROR: $*" >&2; exit 1; }

compose_cmd() {
  if have docker && docker compose version >/dev/null 2>&1; then
	echo "docker compose"
  elif have docker-compose; then
	echo "docker-compose"
  else
	die "Docker Compose not found."
  fi
}

write_file() {
  local path="$1"; shift
  if [[ -e "$path" && "$FORCE_OVERWRITE" != "true" ]]; then
	echo "Exists: $path"
	return
  fi
  mkdir -p "$(dirname "$path")"
  printf "%s" "$*" >"$path"
  echo "Wrote: $path"
}

wait_healthy() {
  local name="$1" timeout="${2:-300}" start status
  start="$(date +%s)"
  echo "Waiting for HEALTHY: $name (timeout ${timeout}s)"
  while true; do
	status="$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null || echo 'unknown')"
	if [[ "$status" == "healthy" ]]; then
  	echo "$name is healthy."
  	return 0
	fi
	(( $(date +%s) - start > timeout )) && { docker logs "$name" --tail 200 || true; die "$name not healthy after ${timeout}s (last: $status)"; }
	sleep 2
  done
}

install_tcpdump() {
  local cname="$1"
  echo "Installing tcpdump in $cname..."
  if docker exec "$cname" sh -c 'command -v apk >/dev/null 2>&1'; then
	docker exec "$cname" sh -lc 'apk update && apk add --no-cache tcpdump'
  elif docker exec "$cname" sh -c 'command -v apt-get >/dev/null 2>&1'; then
	docker exec "$cname" sh -lc 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y tcpdump'
  else
	die "No package manager found in $cname; please install tcpdump manually."
  fi
}

start_capture_as1000() {
  local cname="$AS1000_NAME" pcap="$PCAP_IN_AS1000" pidf="$PID_AS1000"
  echo "Starting ICMPv6 capture on $cname → $pcap ..."
  docker exec "$cname" sh -lc "mkdir -p '$(dirname "$pcap")' && rm -f '$pcap' '$pidf' 2>/dev/null || true"
  docker exec -d "$cname" sh -lc "tcpdump -i any -U -w '$pcap' icmp6 >/dev/null 2>&1 & echo \$! >'$pidf'"
  sleep 1
  docker exec "$cname" sh -lc "[ -s '$pidf' ] && kill -0 \$(cat '$pidf') 2>/dev/null" || die "tcpdump failed to start on $cname"
  echo "tcpdump running on $cname (pid $(docker exec "$cname" sh -lc "cat '$pidf'"))"
}

stop_capture_as1000() {
  local cname="$AS1000_NAME" pidf="$PID_AS1000"
  echo "Stopping tcpdump on $cname ..."
  docker exec "$cname" sh -lc "kill -INT \$(cat '$pidf') 2>/dev/null || true"
}

verify_pcap_as1000() {
  local cname="$AS1000_NAME" pcap="$PCAP_IN_AS1000"
  docker exec "$cname" sh -lc "[ -f '$pcap' ] && [ \$(stat -c%s '$pcap') -gt 24 ]"
}

# ---------- 1) Create folder tree ----------
echo "Creating ${ROOT_DIR}/ structure..."
mkdir -p "${ROOT_DIR}"/{client,as1000,as1337,as2000,as3000}
mkdir -p "${HOST_CAP_DIR}"

# ---------- 2) Client Dockerfile ----------
write_file "${ROOT_DIR}/client/Dockerfile" "$(cat <<'EOF'
FROM alpine:3.20
RUN apk add --no-cache iputils tcpdump iproute2
CMD ["sh", "-lc", "sleep infinity"]
EOF
)"

# ---------- 3) FRR config files ----------
DAEMONS_CONTENT="$(cat <<'DAEMONS'
bgpd=yes
ospfd=no
ospf6d=no
ripd=no
ripngd=no
isisd=no
pimd=no
pim6d=no
ldpd=no
nhrpd=no
eigrpd=no
babeld=no
sharpd=no
pbrd=no
bfdd=no
fabricd=no
vrrpd=no
pathd=no
vtysh_enable=yes
zebra_options="  -A 127.0.0.1 -s 90000000"
bgpd_options="  -A 127.0.0.1"
DAEMONS
)"

for AS in as1000 as1337 as2000 as3000; do
  write_file "${ROOT_DIR}/${AS}/daemons" "$DAEMONS_CONTENT"
  write_file "${ROOT_DIR}/${AS}/vtysh.conf" "service integrated-vtysh-config
username frr nopassword
"
done

write_file "${ROOT_DIR}/as1000/frr.conf" "$(cat <<EOF
frr defaults traditional
service integrated-vtysh-config
hostname ${AS1000_NAME}
ipv6 forwarding
router bgp ${ASN_1000}
 bgp router-id 1.0.0.0
 no bgp default ipv4-unicast
 neighbor ${AS2000_1000_2000_IP} remote-as ${ASN_2000}
 neighbor ${AS1337_1000_1337_IP} remote-as ${ASN_1337}
 address-family ipv6 unicast
  network 2001:10:10:10::/64
  network 2001:12:12:12::/64
  network 2001:1:33:7::/64
  neighbor ${AS2000_1000_2000_IP} activate
  neighbor ${AS1337_1000_1337_IP} activate
 exit-address-family
line vty
EOF
)"

write_file "${ROOT_DIR}/as1337/frr.conf" "$(cat <<EOF
frr defaults traditional
service integrated-vtysh-config
hostname ${AS1337_NAME}
ipv6 forwarding
router bgp ${ASN_1337}
 bgp router-id 13.3.7.7
 no bgp default ipv4-unicast
 neighbor ${AS1000_1000_1337_IP} remote-as ${ASN_1000}
 address-family ipv6 unicast
  network 2001:1:33:7::/64
  neighbor ${AS1000_1000_1337_IP} activate
 exit-address-family
line vty
EOF
)"

write_file "${ROOT_DIR}/as2000/frr.conf" "$(cat <<EOF
frr defaults traditional
service integrated-vtysh-config
hostname ${AS2000_NAME}
ipv6 forwarding
router bgp ${ASN_2000}
 bgp router-id 2.0.0.0
 no bgp default ipv4-unicast
 neighbor ${AS1000_1000_2000_IP} remote-as ${ASN_1000}
 neighbor ${AS3000_2000_3000_IP} remote-as ${ASN_3000}
 address-family ipv6 unicast
  network 2001:12:12:12::/64
  network 2001:23:23:23::/64
  neighbor ${AS1000_1000_2000_IP} activate
  neighbor ${AS3000_2000_3000_IP} activate
 exit-address-family
line vty
EOF
)"

write_file "${ROOT_DIR}/as3000/frr.conf" "$(cat <<EOF
frr defaults traditional
service integrated-vtysh-config
hostname ${AS3000_NAME}
ipv6 forwarding
router bgp ${ASN_3000}
 bgp router-id 3.0.0.0
 no bgp default ipv4-unicast
 neighbor ${AS2000_2000_3000_IP} remote-as ${ASN_2000}
 address-family ipv6 unicast
  network 2001:23:23:23::/64
  neighbor ${AS2000_2000_3000_IP} activate
 exit-address-family
line vty
EOF
)"

# ---------- 4) docker-compose.yml with healthchecks + capture volume ----------
COMPOSE_PATH="${PROJECT_ROOT}/docker-compose.yml"
write_file "${COMPOSE_PATH}" "$(cat <<EOF
name: docker-bgp
services:
  client:
    build:
      context: ./docker-bgp/client
      dockerfile: Dockerfile
    container_name: ${CLIENT_NAME}
    cap_add: [NET_ADMIN, NET_RAW]
    networks:
      lan_client6:
        ipv6_address: "${CLIENT_LAN_IP}"
    healthcheck:
      test: ["CMD-SHELL", "ping -6 -c1 -W1 ${AS1000_LAN_IP} >/dev/null 2>&1 || ping -6 -c1 -W1 ${CLIENT_LAN_IP} >/dev/null 2>&1"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 45s
    restart: unless-stopped

  as1000:
    image: quay.io/frrouting/frr:10.4.1
    container_name: ${AS1000_NAME}
    cap_add: [NET_ADMIN, NET_RAW, NET_BIND_SERVICE, SYS_ADMIN]
    sysctls:
      net.ipv6.conf.all.forwarding: "1"
    volumes:
      - ./docker-bgp/as1000/frr.conf:/etc/frr/frr.conf:ro
      - ./docker-bgp/as1000/daemons:/etc/frr/daemons:ro
      - ./docker-bgp/as1000/vtysh.conf:/etc/frr/vtysh.conf:ro
      - ./captures:${CONTAINER_CAP_DIR}
    networks:
      link_1000_2000:
        ipv6_address: "${AS1000_1000_2000_IP}"
      link_1000_1337:
        ipv6_address: "${AS1000_1000_1337_IP}"
      lan_client6:
        ipv6_address: "${AS1000_LAN_IP}"
    healthcheck:
      test: ["CMD-SHELL", "pidof zebra >/dev/null && pidof bgpd >/dev/null && vtysh -c 'show running' >/dev/null 2>&1"]
      interval: 10s
      timeout: 5s
      retries: 18
      start_period: 60s
    restart: unless-stopped

  as1337:
    image: quay.io/frrouting/frr:10.4.1
    container_name: ${AS1337_NAME}
    cap_add: [NET_ADMIN, NET_RAW, NET_BIND_SERVICE, SYS_ADMIN]
    sysctls:
      net.ipv6.conf.all.forwarding: "1"
    volumes:
      - ./docker-bgp/as1337/frr.conf:/etc/frr/frr.conf:ro
      - ./docker-bgp/as1337/daemons:/etc/frr/daemons:ro
      - ./docker-bgp/as1337/vtysh.conf:/etc/frr/vtysh.conf:ro
    networks:
      link_1000_1337:
        ipv6_address: "${AS1337_1000_1337_IP}"
    healthcheck:
      test: ["CMD-SHELL", "pidof zebra >/dev/null && pidof bgpd >/dev/null && vtysh -c 'show running' >/dev/null 2>&1"]
      interval: 10s
      timeout: 5s
      retries: 18
      start_period: 60s
    restart: unless-stopped

  as2000:
    image: quay.io/frrouting/frr:10.4.1
    container_name: ${AS2000_NAME}
    cap_add: [NET_ADMIN, NET_RAW, NET_BIND_SERVICE, SYS_ADMIN]
    sysctls:
      net.ipv6.conf.all.forwarding: "1"
    volumes:
      - ./docker-bgp/as2000/frr.conf:/etc/frr/frr.conf:ro
      - ./docker-bgp/as2000/daemons:/etc/frr/daemons:ro
      - ./docker-bgp/as2000/vtysh.conf:/etc/frr/vtysh.conf:ro
    networks:
      link_1000_2000:
        ipv6_address: "${AS2000_1000_2000_IP}"
      link_2000_3000:
        ipv6_address: "${AS2000_2000_3000_IP}"
    healthcheck:
      test: ["CMD-SHELL", "pidof zebra >/dev/null && pidof bgpd >/dev/null && vtysh -c 'show running' >/dev/null 2>&1"]
      interval: 10s
      timeout: 5s
      retries: 18
      start_period: 60s
    restart: unless-stopped

  as3000:
    image: quay.io/frrouting/frr:10.4.1
    container_name: ${AS3000_NAME}
    cap_add: [NET_ADMIN, NET_RAW, NET_BIND_SERVICE, SYS_ADMIN]
    sysctls:
      net.ipv6.conf.all.forwarding: "1"
    volumes:
      - ./docker-bgp/as3000/frr.conf:/etc/frr/frr.conf:ro
      - ./docker-bgp/as3000/daemons:/etc/frr/daemons:ro
      - ./docker-bgp/as3000/vtysh.conf:/etc/frr/vtysh.conf:ro
    networks:
      link_2000_3000:
        ipv6_address: "${AS3000_2000_3000_IP}"
    healthcheck:
      test: ["CMD-SHELL", "pidof zebra >/dev/null && pidof bgpd >/dev/null && vtysh -c 'show running' >/dev/null 2>&1"]
      interval: 10s
      timeout: 5s
      retries: 18
      start_period: 60s
    restart: unless-stopped

networks:
  lan_client6:
    driver: bridge
    enable_ipv6: true
    ipam:
      driver: default
      config:
        - subnet: "2001:10:10:10::/64"

  link_1000_2000:
    driver: bridge
    enable_ipv6: true
    ipam:
      driver: default
      config:
        - subnet: "2001:12:12:12::/64"

  link_1000_1337:
    driver: bridge
    enable_ipv6: true
    ipam:
      driver: default
      config:
        - subnet: "2001:1:33:7::/64"

  link_2000_3000:
    driver: bridge
    enable_ipv6: true
    ipam:
      driver: default
      config:
        - subnet: "2001:23:23:23::/64"
EOF
)"

# ---------- 5) Build + Start + Wait Healthy ----------
cmd="$(compose_cmd)"
echo "Building images..."
$cmd build --pull
echo "Starting stack..."
$cmd up -d --force-recreate

wait_healthy "$AS1000_NAME" 300
wait_healthy "$AS1337_NAME" 300
wait_healthy "$AS2000_NAME" 300
wait_healthy "$AS3000_NAME" 300
wait_healthy "$CLIENT_NAME" 180

# ---------- 6) Set default IPv6 route on the client ----------
# Explicitly set default route to AS1000 on the LAN segment
docker exec "$CLIENT_NAME" sh -lc "ip -6 route replace default via ${AS1000_LAN_IP} dev eth0 || true"

# ---------- 7) Ensure tcpdump on AS1000, start capture, ping AS3000, stop, verify ----------
if ! docker exec "$AS1000_NAME" sh -lc 'command -v tcpdump >/dev/null 2>&1'; then
  install_tcpdump "$AS1000_NAME"
fi

# Start capture on AS1000 (PCAP goes straight to ./captures on host)
start_capture_as1000

# Ping **AS3000** only from Client
echo "Pinging ${TARGET_IPV6} from ${CLIENT_NAME} ..."
docker exec "$CLIENT_NAME" sh -lc "ping -6 -c 5 '${TARGET_IPV6}' || true"

# Stop capture and flush
stop_capture_as1000
sleep 2

# Verify pcap has content (>24 bytes)
verify_pcap_as1000 || die "PCAP not found or empty at $PCAP_IN_AS1000."

echo " PCAP saved to host: ${HOST_CAP_DIR}/$(basename "$PCAP_IN_AS1000")"
echo " Captured on AS1000 while Client ↔ AS3000 pings were sent."
echo "Done."


