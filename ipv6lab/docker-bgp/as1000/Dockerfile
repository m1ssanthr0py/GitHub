FROM frrouting/frr:latest
COPY frr.conf /etc/frr/frr.conf
COPY frr_patches/ /etc/frr/patches/
RUN chown frr:frr /etc/frr/frr.conf
CMD ["/usr/lib/frr/docker-start"]
