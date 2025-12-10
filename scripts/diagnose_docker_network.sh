#!/bin/sh

# Docker Network Diagnostics Script
# POSIX-compliant script for diagnosing Docker Compose networking issues
# Usage: ./scripts/diagnose_docker_network.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project and network configuration
PROJECT_NAME="vertex-ar"
NETWORK_NAME="vertex_net"

# Helper functions
print_header() {
    echo ""
    echo "${BLUE}=== $1 ===${NC}"
    echo ""
}

print_success() {
    echo "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo "${RED}✗ $1${NC}"
}

print_info() {
    echo "ℹ $1"
}

# Main diagnostic script
main() {
    echo "${BLUE}Docker Network Diagnostics for Vertex AR Platform${NC}"
    echo "=================================================="
    
    # 1. Check Docker daemon
    print_header "Docker Daemon Status"
    if docker version >/dev/null 2>&1; then
        print_success "Docker daemon is running"
        docker --version
        docker compose version
    else
        print_error "Docker daemon is not accessible"
        exit 1
    fi
    
    # 2. List all networks
    print_header "Docker Networks Overview"
    echo "Available Docker networks:"
    docker network ls
    echo ""
    
    # 3. Check if vertex_net network exists
    if docker network ls | grep -q "$NETWORK_NAME"; then
        print_success "Network '$NETWORK_NAME' found"
    else
        print_warning "Network '$NETWORK_NAME' not found. Creating it..."
        docker network create "$NETWORK_NAME" || print_error "Failed to create network"
    fi
    
    # 4. Inspect vertex_net network
    print_header "Network '$NETWORK_NAME' Details"
    echo "Network configuration:"
    docker network inspect "$NETWORK_NAME" --format='{{json .}}' | python3 -m json.tool 2>/dev/null || docker network inspect "$NETWORK_NAME"
    echo ""
    
    # 5. List containers and their IPs
    print_header "Container Network Information"
    echo "Containers in '$NETWORK_NAME' network:"
    
    # Get all containers in the network
    CONTAINERS=$(docker network inspect "$NETWORK_NAME" --format='{{range .Containers}}{{.Name}} {{.IPv4Address}} {{end}}')
    
    if [ -n "$CONTAINERS" ]; then
        for container_info in $CONTAINERS; do
            # This is a bit tricky with sh, let's use a different approach
            echo ""
        done
        
        # Better approach: Use docker ps and filter
        echo ""
        echo "Running containers:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "network=$NETWORK_NAME" || {
            echo "No containers found in network '$NETWORK_NAME'"
            echo "All running containers:"
            docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        }
    else
        print_warning "No containers found in '$NETWORK_NAME' network"
    fi
    
    # 6. DNS resolution tests
    print_header "DNS Resolution Tests"
    
    # Check if nginx container exists and can resolve app
    if docker ps --format "{{.Names}}" | grep -q "nginx"; then
        echo "Testing DNS resolution from nginx container:"
        
        # Test nslookup for app service
        if docker compose exec -T nginx nslookup app 2>/dev/null; then
            print_success "nginx can resolve 'app' service"
        else
            print_warning "nginx cannot resolve 'app' service via nslookup"
            echo "Trying alternative DNS test..."
            if docker compose exec -T nginx getent hosts app 2>/dev/null; then
                print_success "nginx can resolve 'app' service via getent hosts"
            else
                print_error "nginx cannot resolve 'app' service"
            fi
        fi
        
        # Test nslookup for postgres service
        if docker compose exec -T nginx nslookup postgres 2>/dev/null; then
            print_success "nginx can resolve 'postgres' service"
        else
            print_warning "nginx cannot resolve 'postgres' service via nslookup"
        fi
        
        # Test nslookup for redis service
        if docker compose exec -T nginx nslookup redis 2>/dev/null; then
            print_success "nginx can resolve 'redis' service"
        else
            print_warning "nginx cannot resolve 'redis' service via nslookup"
        fi
    else
        print_warning "nginx container not running - skipping DNS tests"
    fi
    
    # 7. Cross-container connectivity tests
    print_header "Cross-Container Connectivity Tests"
    
    # Test connectivity from nginx to app
    if docker ps --format "{{.Names}}" | grep -q "nginx"; then
        echo "Testing connectivity from nginx to app:"
        if docker compose exec -T nginx curl -f -s -o /dev/null -w "%{http_code}" http://app:8000/api/health/status | grep -q "200"; then
            print_success "nginx can reach app health endpoint (HTTP 200)"
        else
            print_warning "nginx cannot reach app health endpoint"
            echo "Trying basic connectivity test..."
            if docker compose exec -T nginx curl -f -s -o /dev/null -w "%{http_code}" http://app:8000/ | grep -q "200\|404"; then
                print_success "nginx can reach app service (basic connectivity)"
            else
                print_error "nginx cannot reach app service"
            fi
        fi
        
        # Test connectivity to postgres (if possible)
        echo "Testing basic network connectivity to postgres:"
        if docker compose exec -T nginx nc -z -w3 postgres 5432 2>/dev/null; then
            print_success "nginx can connect to postgres port 5432"
        else
            print_warning "nginx cannot connect to postgres port 5432 (nc not available or service unreachable)"
        fi
        
        # Test connectivity to redis (if possible)
        echo "Testing basic network connectivity to redis:"
        if docker compose exec -T nginx nc -z -w3 redis 6379 2>/dev/null; then
            print_success "nginx can connect to redis port 6379"
        else
            print_warning "nginx cannot connect to redis port 6379 (nc not available or service unreachable)"
        fi
    else
        print_warning "nginx container not running - skipping connectivity tests"
    fi
    
    # 8. Service health status
    print_header "Service Health Status"
    echo "Checking health status of all services:"
    
    # Get health status from docker ps
    docker ps --format "table {{.Names}}\t{{.Status}}" --filter "network=$NETWORK_NAME" || {
        echo "All containers:"
        docker ps --format "table {{.Names}}\t{{.Status}}"
    }
    
    # 9. Network troubleshooting tips
    print_header "Troubleshooting Tips"
    echo "Common issues and solutions:"
    echo ""
    print_info "1. If services can't resolve each other:"
    echo "   - Ensure all services are on the same network ('$NETWORK_NAME')"
    echo "   - Check that service names in docker-compose.yml match the names used in code"
    echo "   - Restart the stack: docker compose down && docker compose up -d"
    echo ""
    print_info "2. If network doesn't exist:"
    echo "   - Create it manually: docker network create $NETWORK_NAME"
    echo "   - Or restart the stack to auto-create it"
    echo ""
    print_info "3. If health checks are failing:"
    echo "   - Check service logs: docker compose logs <service-name>"
    echo "   - Verify service dependencies are healthy"
    echo "   - Check environment variables and configuration"
    echo ""
    print_info "4. For detailed network debugging:"
    echo "   - Inspect network: docker network inspect $NETWORK_NAME"
    echo "   - Check container network settings: docker inspect <container-name>"
    echo "   - Test connectivity manually: docker compose exec <service> ping <other-service>"
    echo ""
    print_info "5. Port conflicts:"
    echo "   - Check what's using ports: netstat -tulpn | grep :8000"
    echo "   - Stop conflicting services or change ports in docker-compose.yml"
    echo ""
    
    # 10. Quick commands reference
    print_header "Quick Reference Commands"
    echo "Useful commands for network debugging:"
    echo ""
    echo "View all networks:"
    echo "  docker network ls"
    echo ""
    echo "Inspect vertex_net network:"
    echo "  docker network inspect $NETWORK_NAME"
    echo ""
    echo "Show container IPs:"
    echo "  docker network inspect $NETWORK_NAME --format='{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{\"\\n\"}}{{end}}'"
    echo ""
    echo "Test DNS from container:"
    echo "  docker compose exec nginx nslookup app"
    echo ""
    echo "Test connectivity:"
    echo "  docker compose exec nginx curl -f http://app:8000/api/health/status"
    echo ""
    echo "View service logs:"
    echo "  docker compose logs -f <service-name>"
    echo ""
    echo "Restart all services:"
    echo "  docker compose restart"
    echo ""
    echo "Recreate network:"
    echo "  docker compose down && docker network rm $NETWORK_NAME && docker compose up -d"
    echo ""
    
    print_success "Docker network diagnostics completed!"
    echo ""
    echo "${BLUE}If you're still experiencing issues, review the output above and check the service logs.${NC}"
}

# Run main function
main "$@"