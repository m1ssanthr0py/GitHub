FROM alpine:3.20
RUN apk add --no-cache iputils tcpdump iproute2 docker-cli

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Make the script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# Use the script as entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]