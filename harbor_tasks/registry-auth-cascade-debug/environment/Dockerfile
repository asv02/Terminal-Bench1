# CANARY_STRING_PLACEHOLDER
FROM ubuntu:22.04

WORKDIR /app

# Debug: Show what we're starting with
RUN echo "=== DOCKERFILE DEBUG START ===" && pwd && ls -la

# Install packages with debug output
RUN echo "=== INSTALLING PACKAGES ===" && apt-get update && apt-get install -y openssl curl && rm -rf /var/lib/apt/lists/* && echo "=== PACKAGES INSTALLED ==="

# Create minimal directory structure
RUN echo "=== CREATING DIRECTORIES ===" && mkdir -p /etc/docker/registry /var/lib/registry /var/lib/registry/.index /etc/ssl/registry /etc/ldap /opt/registry/plugins /etc/iptables && echo "=== DIRECTORIES CREATED ==="

# Create minimal corrupted files that Oracle will fix
RUN echo "=== CREATING CORRUPTED FILES ===" \
    && echo "corrupted" > /etc/ssl/registry/ca-root.crt \
    && echo "corrupted" > /etc/ssl/registry/ca-intermediate.crt \
    && echo "corrupted" > /etc/ssl/registry/server.crt \
    && echo "corrupted" > /etc/ssl/registry/server.key \
    && echo "corrupted ldap config" > /etc/ldap/registry-auth.conf \
    && echo "corrupted plugin" > /opt/registry/plugins/webhook-auth.so \
    && echo "corrupted rules" > /etc/iptables/rules.v4 \
    && mkdir -p /var/lib/registry/docker/registry/v2/blobs/sha256/ab/abc123 \
    && echo "corrupted" > /var/lib/registry/docker/registry/v2/blobs/sha256/ab/abc123/data \
    && echo "corrupted" > /var/lib/registry/.index/manifests.db \
    && echo "=== CORRUPTED FILES CREATED ==="

# Set wrong permissions
RUN chmod 700 /var/lib/registry /var/lib/registry/.index

# Create minimal broken config
RUN echo "=== CREATING CONFIG ===" \
    && printf 'version: 0.1\nlog:\n  level: debug\nstorage:\n  filesystem:\n    rootdirectory: /var/lib/registry\nhttp:\n  addr: 127.0.0.1:5000\nauth:\n  htpasswd:\n    realm: registry-realm\n    path: /etc/docker/registry/htpasswd' > /etc/docker/registry/config.yml \
    && echo "=== CONFIG CREATED ===" \
    && echo "=== DOCKERFILE COMPLETED SUCCESSFULLY ===" \
    && ls -la /etc/docker/registry/ \
    && echo "=== FINAL DEBUG END ==="