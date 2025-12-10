#!/bin/bash
# Setup script for Insurance AI Agent

set -e

echo "=========================================="
echo "  Insurance AI Agent - Setup Script"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $python_version"

if [[ $(echo "$python_version < 3.10" | bc -l) -eq 1 ]]; then
    echo "Error: Python 3.10 or higher is required"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys!"
fi

# Create necessary directories
echo ""
echo "Creating data directories..."
mkdir -p data/policies
mkdir -p data/customers
mkdir -p data/chroma_db

# Initialize knowledge base
echo ""
echo "Initializing knowledge base..."
python -c "from src.knowledge.vector_store import initialize_vector_store; initialize_vector_store(reset=True)"

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your OpenAI and ElevenLabs API keys"
echo "  2. Run: streamlit run ui/app.py"
echo "  3. Or run: python main.py demo"
echo ""
echo "For more options: python main.py --help"
