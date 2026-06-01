#!/bin/bash
# pull_and_deploy.sh - Run this on your VPS to pull from GitHub and restart the app

REPO_URL="https://github.com/ktnabeel/ai-portfolio.git"
TARGET_DIR="$HOME/ai-portfolio"

set -e

echo "--- Starting GitHub Pull & Deploy ---"

# 1. Handle Repository
if [ ! -d "$TARGET_DIR" ]; then
    echo "Cloning repository for the first time..."
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
else
    echo "Updating existing repository..."
    cd "$TARGET_DIR"
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
chmod +x ./start.sh
UV_BIN="$UV_BIN" ./start.sh restart

echo "------------------------------------------------"
echo "Success! App is running."
PORT="$("$UV_BIN" run python scripts/config_value.py server.port 2>/dev/null || echo "7860")"
PUBLIC_IP="$(curl -s --max-time 5 ifconfig.me || true)"
if [ -n "$PUBLIC_IP" ]; then
    echo "Access at: http://${PUBLIC_IP}:${PORT}"
else
    echo "Local health URL: http://127.0.0.1:${PORT}"
fi
echo "------------------------------------------------"
