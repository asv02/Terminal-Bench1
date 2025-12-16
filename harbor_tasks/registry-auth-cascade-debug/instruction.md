# CANARY_STRING_PLACEHOLDER
# Container Registry Cascading Failure Recovery

## Task Description

A production Docker registry has suffered a cascading failure involving multiple interconnected systems. The registry appears to be running but exhibits complex failure patterns across SSL certificates, LDAP authentication, storage corruption, network policies, and webhook plugins.

## Critical System State

The registry environment contains corrupted components:
- **Primary registry config**: `/etc/docker/registry/config.yml` (broken YAML structure)
- **SSL certificate chain**: `/etc/ssl/registry/` (corrupted CA hierarchy with invalid signatures)
- **LDAP config**: `/etc/ldap/registry-auth.conf` (custom schema with non-standard attributes)
- **Storage backends**: Multiple corrupted storage layers with checksum mismatches
- **Webhook plugin**: `/opt/registry/plugins/webhook-auth.so` (corrupted binary with invalid symbols)
- **Network policies**: Conflicting iptables rules and DNS resolution failures
- **Storage index**: Memory-mapped corruption in `/var/lib/registry/.index/manifests.db`

## Failure Analysis Requirements

You must diagnose the root cause of cascading failures and implement comprehensive recovery procedures. The failures are interconnected - SSL certificate corruption triggered authentication failures, which led to storage access issues, network policy conflicts, and webhook plugin corruption.

## MANDATORY Recovery Tasks

### 1. SSL Certificate Chain Recovery (PASS/FAIL CRITERION)
**REQUIRED ACTIONS:**
- Create ALL certificate files: `/etc/ssl/registry/ca-root.crt`, `/etc/ssl/registry/ca-intermediate.crt`, `/etc/ssl/registry/server.crt`
- Create ALL private key files: `/etc/ssl/registry/ca-root.key`, `/etc/ssl/registry/ca-intermediate.key`, `/etc/ssl/registry/server.key`
- Set EXACT permissions: certificate files (.crt) 644, private key files (.key) 600
- Ensure PEM format with "BEGIN CERTIFICATE" headers
- Root certificate MUST NOT contain "BEGIN CORRUPTED" text

**VALIDATION CRITERIA:**
- All 6 certificate files must exist: ca-root.crt, ca-root.key, ca-intermediate.crt, ca-intermediate.key, server.crt, server.key
- Certificate files (.crt) MUST have exactly 644 permissions
- ALL private key files (.key) MUST have exactly 600 permissions
- Root certificate must be valid PEM format
- Certificate chain must be complete (root → intermediate → server)

### 2. LDAP Authentication Repair (PASS/FAIL CRITERION)
**REQUIRED ACTIONS:**
- Create `/etc/ldap/registry-auth.conf` with MANDATORY fields:
  - `host:` field containing "localhost" 
  - `bind_dn:` field with service account DN
  - `base_dn:` field with directory base
  - `bind_password:` field with authentication password
  - `user_search_base:` field for user directory location
  - `group_search_base:` field for group directory location
  - `connection_pool_size:` field for connection management
  - `connection_timeout:` field for timeout settings
  - `bind_timeout:` field for connection binding timeout
  - `search_timeout:` field for LDAP search operations timeout
  - `search_filter:` using standard objectClass (NOT registryUser)
  - `tls_enabled:` set to false
- Set LDAP config file permissions to exactly 644
- Remove ALL corrupted content including "corrupted ldap config"
- Configure htpasswd fallback with proper bcrypt hash ($2a$/$2b$/$2y$ prefix, >50 chars)

