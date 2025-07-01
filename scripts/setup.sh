#!/bin/bash
# LocalContextMCP Setup Script

set -e

echo "🚀 Setting up LocalContextMCP..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is available
check_docker() {
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}✅ Docker and Docker Compose found${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker or Docker Compose not found${NC}"
        echo "Please install Docker and Docker Compose first"
        return 1
    fi
}

# Check if PostgreSQL is available locally
check_postgres() {
    if command -v psql &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL client found${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  PostgreSQL client not found (optional for local setup)${NC}"
        return 1
    fi
}

# Setup environment file
setup_env() {
    if [ ! -f .env ]; then
        echo -e "${BLUE}📝 Creating .env file from template...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ .env file created${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env file with your settings${NC}"
    else
        echo -e "${GREEN}✅ .env file already exists${NC}"
    fi
}

# Create virtual environment and install dependencies
setup_python() {
    echo -e "${BLUE}🐍 Setting up Python environment...${NC}"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

# Setup database
setup_database() {
    echo -e "${BLUE}🗄️  Setting up database...${NC}"
    
    read -p "Do you want to use Docker for PostgreSQL? (y/n): " use_docker
    
    if [[ $use_docker == "y" || $use_docker == "Y" ]]; then
        echo "Starting PostgreSQL with Docker..."
        docker-compose -f docker/docker-compose.yml up -d postgres
        echo "Waiting for PostgreSQL to be ready..."
        sleep 10
        
        # Apply schema
        docker-compose -f docker/docker-compose.yml exec postgres psql -U postgres -d localcontextmcp -f /docker-entrypoint-initdb.d/01-schema.sql
        echo -e "${GREEN}✅ Database setup complete${NC}"
    else
        if check_postgres; then
            read -p "Enter PostgreSQL database name (default: localcontextmcp): " db_name
            db_name=${db_name:-localcontextmcp}
            
            read -p "Enter PostgreSQL username (default: postgres): " db_user
            db_user=${db_user:-postgres}
            
            echo "Creating database if it doesn't exist..."
            createdb -U $db_user $db_name 2>/dev/null || echo "Database may already exist"
            
            echo "Applying database schema..."
            psql -U $db_user -d $db_name -f database/schema.sql
            echo -e "${GREEN}✅ Database setup complete${NC}"
        else
            echo -e "${RED}❌ PostgreSQL not available and Docker not chosen${NC}"
            echo "Please install PostgreSQL or use Docker option"
            exit 1
        fi
    fi
}

# Run tests
run_tests() {
    echo -e "${BLUE}🧪 Running tests...${NC}"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    python -m pytest tests/ -v
    echo -e "${GREEN}✅ Tests completed${NC}"
}

# Start the development server
start_dev_server() {
    echo -e "${BLUE}🚀 Starting development server...${NC}"
    
    read -p "Start development server? (y/n): " start_server
    
    if [[ $start_server == "y" || $start_server == "Y" ]]; then
        if [ -d "venv" ]; then
            source venv/bin/activate
        fi
        
        echo "Starting LocalContextMCP server..."
        echo "Server will be available at http://localhost:8080"
        echo "Health check: http://localhost:8080/health"
        echo "Press Ctrl+C to stop"
        
        python -m src.mcp.server
    fi
}

# Main setup flow
main() {
    echo -e "${BLUE}🎯 LocalContextMCP Setup${NC}"
    echo "This script will help you set up the LocalContextMCP server"
    echo ""
    
    # Check prerequisites
    check_docker
    
    # Setup steps
    setup_env
    setup_python
    setup_database
    
    echo ""
    echo -e "${GREEN}🎉 Setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your LM Studio and other settings"
    echo "2. Start LM Studio and load your preferred model"
    echo "3. Run the server:"
    echo "   - With Docker: docker-compose -f docker/docker-compose.yml up"
    echo "   - Locally: python -m src.mcp.server"
    echo ""
    echo "Documentation: README.md"
    echo "Health check: http://localhost:8080/health"
    echo ""
    
    start_dev_server
}

# Parse command line arguments
case "${1:-}" in
    "test")
        run_tests
        ;;
    "docker")
        check_docker
        docker-compose -f docker/docker-compose.yml up -d
        echo -e "${GREEN}✅ Docker containers started${NC}"
        ;;
    "dev")
        check_docker
        docker-compose -f docker/docker-compose.dev.yml up -d
        echo -e "${GREEN}✅ Development environment started${NC}"
        ;;
    "clean")
        echo "Cleaning up..."
        docker-compose -f docker/docker-compose.yml down -v 2>/dev/null || true
        docker-compose -f docker/docker-compose.dev.yml down -v 2>/dev/null || true
        rm -rf venv __pycache__ .pytest_cache
        echo -e "${GREEN}✅ Cleanup complete${NC}"
        ;;
    "help"|"--help"|"-h")
        echo "LocalContextMCP Setup Script"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  (no args)  Run full interactive setup"
        echo "  test       Run tests only"
        echo "  docker     Start with Docker Compose"
        echo "  dev        Start development environment"
        echo "  clean      Clean up containers and virtual environment"
        echo "  help       Show this help message"
        ;;
    *)
        main
        ;;
esac