#!/bin/bash
# scripts/run_verification_quick.sh
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if command succeeded
check_status() {
    if [ $? -eq 0 ]; then
        print_status $GREEN "✅ $1"
    else
        print_status $RED "❌ $1"
        exit 1
    fi
}

print_status $YELLOW "🚀 Starting Quick Storage Verification..."
echo "======================================================================"

# 1. Unit Tests
print_status $BLUE "📋 Running Unit Tests..."
PYTHONPATH=/home/engine/project pytest tests/unit/test_storage_providers.py -v --tb=short
check_status "Unit Tests completed"

# 2. Integration Tests
print_status $BLUE "🔗 Running Integration Tests..."
PYTHONPATH=/home/engine/project pytest tests/integration/test_storage_integration.py -v --tb=short
check_status "Integration Tests completed"

# 3. Storage Provider Test
print_status $BLUE "🗄️ Testing Storage Provider..."
PYTHONPATH=/home/engine/project python -c "
import tempfile
import os
os.environ['STORAGE_BASE_PATH'] = tempfile.mkdtemp()
from app.services.storage.factory import StorageProviderFactory
provider = StorageProviderFactory.create_provider('local_disk', {'base_path': os.environ['STORAGE_BASE_PATH']})
print('✅ Local storage provider created successfully')
print(f'Provider type: {type(provider).__name__}')
"
check_status "Storage Provider Test completed"

echo "======================================================================"
print_status $GREEN "✨ Quick verification completed successfully!"
echo ""
print_status $BLUE "📚 For full verification, run: ./scripts/run_verification.sh"