#!/bin/bash
# remote_setup.sh - Script to be run on the VPS

set -e

echo "Updating system and installing dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv curl git

# Install uv if not present
if ! command -v uv &> /dev/null
then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "uv is already installed."
fi

# Ensure we are in the project directory
cd ~/ai-portfolio

# Create logs directory if it doesn't exist
mkdir -p logs

# Install dependencies using uv
echo "Installing project dependencies..."
/home/ubuntu/.cargo/bin/uv sync

# Kill any existing app.py processes
pkill -f "python app.py" || true

# Run the app in the background
echo "Starting the application..."
nohup /home/ubuntu/.cargo/bin/uv run python app.py > logs/app.log 2>&1 &

echo "------------------------------------------------"
echo "Deployment successful!"
echo "The app should be running at http://43.131.49.3:7860"
echo "Check ~/ai-portfolio/logs/app.log for details."
echo "------------------------------------------------"
