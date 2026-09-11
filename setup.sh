#!/usr/bin/env bash

# ==============================================================================
# Radhe Multi-Userbot AutoChat Bot - One-Click VPS Setup Script (Ubuntu/Debian)
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 Starting Radhe Multi-Userbot VPS Installation..."
echo "=========================================================="

# 1. Update system packages
echo "📦 Updating apt packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. Install Python, Pip, Git, Build tools for tgcrypto
echo "📦 Installing required dependencies (Python, Git, GCC, libffi, libssl)..."
sudo apt-get install -y python3 python3-pip python3-venv git build-essential gcc libffi-dev libssl-dev tmux

# 3. Create virtual environment if not present
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment (venv)..."
    python3 -m venv venv
fi

# 4. Activate virtual environment and install requirements
echo "📦 Installing Python packages from requirements.txt..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Check for .env file
if [ ! -f ".env" ]; then
    if [ -f "sample.env" ]; then
        echo "⚠️ .env file not found. Copying sample.env to .env..."
        cp sample.env .env
        echo "📝 Please edit the .env file with your credentials: nano .env"
    fi
fi

echo "=========================================================="
echo "✅ Setup Completed Successfully!"
echo "=========================================================="
echo ""
echo "To run the bot now:"
echo "  source venv/bin/activate"
echo "  python3 -m Radhe"
echo ""
echo "To run 24/7 in a background screen/tmux:"
echo "  tmux new -s radhe"
echo "  source venv/bin/activate && python3 -m Radhe"
echo "  (Press Ctrl+B then D to detach)"
echo ""
echo "Or configure the systemd service using radhebot.service!"
echo "=========================================================="
