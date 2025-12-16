# CANARY_STRING_PLACEHOLDER
import os
import yaml
from pathlib import Path

def test_cascade_recovery_report_exists():
    """Testing that cascading failure recovery report was created"""
    report_path = Path("/app/cascade_recovery_report.txt")
    assert report_path.exists(), "Cascade recovery report not found at /app/cascade_recovery_report.txt"

def test_report_documents_cascading_failures():
    """Test that report identifies all cascading failure components"""
    with open("/app/cascade_recovery_report.txt", "r") as f:
        content = f.read()
    
    # Check for all required report sections
    required_sections = [
        "CASCADING FAILURE ANALYSIS",
        "SSL CERTIFICATE RECOVERY", 
        "LDAP AUTHENTICATION REPAIR",
        "STORAGE CORRUPTION FIXES",
        "NETWORK POLICY RESOLUTION",
        "WEBHOOK PLUGIN RECOVERY",
        "VERIFICATION MATRIX",
        "PREVENTION MEASURES"
    ]
    
    for section in required_sections:
        assert section in content, f"Report must contain {section} section"
    
    # Check for specific technical details
    technical_terms = ["certificate chain", "ldap", "storage corruption", "webhook", "network policy"]
    for term in technical_terms:
        assert term.lower() in content.lower(), f"Report must mention {term}"

def test_ssl_certificate_chain_recovery():
    """Test that SSL certificate chain was properly rebuilt"""
    # Check that certificate files exist
    cert_files = [
        "/etc/ssl/registry/ca-root.crt",
        "/etc/ssl/registry/ca-intermediate.crt", 
        "/etc/ssl/registry/server.crt",
        "/etc/ssl/registry/server.key"
    ]
    
    for cert_file in cert_files:
        assert os.path.exists(cert_file), f"Certificate file {cert_file} should exist"
    
    # Check certificate permissions
    for crt_file in ["/etc/ssl/registry/ca-root.crt", "/etc/ssl/registry/ca-intermediate.crt", "/etc/ssl/registry/server.crt"]:
        stat_info = os.stat(crt_file)
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "644", f"Certificate {crt_file} should have 644 permissions, got {permissions}"
    
    # Check private key permissions - ALL private keys must have 600 and MUST exist
    for key_file in ["/etc/ssl/registry/ca-root.key", "/etc/ssl/registry/ca-intermediate.key", "/etc/ssl/registry/server.key"]:
        assert os.path.exists(key_file), f"Private key {key_file} must exist"
        key_stat = os.stat(key_file)
        key_perms = oct(key_stat.st_mode)[-3:]
        assert key_perms == "600", f"Private key {key_file} should have 600 permissions, got {key_perms}"
    
    # Verify certificates are not corrupted (basic format check)
    with open("/etc/ssl/registry/ca-root.crt", "r") as f:
        root_cert = f.read()
    assert "BEGIN CERTIFICATE" in root_cert, "Root certificate should be in PEM format"
    assert "END CERTIFICATE" in root_cert, "Root certificate should have proper PEM ending"
    assert "BEGIN CORRUPTED" not in root_cert, "Root certificate should not be corrupted"
    assert "corrupted" not in root_cert.lower(), "Root certificate should not contain corrupted content"
    
    # Verify certificate chain structure (root → intermediate → server)
    with open("/etc/ssl/registry/ca-intermediate.crt", "r") as f:
        intermediate_cert = f.read()
    assert "BEGIN CERTIFICATE" in intermediate_cert, "Intermediate certificate should be in PEM format"
    assert "END CERTIFICATE" in intermediate_cert, "Intermediate certificate should have proper PEM ending"
    
    with open("/etc/ssl/registry/server.crt", "r") as f:
        server_cert = f.read()
    assert "BEGIN CERTIFICATE" in server_cert, "Server certificate should be in PEM format"
    assert "END CERTIFICATE" in server_cert, "Server certificate should have proper PEM ending"
    
    # Verify complete certificate chain exists (root → intermediate → server)
    assert os.path.exists("/etc/ssl/registry/ca-root.crt"), "Root certificate must exist for complete chain"
    assert os.path.exists("/etc/ssl/registry/ca-intermediate.crt"), "Intermediate certificate must exist for complete chain"
    assert os.path.exists("/etc/ssl/registry/server.crt"), "Server certificate must exist for complete chain"

