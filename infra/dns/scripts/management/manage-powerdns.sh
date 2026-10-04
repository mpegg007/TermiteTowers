#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
#  %ccm_git_branch: main %
#  %ccm_git_object_id: infra/dns/scripts/management/manage-powerdns.sh:97 %
#  %ccm_git_author: CCM Maintainer %
#  %ccm_git_author_email: ccm@test %
#  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
#  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
#  %ccm_git_commit_count: 97 %
#  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: big update %
#  %ccm_git_modify_date: 2025-08-29 07:37:53 %
#  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
#  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_language_mode:  %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 659 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: service updates % 
# PowerDNS Management Script
# TermiteTowers Infrastructure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="powerdns-dev1.yml"
SERVICE_NAME="powerdns"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|test|setup}"
    echo ""
    echo "Commands:"
    echo "  start    - Start PowerDNS services"
    echo "  stop     - Stop PowerDNS services"
    echo "  restart  - Restart PowerDNS services"
    echo "  status   - Show service status"
    echo "  logs     - Show service logs"
    echo "  test     - Test DNS resolution"
    echo "  setup    - Initial setup and deployment"
    exit 1
}

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

check_requirements() {
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
}

start_services() {
    log "Starting PowerDNS services..."
    cd "$SCRIPT_DIR"
    docker compose -f "$COMPOSE_FILE" up -d
    
    log "Waiting for services to start..."
    sleep 10
    
    log "PowerDNS services started successfully"
    show_status
}

stop_services() {
    log "Stopping PowerDNS services..."
    cd "$SCRIPT_DIR"
    docker compose -f "$COMPOSE_FILE" down
    log "PowerDNS services stopped"
}

restart_services() {
    log "Restarting PowerDNS services..."
    stop_services
    sleep 5
    start_services
}

show_status() {
    log "PowerDNS Service Status:"
    cd "$SCRIPT_DIR"
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    log "Service URLs:"
    echo "  - PowerDNS API:    http://192.168.1.10:8081"
    echo "  - PowerDNS Admin:  http://192.168.1.10:9191"
    echo "  - DNS Service:     192.168.1.10:53 / 192.168.4.10:53"
}

show_logs() {
    log "PowerDNS Service Logs:"
    cd "$SCRIPT_DIR"
    docker compose -f "$COMPOSE_FILE" logs -f --tail=50
}

test_dns() {
    log "Testing DNS resolution..."
    
    # Test DNS service availability
    if dig @192.168.1.10 -p 53 google.com +timeout=5 +tries=1 > /dev/null 2>&1; then
        log "✓ DNS service is responding on 192.168.1.10:53"
    else
        warn "✗ DNS service not responding on 192.168.1.10:53"
    fi
    
    if dig @192.168.4.10 -p 53 google.com +timeout=5 +tries=1 > /dev/null 2>&1; then
        log "✓ DNS service is responding on 192.168.4.10:53"
    else
        warn "✗ DNS service not responding on 192.168.4.10:53"
    fi
    
    # Test API endpoint
    if curl -s http://192.168.1.10:8081/api/v1/servers/localhost > /dev/null 2>&1; then
        log "✓ PowerDNS API is accessible"
    else
        warn "✗ PowerDNS API not accessible"
    fi
    
    # Test web interface
    if curl -s http://192.168.1.10:9191 > /dev/null 2>&1; then
        log "✓ PowerDNS Admin web interface is accessible"
    else
        warn "✗ PowerDNS Admin web interface not accessible"
    fi
}

setup_deployment() {
    log "Setting up PowerDNS deployment structure..."
    
    # Create /srv/dev1 structure if it doesn't exist
    if [ ! -d "/srv/dev1/powerdns/docker" ]; then
        log "Creating /srv/dev1/powerdns/docker directory structure..."
        sudo mkdir -p /srv/dev1/powerdns/docker
    fi
    
    # Create symlinks
    log "Creating symlinks..."
    sudo ln -sf "$SCRIPT_DIR/$COMPOSE_FILE" "/srv/dev1/powerdns/docker/$COMPOSE_FILE"
    sudo ln -sf "$SCRIPT_DIR/schema.sql" "/srv/dev1/powerdns/docker/schema.sql"
    sudo ln -sf "$SCRIPT_DIR/manage-powerdns.sh" "/srv/dev1/powerdns/docker/manage-powerdns.sh"
    
    # Create data directories
    log "Creating data storage directories..."
    sudo mkdir -p /mnt/ai_storage/dns/powerdns-mysql
    sudo mkdir -p /mnt/ai_storage/dns/powerdns-admin-data
    
    log "Deployment structure created successfully"
    log "You can now manage PowerDNS from:"
    echo "  - Source:      $SCRIPT_DIR"
    echo "  - Runtime:     /srv/dev1/powerdns/docker"
    echo "  - Data:        /mnt/ai_storage/dns/powerdns-*"
}

# Main script logic
check_requirements

case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        test_dns
        ;;
    setup)
        setup_deployment
        ;;
    *)
        usage
        ;;
esac
