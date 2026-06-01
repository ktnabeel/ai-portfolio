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
UV_BIN="$(command -v uv || true)"
if [ -z "$UV_BIN" ] && [ -x "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
fi
if [ -z "$UV_BIN" ] && [ -x "$HOME/.cargo/bin/uv" ]; then
    UV_BIN="$HOME/.cargo/bin/uv"
fi
if [ -z "$UV_BIN" ]; then
    echo "ERROR: uv installation was not found after install step." >&2
    exit 1
fi
"$UV_BIN" sync

# Run the app through the shared service wrapper so stale listeners are handled consistently.
echo "Starting the application..."
chmod +x ./start.sh
UV_BIN="$UV_BIN" ./start.sh restart

echo "------------------------------------------------"
echo "Deployment successful!"
echo "The app should be running at http://43.131.49.3:7860"
echo "Check ~/ai-portfolio/logs/ai-portfolio.err.log for details."
echo "------------------------------------------------"