def test_storage_corruption_recovery():
    """Test that storage layer corruption was resolved"""
    # Verify registry user with uid 1000 exists
    import pwd
    try:
        user_info = pwd.getpwuid(1000)
        assert user_info.pw_uid == 1000, f"Registry user should have uid 1000, got {user_info.pw_uid}"
    except KeyError:
        assert False, "Registry user with uid 1000 does not exist"
    
    # Check storage directory permissions
    stat_info = os.stat("/var/lib/registry")
    permissions = oct(stat_info.st_mode)[-3:]
    assert permissions == "755", f"Storage directory should have 755 permissions, got {permissions}"
    
    # Check storage directory ownership
    assert stat_info.st_uid == 1000, f"Storage directory should be owned by uid 1000, got {stat_info.st_uid}"
    
    # Check storage index permissions
    index_stat = os.stat("/var/lib/registry/.index")
    index_perms = oct(index_stat.st_mode)[-3:]
    assert index_perms == "755", f"Storage index should have 755 permissions, got {index_perms}"
    
    # Check storage index ownership
    assert index_stat.st_uid == 1000, f"Storage index should be owned by uid 1000, got {index_stat.st_uid}"
    
    # Verify corrupted blobs were removed
    corrupted_blob_path = "/var/lib/registry/docker/registry/v2/blobs/sha256/ab/abc123"
    assert not os.path.exists(corrupted_blob_path), "Corrupted blob should be removed"
    
    # Verify corrupted index was removed
    corrupted_index = "/var/lib/registry/.index/manifests.db"
    assert not os.path.exists(corrupted_index), "Corrupted storage index should be removed"

def test_ldap_authentication_repair():
    """Test that LDAP authentication configuration was repaired"""
    ldap_config_path = "/etc/ldap/registry-auth.conf"
    assert os.path.exists(ldap_config_path), "LDAP configuration file should exist"
    
    with open(ldap_config_path, "r") as f:
        ldap_config = f.read()
    
    # Check LDAP config file permissions
    ldap_stat = os.stat(ldap_config_path)
    ldap_perms = oct(ldap_stat.st_mode)[-3:]
    assert ldap_perms == "644", f"LDAP config should have 644 permissions, got {ldap_perms}"
    
    # Check that LDAP config contains ALL required fields with exact values
    assert "host:" in ldap_config, "LDAP config should contain host field"
    assert "bind_dn:" in ldap_config, "LDAP config should contain bind_dn field"
    assert "localhost" in ldap_config, "LDAP config should use localhost server"
    assert "search_filter:" in ldap_config, "LDAP config should contain search_filter field"
    assert "tls_enabled:" in ldap_config, "LDAP config should contain tls_enabled field"
    assert "tls_enabled: false" in ldap_config, "LDAP config must have 'tls_enabled: false' exactly"
    assert "connection_pool_size:" in ldap_config, "LDAP config should contain connection_pool_size field"
    assert "connection_timeout:" in ldap_config, "LDAP config should contain connection_timeout field"
    assert "base_dn:" in ldap_config, "LDAP config should contain base_dn field"
    assert "bind_password:" in ldap_config, "LDAP config should contain bind_password field"
    assert "user_search_base:" in ldap_config, "LDAP config should contain user_search_base field"
    assert "group_search_base:" in ldap_config, "LDAP config should contain group_search_base field"
    assert "bind_timeout:" in ldap_config, "LDAP config should contain bind_timeout field"
    assert "search_timeout:" in ldap_config, "LDAP config should contain search_timeout field"
    
    # Check that corrupted content was removed
    assert "corrupted ldap config" not in ldap_config, "LDAP config should not contain original corrupted content"
    assert "corrupted_password_hash" not in ldap_config, "LDAP config should not contain corrupted password hash"
    assert "ldaps://ldap.registry.local:636" not in ldap_config, "LDAP config should not use unreachable LDAPS server"
    assert "registryUser" not in ldap_config, "LDAP config should not use custom registryUser objectClass"
    
    # Verify standard LDAP objectClass is used and search filter format
    assert "person" in ldap_config or "objectClass=person" in ldap_config, "LDAP config should use standard person objectClass"
    assert "(&(objectClass=person)" in ldap_config or "(objectClass=person)" in ldap_config, "LDAP search filter should use standard person objectClass format"

