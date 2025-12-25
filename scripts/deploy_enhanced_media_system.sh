#!/bin/bash

# Enhanced Media System Deployment and Testing Script
# This script deploys and tests the new enhanced media preview system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root"
   exit 1
fi

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

log_info "Starting Enhanced Media System Deployment..."
log_info "Project directory: $PROJECT_DIR"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Check if virtual environment exists
    if [[ ! -d "venv" ]]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install required packages
    pip install -r requirements.txt
    
    # Install additional packages for enhanced media system
    pip install \
        redis[hiredis]==4.5.4 \
        pillow-heif==0.13.0 \
        opencv-python==4.8.1 \
        python-magic==0.4.27 \
        clamd==1.0.2 \
        webp==0.3.0 \
        av==9.2.0 \
        pytest==7.4.0 \
        pytest-asyncio==0.21.0 \
        pytest-cov==4.1.0
    
    log_success "Dependencies installed successfully"
}

# Function to setup Redis
setup_redis() {
    log_info "Setting up Redis..."
    
    if command_exists redis-server; then
        log_info "Redis is already installed"
    else
        log_info "Installing Redis..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y redis-server
        elif command_exists yum; then
            sudo yum install -y redis
        elif command_exists brew; then
            brew install redis
        else
            log_warning "Could not install Redis automatically. Please install Redis manually."
        fi
    fi
    
    # Start Redis if not running
    if ! pgrep -x "redis-server" > /dev/null; then
        log_info "Starting Redis..."
        redis-server --daemonize yes
        sleep 2
    fi
    
    # Test Redis connection
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is running and accessible"
    else
        log_error "Redis is not accessible"
        exit 1
    fi
}

# Function to setup ClamAV for virus scanning
setup_clamav() {
    log_info "Setting up ClamAV for virus scanning..."
    
    if command_exists clamscan; then
        log_info "ClamAV is already installed"
    else
        log_info "Installing ClamAV..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y clamav clamav-daemon
        elif command_exists yum; then
            sudo yum install -y clamav clamav-update
        elif command_exists brew; then
            brew install clamav
        else
            log_warning "Could not install ClamAV automatically. Virus scanning will be disabled."
            return
        fi
    fi
    
    # Update virus definitions
    if command_exists freshclam; then
        log_info "Updating virus definitions..."
        sudo freshclam
    fi
    
    log_success "ClamAV setup completed"
}

# Function to setup FFmpeg
setup_ffmpeg() {
    log_info "Setting up FFmpeg..."
    
    if command_exists ffmpeg; then
        log_info "FFmpeg is already installed"
    else
        log_info "Installing FFmpeg..."
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        elif command_exists yum; then
            sudo yum install -y epel-release
            sudo yum install -y ffmpeg
        elif command_exists brew; then
            brew install ffmpeg
        else
            log_warning "Could not install FFmpeg automatically. Please install FFmpeg manually."
        fi
    fi
    
    if command_exists ffmpeg; then
        log_success "FFmpeg is installed and accessible"
    else
        log_error "FFmpeg is not accessible"
        exit 1
    fi
}

# Function to create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    # Storage directories
    mkdir -p storage/content/thumbnails
    mkdir -p storage/content/videos
    mkdir -p storage/content/previews
    mkdir -p storage/content/qrcodes
    mkdir -p storage/content/markers
    
    # Cache directories
    mkdir -p /tmp/vertex_cache
    mkdir -p /tmp/vertex_validation
    
    # Logs directory
    mkdir -p logs
    
    # Set permissions
    chmod -R 755 storage/
    chmod -R 755 /tmp/vertex_cache
    chmod -R 755 /tmp/vertex_validation
    
    log_success "Directories created successfully"
}

# Function to run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    source venv/bin/activate
    
    # Check if alembic is configured
    if [[ ! -f "alembic.ini" ]]; then
        log_warning "Alembic not configured. Skipping migrations."
        return
    fi
    
    # Run migrations
    alembic upgrade head
    
    log_success "Database migrations completed"
}

