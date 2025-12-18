#!/bin/sh

# Docker Network Diagnostics Script for Vertex AR Platform
# POSIX-compliant comprehensive network diagnostics for Docker Compose setup

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo "${BLUE}INFO: $1${NC}"
}

log_success() {
    echo "${GREEN}SUCCESS: $1${NC}"
}

log_warning() {
    echo "${YELLOW}WARNING: $1${NC}"
}

log_error() {
    echo "${RED}ERROR: $1${NC}" >&2
}

# Main diagnostic function
main() {
    log_info "Starting Docker Network Diagnostics for Vertex AR Platform"
    echo "==========================================================="
    
    # 1. Check Docker daemon status
    check_docker_daemon
    
    # 2. Check Docker Compose status
    check_docker_compose
    
    # 3. List Docker networks
    list_docker_networks
    
    # 4. Check container status
    check_container_status
    
    # 5. Check container IP addresses
    check_container_ips
    
    # 6. Test DNS resolution
    test_dns_resolution
    
    # 7. Test cross-container connectivity
    test_cross_container_connectivity
    
    # 8. Check service health status
    check_service_health
    
    # 9. Summary
    print_summary
    
    log_info "Docker Network Diagnostics completed"
}

# Check Docker daemon status
check_docker_daemon() {
    log_info "1. Checking Docker daemon status..."
    
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            log_success "Docker daemon is running"
        else
            log_error "Docker daemon is not accessible"
            return 1
        fi
    else
        log_error "Docker is not installed"
        return 1
    fi
}

# Check Docker Compose status
check_docker_compose() {
    log_info "2. Checking Docker Compose status..."
    
    if command -v docker-compose >/dev/null 2>&1; then
        log_success "docker-compose command is available"
        log_info "Docker Compose version: $(docker-compose --version)"
    elif docker compose version >/dev/null 2>&1; then
        log_success "docker compose plugin is available"
        log_info "Docker Compose version: $(docker compose version)"
    else
        log_error "Docker Compose is not installed"
        return 1
    fi
}

# List Docker networks
list_docker_networks() {
    log_info "3. Listing Docker networks..."
    
    if docker network ls | grep -q vertex_net; then
        log_success "vertex_net network found"
        docker network ls | grep vertex_net
    else
        log_warning "vertex_net network not found - it will be created on 'docker compose up'"
    fi
    
    log_info "All Docker networks:"
    docker network ls
}

# Check container status
check_container_status() {
    log_info "4. Checking container status..."
    
    if docker compose ps >/dev/null 2>&1; then
        log_info "Container status:"
        docker compose ps
    else
        log_warning "No containers found or docker-compose not initialized"
    fi
}

# Check container IP addresses
check_container_ips() {
    log_info "5. Checking container IP addresses..."
    
    # Get list of running containers
    containers=$(docker compose ps --format "json" 2>/dev/null | jq -r '.[].Name' 2>/dev/null || echo "")
    
    if [ -n "$containers" ]; then
        for container in $containers; do
            if ip=$(docker inspect "$container" 2>/dev/null | jq -r '.[0].NetworkSettings.Networks."vertex-ar_vertex_net".IPAddress' 2>/dev/null) && [ -n "$ip" ] && [ "$ip" != "null" ]; then
                echo "  $container: $ip"
            else
                log_warning "Could not get IP for $container"
            fi
        done
    else
        log_warning "No running containers found"
    fi
}

# Test DNS resolution
test_dns_resolution() {
    log_info "6. Testing DNS resolution between containers..."
    
    # Test if we can resolve service names from within containers
    containers=$(docker compose ps --format "json" 2>/dev/null | jq -r '.[].Name' 2>/dev/null | head -n 1)
    
    if [ -n "$containers" ]; then
        for container in $containers; do
            log_info "Testing DNS resolution from $container:"
            
            # Test resolving postgres
            if docker exec "$container" nslookup postgres >/dev/null 2>&1; then
                log_success "  Can resolve 'postgres' from $container"
            else
                log_warning "  Cannot resolve 'postgres' from $container"
            fi
            
            # Test resolving redis
            if docker exec "$container" nslookup redis >/dev/null 2>&1; then
                log_success "  Can resolve 'redis' from $container"
            else
                log_warning "  Cannot resolve 'redis' from $container"
            fi
            
            # Test resolving app
            if docker exec "$container" nslookup app >/dev/null 2>&1; then
                log_success "  Can resolve 'app' from $container"
            else
                log_warning "  Cannot resolve 'app' from $container"
            fi
            break
        done
    else
        log_warning "No running containers found for DNS testing"
    fi
}

# Test cross-container connectivity
test_cross_container_connectivity() {
    log_info "7. Testing cross-container connectivity..."
    
    # Test if app container can reach postgres on port 5432
    if docker compose ps app >/dev/null 2>&1 && docker compose ps postgres >/dev/null 2>&1; then
        if docker exec app nc -z postgres 5432 >/dev/null 2>&1; then
            log_success "App can connect to Postgres on port 5432"
        else
            log_warning "App cannot connect to Postgres on port 5432"
        fi
    else
        log_warning "App or Postgres container not running, skipping connectivity test"
    fi
    
    # Test if app container can reach redis on port 6379
    if docker compose ps app >/dev/null 2>&1 && docker compose ps redis >/dev/null 2>&1; then
        if docker exec app nc -z redis 6379 >/dev/null 2>&1; then
            log_success "App can connect to Redis on port 6379"
        else
            log_warning "App cannot connect to Redis on port 6379"
        fi
    else
        log_warning "App or Redis container not running, skipping connectivity test"
    fi
}

# Check service health status
check_service_health() {
    log_info "8. Checking service health status..."
    
    if docker compose ps --format "json" >/dev/null 2>&1; then
        log_info "Health status of services:"
        # Try to get health status in a portable way
        if command -v jq >/dev/null 2>&1; then
            docker compose ps --format "json" | jq -r '.[] | "  \(.Name): \(.Status)"' 2>/dev/null || echo "  Unable to parse health status"
        else
            docker compose ps
        fi
    else
        log_warning "Cannot get service health status"
    fi
}

# Print summary and troubleshooting tips
print_summary() {
    log_info "9. Summary and troubleshooting tips:"
    echo
    echo "COMMON ISSUES AND SOLUTIONS:"
    echo "============================"
    echo "1. If containers can't resolve each other by service name:"
    echo "   - Ensure all services are attached to the same network (vertex_net)"
    echo "   - Restart the services: docker compose down && docker compose up -d"
    echo
    echo "2. If containers have incorrect IP addresses:"
    echo "   - Check network configuration in docker-compose.yml"
    echo "   - Recreate network: docker compose down && docker network prune -f"
    echo
    echo "3. If health checks are failing:"
    echo "   - Check service logs: docker compose logs <service>"
    echo "   - Verify service configuration and dependencies"
    echo
    echo "4. If services aren't starting in the correct order:"
    echo "   - Check depends_on conditions in docker-compose.yml"
    echo "   - Ensure health checks are properly configured"
    echo
    echo "USEFUL COMMANDS FOR DEBUGGING:"
    echo "=============================="
    echo "• View container logs: docker compose logs <service>"
    echo "• Execute commands in container: docker exec -it <container> sh"
    echo "• Check network details: docker network inspect vertex-ar_vertex_net"
    echo "• List all containers: docker compose ps -a"
    echo "• View service dependencies: docker compose config --services"
    echo
}

# Run main function
main "$@"