def test_network_policy_resolution():
    """Test that network policy conflicts were resolved"""
    # Check that conflicting iptables rules were removed
    iptables_rules = "/etc/iptables/rules.v4"
    assert not os.path.exists(iptables_rules), "Conflicting iptables rules should be removed"
    
    # Check DNS resolution fixes
    with open("/etc/hosts", "r") as f:
        hosts_content = f.read()
    
    # Check that ALL incorrect DNS mappings were removed
    assert "wrong.registry.local" not in hosts_content, "Incorrect DNS mapping wrong.registry.local should be removed"
    assert "ldap.registry.local" not in hosts_content, "Incorrect DNS mapping ldap.registry.local should be removed"
    assert "auth.registry.local" not in hosts_content, "Incorrect DNS mapping auth.registry.local should be removed"
    
    # Check that correct DNS mapping exists
    assert "registry.local" in hosts_content, "Correct DNS mapping should be present"
    assert "127.0.0.1" in hosts_content, "Localhost IP mapping should be present"
    
    # Verify no duplicate entries
    registry_lines = [line for line in hosts_content.split('\n') if 'registry.local' in line and line.strip()]
    assert len(registry_lines) == 1, f"Exactly one registry.local mapping should exist, found {len(registry_lines)}"
    
    # Verify DNS resolution works
    registry_line = registry_lines[0]
    assert "127.0.0.1" in registry_line and "registry.local" in registry_line, "registry.local must resolve to 127.0.0.1"

def test_webhook_plugin_recovery():
    """Test that webhook plugin corruption was resolved"""
    # Check that corrupted plugin was removed
    corrupted_plugin = "/opt/registry/plugins/webhook-auth.so"
    assert not os.path.exists(corrupted_plugin), "Corrupted webhook plugin should be removed"
    
    # Check that working plugin stub exists
    plugin_stub = "/opt/registry/plugins/webhook-auth.sh"
    if os.path.exists(plugin_stub):
        stat_info = os.stat(plugin_stub)
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "755", f"Plugin stub should be executable, got {permissions}"

def test_htpasswd_authentication_fallback():
    """Test that htpasswd authentication fallback was properly configured"""
    htpasswd_path = Path("/etc/docker/registry/htpasswd")
    assert htpasswd_path.exists(), "htpasswd file should exist as authentication fallback"
    
    # Check htpasswd file permissions
    htpasswd_stat = os.stat(htpasswd_path)
    htpasswd_perms = oct(htpasswd_stat.st_mode)[-3:]
    assert htpasswd_perms == "644", f"htpasswd file should have 644 permissions, got {htpasswd_perms}"
    
    with open(htpasswd_path, "r") as f:
        content = f.read().strip()
    
    assert ":" in content, "htpasswd should have username:hash format"
    assert "$2" in content, "htpasswd should use bcrypt format"
    lines = content.split("\n")
    assert len(lines) >= 1, "htpasswd should have at least one user entry"
    
    # Verify proper bcrypt format
    hash_part = content.split(":")[1]
    assert len(hash_part) > 50, "Bcrypt hash should be properly formatted"
    assert hash_part.startswith("$2a$") or hash_part.startswith("$2b$") or hash_part.startswith("$2y$"), "Must use proper bcrypt format"

def test_registry_config_simplified():
    """Test that registry config was simplified to remove cascading failure points"""
    config_path = "/etc/docker/registry/config.yml"
    
    # Check registry config file permissions
    config_stat = os.stat(config_path)
    config_perms = oct(config_stat.st_mode)[-3:]
    assert config_perms == "644", f"Registry config should have 644 permissions, got {config_perms}"
    
    with open(config_path, "r") as f:
        config_content = f.read()
        
    config_data = yaml.safe_load(config_content)
    
    # Check basic required sections
    assert "version" in config_data, "Config must have version"
    assert "storage" in config_data, "Config must have storage section"
    assert "http" in config_data, "Config must have http section"
    assert "auth" in config_data, "Config must have auth section"
    assert "health" in config_data, "Config must have health section"
    
    # Check exact log schema details
    log_config = config_data.get("log", {})
    assert "fields" in log_config, "Log config must have fields section"
    assert log_config["fields"].get("service") == "registry", "Log service must be 'registry'"
    assert log_config.get("level") == "info", "Log level must be 'info'"
    
    # Check exact health schema details
    health_config = config_data.get("health", {})
    assert "storagedriver" in health_config, "Health config must have storagedriver section"
    storagedriver_config = health_config["storagedriver"]
    assert storagedriver_config.get("enabled"), "Health storagedriver must be enabled"
    assert storagedriver_config.get("interval") == "10s", "Health interval must be '10s'"
    assert storagedriver_config.get("threshold") == 3, "Health threshold must be 3"
    
    # Verify external dependencies were removed
    assert "redis" not in config_content, "Redis dependency should be removed"
    assert "ldap" not in config_data.get("auth", {}), "LDAP auth should be removed from registry config"
    assert "middleware" not in config_data, "Webhook middleware should be removed"
    assert "notifications" not in config_data, "Notification endpoints should be removed"
    assert "proxy" not in config_data, "Proxy configuration should be removed"
    assert "reporting" not in config_data, "External reporting should be removed"
    
    # Check that registry binds to all interfaces
    http_addr = config_data.get("http", {}).get("addr", "")
    assert "0.0.0.0:5000" in http_addr, "Registry should bind to 0.0.0.0:5000 for external access"
    
    # Verify htpasswd fallback is configured
    auth_config = config_data.get("auth", {})
    assert "htpasswd" in auth_config, "htpasswd authentication should be configured"
    htpasswd_config = auth_config.get("htpasswd", {})
    assert "path" in htpasswd_config, "htpasswd path should be specified"
    assert "/etc/docker/registry/htpasswd" in htpasswd_config["path"], "htpasswd should point to correct file"

