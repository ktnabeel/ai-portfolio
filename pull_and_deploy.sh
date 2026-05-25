#!/bin/bash
# pull_and_deploy.sh - Run this on your VPS to pull from GitHub and restart the app

REPO_URL="https://github.com/ktnabeel/ai-portfolio.git"
TARGET_DIR="$HOME/ai-portfolio"

set -e

echo "--- Starting GitHub Pull & Deploy ---"

# 1. Handle Repository
if [ ! -d "$TARGET_DIR" ]; then
    echo "Cloning repository for the first time..."
    git clone $REPO_URL $TARGET_DIR
    cd $TARGET_DIR
else
    echo "Updating existing repository..."
    cd $TARGET_DIR
    git fetch origin
    # This ensures we match the remote exactly
    git reset --hard origin/$(git remote show origin | grep 'HEAD branch' | cut -d' ' -f5)
fi

# 2. Ensure Environment is ready
UV_BIN=""
if command -v uv &> /dev/null; then
    UV_BIN=$(command -v uv)
elif [ -f "$HOME/.cargo/bin/uv" ]; then
    UV_BIN="$HOME/.cargo/bin/uv"
elif [ -f "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
elif [ -f "/home/ubuntu/.cargo/bin/uv" ]; then
    UV_BIN="/home/ubuntu/.cargo/bin/uv"
elif [ -f "/root/.local/bin/uv" ]; then
    UV_BIN="/root/.local/bin/uv"
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    [ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"
    [ -f "$HOME/.local/bin/uv" ] && UV_BIN="$HOME/.local/bin/uv" || UV_BIN="$HOME/.cargo/bin/uv"
fi

# 3. Sync and Start
echo "Syncing dependencies using $UV_BIN..."
"$UV_BIN" sync

echo "Restarting application..."
pkill -f "python app.py" || true
mkdir -p logs
nohup "$UV_BIN" run python app.py > logs/app.log 2>&1 &

echo "------------------------------------------------"
echo "Success! App is running."
echo "Access at: http://$(curl -s ifconfig.me):7860"
echo "------------------------------------------------"
