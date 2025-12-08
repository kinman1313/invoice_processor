#!/bin/bash
# Quick setup script for Invoice Processing Agent

echo "🚀 Invoice Processing Agent - Setup Script"
echo "=========================================="
echo ""

# Check Python
echo "✓ Checking Python..."
python_version=$(python --version 2>&1)
if [ $? -eq 0 ]; then
    echo "  Found: $python_version"
else
    echo "  ❌ Python not found. Please install Python 3.8+"
    exit 1
fi

# Create virtual environment
echo ""
echo "✓ Creating virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "  Created: venv/"
else
    echo "  Already exists: venv/"
fi

# Activate virtual environment
echo ""
echo "✓ Activating virtual environment..."
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null
echo "  Activated"

# Install dependencies
echo ""
echo "✓ Installing dependencies..."
pip install -q -r requirements.txt
if [ $? -eq 0 ]; then
    echo "  Installed from requirements.txt"
else
    echo "  ⚠️  Some packages may have failed. Check requirements.txt"
fi

# Setup .env file
echo ""
echo "✓ Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created: .env (edit this file with your API key)"
else
    echo "  Already exists: .env"
fi

# Generate sample invoices
echo ""
echo "✓ Generating sample invoices..."
if python generate_samples.py > /dev/null 2>&1; then
    echo "  Created 5 sample invoices in sample_invoices/"
else
    echo "  ⚠️  Could not generate samples. Check ReportLab installation."
fi

# Summary
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env and add your Anthropic API key:"
echo "   ANTHROPIC_API_KEY=sk-ant-..."
echo ""
echo "2. Start the web interface:"
echo "   streamlit run app.py"
echo ""
echo "   Or test from command line:"
echo "   python invoice_agent.py sample_invoices/invoice_clean.pdf"
echo ""
echo "=========================================="
