#!/bin/bash

# Local DeepSeek Setup Script
# Helps set up DeepSeek to run locally instead of using remote API

set -e

echo "🚀 Setting up DeepSeek locally..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

print_header "DeepSeek Local Setup Options"

echo ""
echo "Choose your preferred method to run DeepSeek locally:"
echo ""
echo "1. Ollama (Recommended - Easy setup)"
echo "2. vLLM (High performance)"
echo "3. Text Generation WebUI (User-friendly interface)"
echo "4. Docker with TGI (Hugging Face Text Generation Inference)"
echo "5. Skip DeepSeek setup (use only Granite)"
echo ""

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        print_header "Setting up DeepSeek with Ollama..."
        
        # Check if Ollama is installed
        if ! command -v ollama &> /dev/null; then
            print_status "Installing Ollama..."
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
        
        print_status "Pulling DeepSeek model..."
        ollama pull deepseek-coder:6.7b
        
        print_status "Creating Ollama service for port 8000..."
        cat > start_deepseek_ollama.sh << 'EOF'
#!/bin/bash
export OLLAMA_HOST=0.0.0.0:8000
ollama serve &
sleep 5
ollama run deepseek-coder:6.7b
EOF
        chmod +x start_deepseek_ollama.sh
        
        print_status "✅ DeepSeek with Ollama setup complete!"
        print_status "Run: ./start_deepseek_ollama.sh to start DeepSeek on port 8000"
        ;;
        
    2)
        print_header "Setting up DeepSeek with vLLM..."
        
        print_status "Installing vLLM..."
        pip install vllm
        
        print_status "Creating vLLM startup script..."
        cat > start_deepseek_vllm.sh << 'EOF'
#!/bin/bash
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/deepseek-coder-6.7b-instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name deepseek-coder
EOF
        chmod +x start_deepseek_vllm.sh
        
        print_status "✅ vLLM setup complete!"
        print_status "Run: ./start_deepseek_vllm.sh to start DeepSeek on port 8000"
        print_warning "Note: First run will download the model (several GB)"
        ;;
        
    3)
        print_header "Setting up Text Generation WebUI..."
        
        print_status "Cloning Text Generation WebUI..."
        if [ ! -d "text-generation-webui" ]; then
            git clone https://github.com/oobabooga/text-generation-webui.git
        fi
        
        cd text-generation-webui
        
        print_status "Installing dependencies..."
        ./start_linux.sh --api --api-port 8000 --model deepseek-ai/deepseek-coder-6.7b-instruct
        
        print_status "Creating startup script..."
        cat > ../start_deepseek_webui.sh << 'EOF'
#!/bin/bash
cd text-generation-webui
python server.py --api --api-port 8000 --model deepseek-ai/deepseek-coder-6.7b-instruct
EOF
        chmod +x ../start_deepseek_webui.sh
        
        cd ..
        
        print_status "✅ Text Generation WebUI setup complete!"
        print_status "Run: ./start_deepseek_webui.sh to start DeepSeek on port 8000"
        ;;
        
    4)
        print_header "Setting up DeepSeek with Docker TGI..."
        
        print_status "Creating Docker setup..."
        cat > docker-compose.deepseek.yml << 'EOF'
version: '3.8'
services:
  deepseek:
    image: ghcr.io/huggingface/text-generation-inference:latest
    container_name: deepseek-local
    ports:
      - "8000:80"
    volumes:
      - deepseek_data:/data
    environment:
      - MODEL_ID=deepseek-ai/deepseek-coder-6.7b-instruct
      - PORT=80
      - HUGGING_FACE_HUB_TOKEN=${HUGGING_FACE_TOKEN}
    command: --model-id deepseek-ai/deepseek-coder-6.7b-instruct --port 80

volumes:
  deepseek_data:
EOF
        
        print_status "✅ Docker TGI setup complete!"
        print_status "Run: docker-compose -f docker-compose.deepseek.yml up -d"
        print_warning "You may need to set HUGGING_FACE_TOKEN for model access"
        ;;
        
    5)
        print_header "Skipping DeepSeek setup..."
        print_status "DeepSeek will be disabled. Only Granite will be used for AI tasks."
        
        # Update .env to disable DeepSeek
        if [ -f .env ]; then
            sed -i 's/DEEPSEEK_API_BASE=.*/DEEPSEEK_API_BASE=disabled/' .env
        fi
        ;;
        
    *)
        print_error "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

print_header "Updating configuration..."

# Update .env file
if [ -f .env ]; then
    # Update DeepSeek configuration
    sed -i 's|DEEPSEEK_API_BASE=.*|DEEPSEEK_API_BASE=http://localhost:8000/v1|' .env
    
    # Add DeepSeek model if not present
    if ! grep -q "DEEPSEEK_MODEL" .env; then
        echo "DEEPSEEK_MODEL=deepseek-coder" >> .env
    fi
    
    print_status "✅ Environment configuration updated"
else
    print_warning ".env file not found - creating one..."
    cat > .env << 'EOF'
# DeepSeek Configuration (Local)
DEEPSEEK_API_BASE=http://localhost:8000/v1
DEEPSEEK_MODEL=deepseek-coder

# Granite Configuration (Local)
GRANITE_API_BASE=http://localhost:11434/v1

# Database Configuration
PGHOST=localhost
PGPORT=5432
PGDATABASE=mcp_memory
PGUSER=postgres
PGPASSWORD=postgres

# Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
EOF
    print_status "✅ Environment configuration created"
fi

echo ""
print_header "Setup Complete! 🎉"
echo ""
print_status "Next steps:"
echo "1. Start your chosen DeepSeek service"
echo "2. Start the MCP server: python comprehensive_mcp_server.py"
echo "3. Test the connection: curl http://localhost:8080/health"
echo ""
print_status "DeepSeek will be available at: http://localhost:8000/v1"
print_status "MCP server will be available at: http://localhost:8080"
echo ""