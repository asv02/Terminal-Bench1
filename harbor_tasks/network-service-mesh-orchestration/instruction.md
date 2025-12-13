Build an advanced service mesh orchestration platform with monitoring, scaling, and lifecycle management using only command-line tools and shell scripting.

Requirements:
1. Create the following shell scripts in /app/:
   - /app/orchestrator.sh: Main orchestration engine with lifecycle management
   - /app/mesh_controller.sh: Service mesh configuration and traffic routing
   - /app/scaler.sh: Service scaling and replica management
   - /app/monitor.sh: Real-time monitoring and metrics collection
   - /app/topology.sh: Network topology visualization and mapping

2. Create directory structure:
   - /app/monitoring/ for storing monitoring data and configurations (must exist and be a directory)

3. Service mesh functionality:
   - Enable service mesh with sidecar proxy configuration
   - Configure traffic routing between services (--route --from --to)
   - Enforce inter-service communication policies (--policies --communication)
   - Implement service-to-service authentication (--auth --service-to-service)

4. Service scaling and replicas:
   - Scale services to specified replica count (--scale SERVICE --replicas N)
   - List active replicas for a service (--replicas --list --service NAME)
   - Monitor replica health and status (--replicas --health --service NAME)
   - Support dynamic autoscaling based on load (--auto-scale --load-based --service NAME)

5. Lifecycle management:
   - Complete service lifecycle orchestration (--lifecycle --service NAME)
   - Graceful shutdown with timeout (--shutdown SERVICE --graceful --timeout N)
   - Service dependency checking (--check-dependencies --service NAME)
   - Automated rollback on deployment failures (--deploy --rollback-on-failure)

6. Monitoring and metrics:
   - Real-time metrics collection (--metrics --collect --realtime)
   - Performance dashboard display (--dashboard)
   - Metrics must include ALL 5 types with keywords: requests/sec, response time, error rate, throughput, latency
   - All metrics must show actual numeric values next to metric names, not placeholders
   - Each metric type must be clearly identifiable by keyword in the output

7. Network topology:
   - Visualize network topology (--visualize --output FILE)
   - Map service relationships (--relationships --map --output FILE)
   - Generate topology graphs showing service connections (must include connection indicators like arrows, links, or dependencies)
   - Track service dependencies and communication patterns
   - Output files must contain topology structure with nodes and connections

8. Configuration hot-reload:
   - Support configuration hot-reload without service restart (--reload-config)
   - Validate configuration changes before applying (--validate-config --config FILE)
     Expected output: "Configuration valid" or similar validation message
   - Rollback on invalid configuration (--rollback-config)
     Expected output: "Rollback to previous configuration" or similar rollback message

9. Comprehensive orchestration:
   - Run end-to-end orchestration tests (--comprehensive)
   - Integrate all components (mesh, scaling, monitoring, lifecycle) - output must show keywords from all 4 components
   - Validate complete workflow execution with clear indicators of each integrated component in output text

All scripts must be executable and handle command-line arguments properly.

Implementation Guide:

General Script Pattern:
```bash
#!/bin/bash
# Initialize variables
FLAG1=0
FLAG2=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --flag1) FLAG1=1; shift ;;
        --flag2) FLAG2="$2"; shift 2 ;;
        --test) TEST_MODE=1; shift ;;
        *) shift ;;
    esac
done

# Perform action
if [ "$FLAG1" = "1" ]; then
    echo "Performing action with $FLAG2"
fi
```

Directory Setup:
- Create /app/monitoring/ directory: mkdir -p /app/monitoring
- All scripts go in /app/ and must be executable

 Hints:

1. /app/orchestrator.sh - Main orchestration engine:
   Flags: --lifecycle, --service NAME, --shutdown SERVICE, --graceful, --timeout N, 
          --check-dependencies, --reload-config, --validate, --validate-config, --rollback-config,
          --config FILE, --deploy, --rollback-on-failure, --comprehensive, --test
   
   Examples:
   - Lifecycle: echo numbered stages like "1. Deployed service", "2. Monitored", "3. Scaled"
   - Hot-reload with validation: Check if CONFIG_FILE contains "invalid" string in filename
     If invalid: echo "Configuration validation failed", "Invalid configuration", "Rollback"
     If valid: echo "Configuration validation passed", "Hot-reload completed"
   - Deploy with rollback: echo "Deploying", "Rollback mechanism enabled", "Recovery"
   - Comprehensive: Must call all 4 component scripts (mesh, scaler, monitor, lifecycle)

2. /app/mesh_controller.sh - Service mesh configuration:
   Flags: --enable, --route, --from SERVICE, --to SERVICE, --policies, 
          --communication, --auth, --service-to-service, --test
   
   Examples:
   - Enable mesh: echo "Deploying sidecar proxies", "inter-service communication" (both required)
   - Policies: echo "policy rules", "traffic control", "inter-service access" (need 2+ keywords)
   - Auth: echo "TLS certificates", "mTLS authentication", "service-to-service" (need 2+ keywords)

3. /app/scaler.sh - Service scaling:
   Flags: --scale SERVICE, --replicas N, --list, --auto-scale, 
          --load-based, --service NAME, --test
   
   Examples:
   - Scale: echo "Scaling service to N replicas", loop to show each replica number
   - Auto-scale: echo "auto-scale policy", "load thresholds", "CPU threshold: 70%" (need 3+ keywords)

4. /app/monitor.sh - Monitoring and metrics:
   Flags: --dashboard, --metrics, --collect, --realtime, --replicas, 
          --health, --service NAME, --test
   
   Examples:
   - Dashboard: echo service status with replica counts and numeric metrics values
   - Metrics: echo all 5 types: "Requests per second: 1,245", "response time: 42ms", etc.
   - Replica health: echo "Replica 1: Status=Ready, Health=Alive", use 3+ keywords: 
     health, status, replica, alive, ready

5. /app/topology.sh - Network topology:
   Flags: --visualize, --output FILE, --relationships, --map
   
   Examples:
   - Write to output file with: service nodes, connections arrows (->), network info
   - Include 2+ keywords: service, node, connection, topology, relationship, depends

Critical Keywords for Tests:
- Use exact keywords mentioned in hints (e.g., "policy", "traffic", "inter-service")
- Include numeric values where specified (requests/sec, CPU %, etc.)
- Echo multiple relevant keywords per feature (tests check for 2-3 keywords)

Common Patterns:
- Always support --test flag for test mode
- Use [[ "$CONFIG_FILE" == *"invalid"* ]] to check for "invalid" in filename
- Create output files with echo "content" > "$OUTPUT_FILE"
- Use loops for replicas: for i in $(seq 1 $N); do echo "Replica $i"; done