**VALIDATION CRITERIA:**
- LDAP config file must exist and contain "host:", "bind_dn:", "base_dn:", and "bind_password:" fields
- Must contain "localhost" in host field
- Must contain "tls_enabled: false" exactly
- Must contain "search_filter:" with standard LDAP filter format
- Must contain "connection_pool_size:" and "connection_timeout:" fields
- Must contain "user_search_base:" field for user directory location
- Must contain "group_search_base:" field for group directory location
- Must contain "bind_timeout:" field for connection binding timeout
- Must contain "search_timeout:" field for LDAP search operations timeout
- Must use "person" objectClass (not "registryUser")
- Must NOT contain "corrupted ldap config" text
- htpasswd file must have proper bcrypt format with correct prefix
- LDAP config must have exactly 644 permissions

### 3. Storage Corruption Recovery (PASS/FAIL CRITERION)
**REQUIRED ACTIONS:**
- Create registry user with uid 1000 if it doesn't exist
- Set directory permissions to exactly 755 for `/var/lib/registry` and `/var/lib/registry/.index`
- Set ownership to registry user (uid 1000) for both storage directories
- Remove corrupted blob: `/var/lib/registry/docker/registry/v2/blobs/sha256/ab/abc123`
- Delete corrupted index: `/var/lib/registry/.index/manifests.db`
- Create clean storage structure with proper directory hierarchy

**VALIDATION CRITERIA:**
- Storage directories MUST have exactly 755 permissions
- Corrupted blob path must NOT exist
- Corrupted index file must NOT exist
- Storage directory must be owned by registry user (uid 1000)
- Storage index directory must be owned by registry user (uid 1000)

### 4. Network Policy Resolution (PASS/FAIL CRITERION)
**REQUIRED ACTIONS:**
- Remove conflicting iptables rules file: `/etc/iptables/rules.v4`
- Clean DNS resolution by removing ALL wrong entries: `wrong.registry.local`, `ldap.registry.local`, `auth.registry.local`
- Remove any existing registry.local entries to prevent duplicates
- Add correct mapping: `127.0.0.1 registry.local`

**VALIDATION CRITERIA:**
- iptables rules file must NOT exist
- /etc/hosts must NOT contain "wrong.registry.local", "ldap.registry.local", or "auth.registry.local"
- /etc/hosts MUST contain "registry.local"
- /etc/hosts must NOT contain duplicate registry.local entries
- DNS resolution must work for registry.local (resolvable to 127.0.0.1)

### 5. Webhook Plugin Recovery (PASS/FAIL CRITERION)
**REQUIRED ACTIONS:**
- MANDATORY: Remove corrupted plugin binary `/opt/registry/plugins/webhook-auth.so`
- Optional: Create functional stub at `/opt/registry/plugins/webhook-auth.sh` with 755 permissions

**VALIDATION CRITERIA:**
- Corrupted webhook plugin binary must NOT exist
- If plugin stub created, must have exactly 755 permissions

### 6. Registry Configuration Rebuild (PASS/FAIL CRITERION)
**REQUIRED STRUCTURE - ALL SECTIONS MANDATORY:**
```yaml
version: 0.1
log:
  fields:
    service: registry
  level: info
storage:
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
http:
  addr: 0.0.0.0:5000
  headers:
    X-Content-Type-Options: [nosniff]
    X-Frame-Options: [DENY]
auth:
  htpasswd:
    realm: registry-realm
    path: /etc/docker/registry/htpasswd
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
```

**ADDITIONAL REQUIREMENTS:**
- Set registry config file permissions to exactly 644
- Set htpasswd file permissions to exactly 644
- Ensure YAML syntax is valid with no trailing spaces

**VALIDATION CRITERIA:**
- ALL sections (version, log, storage, http, auth, health) are MANDATORY
- Registry config file MUST have exactly 644 permissions
- htpasswd file MUST have exactly 644 permissions
- Log fields service MUST be "registry" and level MUST be "info"
- Health interval MUST be "10s" and threshold MUST be 3
- HTTP headers MUST include both X-Content-Type-Options AND X-Frame-Options
- Must NOT contain: redis, ldap auth, middleware, notifications, proxy, reporting
- HTTP addr MUST be "0.0.0.0:5000"
- Storage delete MUST be enabled
- Health storagedriver MUST be enabled
- Config YAML must be valid (no syntax errors or trailing spaces)

