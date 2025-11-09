FROM alpine:3.20
RUN apk add --no-cache iputils tcpdump iproute2

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["sh", "-lc", "sleep infinity"]