def test_cascading_failure_prevention():
    """Test that configuration prevents future cascading failures"""
    with open("/etc/docker/registry/config.yml", "r") as f:
        config_content = f.read()
        
    config_data = yaml.safe_load(config_content)
    
    # Verify storage configuration is resilient
    storage_config = config_data.get("storage", {})
    assert "filesystem" in storage_config, "Storage must use reliable filesystem driver"
    assert "delete" in storage_config, "Storage deletion should be enabled for GC recovery"
    assert storage_config["delete"]["enabled"], "Storage deletion must be enabled"
    
    # Verify HTTP configuration is secure but simple
    http_config = config_data.get("http", {})
    assert "addr" in http_config, "HTTP config must have addr field"
    assert "0.0.0.0:5000" in http_config["addr"], "HTTP must bind to all interfaces on port 5000"
    assert "headers" in http_config, "HTTP config must have security headers"
    
    # Verify both required HTTP headers are present
    headers = http_config.get("headers", {})
    assert "X-Content-Type-Options" in headers, "HTTP headers must include X-Content-Type-Options"
    assert "X-Frame-Options" in headers, "HTTP headers must include X-Frame-Options"
    assert headers["X-Content-Type-Options"] == ["nosniff"], "X-Content-Type-Options must be [nosniff]"
    assert headers["X-Frame-Options"] == ["DENY"], "X-Frame-Options must be [DENY]"
    
    # Verify YAML has no trailing spaces
    config_lines = config_content.split('\n')
    for i, line in enumerate(config_lines):
        assert not line.endswith(' '), f"YAML line {i+1} has trailing spaces: '{line}'"
        assert not line.endswith('\t'), f"YAML line {i+1} has trailing tabs: '{line}'"
    
    # Verify health checks are enabled
    health_config = config_data.get("health", {})
    assert "storagedriver" in health_config, "Health config must monitor storage driver"
    assert health_config["storagedriver"]["enabled"], "Storage driver health checks must be enabled"

def test_comprehensive_recovery_verification():
    """Test that all recovery components are properly verified"""
    with open("/app/cascade_recovery_report.txt", "r") as f:
        report_content = f.read()
    
    # Check verification matrix indicators
    verification_indicators = [
        "SSL certificate chain validates correctly with proper CA hierarchy and intermediate signing",
        "Storage layer accessible with proper permissions and clean index structure", 
        "Network policies allow registry traffic on all required ports without conflicts",
        "Registry configuration contains all required sections and proper bindings for production",
        "Authentication works with htpasswd fallback mechanism enabled and configured",
        "Storage integrity verified through checksum validation and corruption detection systems"
    ]
    
    for indicator in verification_indicators:
        assert indicator in report_content, f"Report must verify: {indicator}"
    
    # Check prevention measures are documented
    prevention_measures = [
        "automated certificate monitoring and renewal infrastructure",
        "comprehensive health checks with alerting and notification systems", 
        "continuous storage integrity validation processes and monitoring",
        "network policy validation framework implementation and enforcement",
        "cascading failure detection system with circuit breakers and recovery mechanisms"
    ]
    
    for measure in prevention_measures:
        assert measure in report_content.lower(), f"Report must include prevention measure: {measure}"