# Function to run tests
run_tests() {
    log_info "Running enhanced media system tests..."
    
    source venv/bin/activate
    
    # Run unit tests
    log_info "Running unit tests..."
    python -m pytest tests/unit/ -v --cov=app/services --cov-report=html --cov-report=term-missing
    
    # Run integration tests
    log_info "Running integration tests..."
    python -m pytest tests/integration/test_enhanced_media_services.py -v --cov=app/services --cov-append --cov-report=html
    
    # Run specific enhanced media tests
    log_info "Running enhanced media service tests..."
    python -m pytest tests/integration/test_enhanced_media_services.py::TestEnhancedThumbnailService -v
    python -m pytest tests/integration/test_enhanced_media_services.py::TestEnhancedValidationService -v
    python -m pytest tests/integration/test_enhanced_media_services.py::TestEnhancedCacheService -v
    python -m pytest tests/integration/test_enhanced_media_services.py::TestReliabilityService -v
    
    log_success "All tests completed successfully"
}

# Function to create test data
create_test_data() {
    log_info "Creating test data..."
    
    source venv/bin/activate
    
    # Create test images
    python3 -c "
from PIL import Image
import os
import random

# Create test directory
test_dir = 'test_media'
os.makedirs(test_dir, exist_ok=True)

# Create different test images
for i, (size, color) in enumerate([
    ((800, 600), 'red'),
    ((1200, 800), 'blue'),
    ((640, 480), 'green'),
    ((1920, 1080), 'purple')
]):
    img = Image.new('RGB', size, color=color)
    img.save(f'{test_dir}/test_image_{i+1}_{color}.jpg', 'JPEG', quality=95)
    print(f'Created {test_dir}/test_image_{i+1}_{color}.jpg')

print('Test images created successfully')
"
    
    # Create test video using FFmpeg
    if command_exists ffmpeg; then
        mkdir -p test_media
        ffmpeg -f lavfi -i testsrc2=duration=10:size=640x480:rate=30 -c:v libx264 -t 10 test_media/test_video.mp4 -y
        log_success "Test video created"
    fi
    
    log_success "Test data created successfully"
}

# Function to start the application
start_application() {
    log_info "Starting the enhanced media application..."
    
    source venv/bin/activate
    
    # Check if application is configured
    if [[ ! -f ".env" ]]; then
        log_warning ".env file not found. Creating default configuration..."
        cat > .env << EOF
# Enhanced Media System Configuration
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite+aiosqlite:///./vertex_ar_enhanced.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
STORAGE_BASE_PATH=./storage/content
MEDIA_ROOT=./storage/content
LOCAL_STORAGE_PATH=./storage/content
LOCAL_STORAGE_PUBLIC_URL=http://localhost:8000/storage

# File limits
MAX_FILE_SIZE_PHOTO=10485760  # 10MB
MAX_FILE_SIZE_VIDEO=104857600  # 100MB

# Background tasks
MAX_BACKGROUND_WORKERS=4

# Security
SECRET_KEY=enhanced-media-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EOF
        log_success "Default .env file created"
    fi
    
    # Start the application in background
    log_info "Starting FastAPI application..."
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > logs/app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > .app.pid
    
    # Wait for application to start
    sleep 5
    
    # Check if application is running
    if curl -s http://localhost:8000/health > /dev/null; then
        log_success "Application started successfully (PID: $APP_PID)"
    else
        log_error "Application failed to start"
        tail -n 20 logs/app.log
        exit 1
    fi
}