## MANDATORY Recovery Report (PASS/FAIL CRITERION)

Create `/app/cascade_recovery_report.txt` with ALL 8 REQUIRED SECTIONS:

### 1. CASCADING FAILURE ANALYSIS (MANDATORY)
Root cause analysis explaining how SSL certificate corruption triggered the cascade of failures across authentication, storage, network, and webhook systems.

### 2. SSL CERTIFICATE RECOVERY (MANDATORY)
Document the certificate chain rebuilding process, including root CA, intermediate CA, and server certificate generation with proper permissions.

### 3. LDAP AUTHENTICATION REPAIR (MANDATORY)
Detail the LDAP backend restoration, including configuration fixes and htpasswd fallback implementation.

### 4. STORAGE CORRUPTION FIXES (MANDATORY)
Describe storage layer recovery procedures, permission fixes, and corrupted data removal.

### 5. NETWORK POLICY RESOLUTION (MANDATORY)
Explain network connectivity restoration, iptables cleanup, and DNS resolution fixes.

### 6. WEBHOOK PLUGIN RECOVERY (MANDATORY)
Document plugin repair process and configuration simplification.

### 7. VERIFICATION MATRIX (MANDATORY)
MUST include these EXACT phrases VERBATIM in the report text:
- "SSL certificate chain validates correctly with proper CA hierarchy and intermediate signing"
- "Storage layer accessible with proper permissions and clean index structure"
- "Network policies allow registry traffic on all required ports without conflicts"
- "Registry configuration contains all required sections and proper bindings for production"
- "Authentication works with htpasswd fallback mechanism enabled and configured"
- "Storage integrity verified through checksum validation and corruption detection systems"

These phrases must appear word-for-word in your VERIFICATION MATRIX section.

### 8. PREVENTION MEASURES (MANDATORY)
MUST include these EXACT terms VERBATIM in the report text:
- "automated certificate monitoring and renewal infrastructure"
- "comprehensive health checks with alerting and notification systems"
- "continuous storage integrity validation processes and monitoring"
- "network policy validation framework implementation and enforcement"
- "cascading failure detection system with circuit breakers and recovery mechanisms"

These terms must appear word-for-word in your PREVENTION MEASURES section.

## Validation Matrix

The solution will be validated against these tested criteria:
-  SSL certificate chain recovery (proper files, permissions, PEM format)
-  LDAP configuration repair (all required fields, person objectClass)
-  Storage corruption fixes (permissions, corrupted file removal)
-  Network policy resolution (DNS cleanup, iptables removal)
-  Webhook plugin recovery (binary removal, stub creation)
-  Registry configuration completeness (all 6 mandatory sections)
-  Recovery report documentation (all 8 required sections)
-  Verification matrix phrases (6 exact phrases required)
-  Prevention measures terminology (5 exact terms required)
-  File permission accuracy (644/600/755 as specified)
-  Authentication fallback (htpasswd with bcrypt format)
-  Configuration hardening (dependency elimination)

## Critical Success Factors

1. **Cascading Failure Root Cause Analysis**: Must trace failure propagation from SSL→LDAP→Storage→Network→Webhook
2. **SSL Certificate Chain Recovery**: Generate proper certificate files with correct permissions
3. **LDAP Configuration Repair**: Create complete config with all required fields
4. **Storage Corruption Recovery**: Fix permissions and remove corrupted files
5. **Network Policy Resolution**: Clean DNS entries and remove iptables conflicts
6. **Authentication Simplification**: Remove plugin dependencies, configure htpasswd fallback
7. **Registry Configuration**: Create complete YAML with all mandatory sections
8. **Comprehensive Documentation**: Include all 8 required report sections with exact phrases