# Function to run performance benchmarks
run_benchmarks() {
    log_info "Running performance benchmarks..."
    
    source venv/bin/activate
    
    # Create benchmark script
    cat > benchmark_enhanced_media.py << 'EOF'
import asyncio
import time
import aiohttp
import statistics
from pathlib import Path

async def benchmark_thumbnail_generation():
    """Benchmark thumbnail generation performance."""
    
    # Test image
    test_image = "test_media/test_image_1_red.jpg"
    
    async with aiohttp.ClientSession() as session:
        # Test single thumbnail generation
        start_time = time.time()
        async with session.post('http://localhost:8000/api/v2/media/thumbnails/generate', json={
            'file_path': test_image,
            'size': 'medium',
            'format': 'webp'
        }) as response:
            result = await response.json()
            single_time = time.time() - start_time
            print(f"Single thumbnail generation: {single_time:.3f}s")
        
        # Test batch thumbnail generation
        start_time = time.time()
        async with session.post('http://localhost:8000/api/v2/media/thumbnails/batch', json={
            'file_paths': [test_image],
            'sizes': ['small', 'medium', 'large'],
            'formats': ['webp', 'jpeg']
        }) as response:
            result = await response.json()
            batch_time = time.time() - start_time
            print(f"Batch thumbnail generation: {batch_time:.3f}s")
        
        # Test cache performance
        times = []
        for i in range(10):
            start_time = time.time()
            async with session.post('http://localhost:8000/api/v2/media/thumbnails/generate', json={
                'file_path': test_image,
                'size': 'medium',
                'format': 'webp'
            }) as response:
                result = await response.json()
                times.append(time.time() - start_time)
        
        avg_cache_time = statistics.mean(times)
        print(f"Average cached thumbnail access: {avg_cache_time:.3f}s")

async def benchmark_validation():
    """Benchmark file validation performance."""
    
    test_image = "test_media/test_image_1_red.jpg"
    
    async with aiohttp.ClientSession() as session:
        # Test basic validation
        start_time = time.time()
        async with session.post('http://localhost:8000/api/v2/media/validation/validate', json={
            'file_path': test_image,
            'validation_level': 'basic'
        }) as response:
            result = await response.json()
            basic_time = time.time() - start_time
            print(f"Basic validation: {basic_time:.3f}s")
        
        # Test comprehensive validation
        start_time = time.time()
        async with session.post('http://localhost:8000/api/v2/media/validation/validate', json={
            'file_path': test_image,
            'validation_level': 'comprehensive'
        }) as response:
            result = await response.json()
            comprehensive_time = time.time() - start_time
            print(f"Comprehensive validation: {comprehensive_time:.3f}s")

async def main():
    print("=== Enhanced Media System Benchmarks ===")
    
    try:
        await benchmark_thumbnail_generation()
        print()
        await benchmark_validation()
        
    except Exception as e:
        print(f"Benchmark failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    # Run benchmarks
    python benchmark_enhanced_media.py
    
    log_success "Performance benchmarks completed"
}

# Function to cleanup
cleanup() {
    log_info "Cleaning up..."
    
    # Stop application if running
    if [[ -f ".app.pid" ]]; then
        APP_PID=$(cat .app.pid)
        if ps -p $APP_PID > /dev/null; then
            kill $APP_PID
            log_info "Application stopped"
        fi
        rm -f .app.pid
    fi
    
    # Cleanup test files
    rm -rf test_media/
    rm -f benchmark_enhanced_media.py
    
    log_success "Cleanup completed"
}

# Function to show usage
show_usage() {
    echo "Enhanced Media System Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy      - Full deployment (install, setup, start)"
    echo "  test        - Run tests only"
    echo "  benchmark   - Run performance benchmarks"
    echo "  start       - Start application only"
    echo "  stop        - Stop application"
    echo "  cleanup     - Cleanup and stop"
    echo "  help        - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 deploy    # Full deployment"
    echo "  $0 test      # Run tests"
    echo "  $0 benchmark # Run benchmarks"
}

# Main execution
main() {
    case "${1:-deploy}" in
        "deploy")
            install_dependencies
            setup_redis
            setup_clamav
            setup_ffmpeg
            create_directories
            run_migrations
            create_test_data
            run_tests
            start_application
            run_benchmarks
            log_success "Enhanced Media System deployed successfully!"
            echo ""
            echo "🚀 Application is running at: http://localhost:8000"
            echo "📊 API Documentation: http://localhost:8000/docs"
            echo "🔍 Enhanced Media API: http://localhost:8000/api/v2/media"
            echo ""
            echo "To stop the application, run: $0 stop"
            ;;
        "test")
            run_tests
            ;;
        "benchmark")
            run_benchmarks
            ;;
        "start")
            start_application
            ;;
        "stop")
            cleanup
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Trap cleanup on script exit
trap cleanup EXIT

# Run main function
main "$@"