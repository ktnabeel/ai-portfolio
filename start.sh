#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

APP_NAME="ai-portfolio"
PID_FILE="$(pwd)/.${APP_NAME}.pid"
LOG_DIR="$(pwd)/logs"
OUT_LOG="${LOG_DIR}/${APP_NAME}.out.log"
ERR_LOG="${LOG_DIR}/${APP_NAME}.err.log"

COMMAND="${1:-start}"

# ── Config ──────────────────────────────────────────────────────────────────

# Require dependencies
command -v uv >/dev/null 2>&1 || { echo "ERROR: uv is required but not installed. See https://docs.astral.sh/uv/" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required but not installed." >&2; exit 1; }

HOST="$(uv run python scripts/config_value.py server.host 2>/dev/null || echo "127.0.0.1")"
PORT="$(uv run python scripts/config_value.py server.port 2>/dev/null || echo "7860")"
URL="http://${HOST}:${PORT}"

# ── Helpers ─────────────────────────────────────────────────────────────────

_help() {
    cat <<EOF
Usage:
  start.sh start     Start the portfolio service; restart it if already running
  start.sh stop      Stop the portfolio service
  start.sh restart   Restart the portfolio service
  start.sh status    Show service status
  start.sh help      Show this help message

Default command:
  start.sh

Local URL:
  ${URL}
EOF
    exit 0
}

_kill_existing() {
    echo "Checking for existing ${APP_NAME} processes..."

    # Kill by PID file if the process is alive
    if [ -f "${PID_FILE}" ]; then
        local pid
        pid="$(cat "${PID_FILE}" 2>/dev/null)"
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            echo "  Stopping existing ${APP_NAME} on PID ${pid}"
            kill "${pid}" 2>/dev/null || true
            sleep 2
            # Force-kill if still alive
            if kill -0 "${pid}" 2>/dev/null; then
                echo "  Force-killing PID ${pid}"
                kill -9 "${pid}" 2>/dev/null || true
                sleep 1
            fi
        fi
        rm -f "${PID_FILE}"
    fi

    # Kill any process listening on the target port
    local listeners
    listeners="$(ss -tlnp 2>/dev/null | grep ":${PORT} " | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' || true)"
    if [ -n "${listeners}" ]; then
        for pid in ${listeners}; do
            if kill -0 "${pid}" 2>/dev/null; then
                echo "  Freeing port ${PORT} from PID ${pid}"
                kill "${pid}" 2>/dev/null || true
                sleep 1
                if kill -0 "${pid}" 2>/dev/null; then
                    echo "  Force-killing PID ${pid}"
                    kill -9 "${pid}" 2>/dev/null || true
                    sleep 1
                fi
            fi
        done
        sleep 1
        # Verify port is actually free
        if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
            echo "  WARNING: Port ${PORT} is still in use after kill attempts."
        else
            echo "  Port ${PORT} is free."
        fi
    fi
}

_wait_for_listen() {
    local pid="$1"
    local deadline
    deadline="$(($(date +%s) + 120))"

    while [ "$(date +%s)" -lt "${deadline}" ]; do
        # Verify the app is actually serving HTTP (not just listening on port)
        if curl -s -o /dev/null -w '%{http_code}' --max-time 2 --connect-timeout 2 "${URL}" 2>/dev/null | grep -q '^[23]'; then
            return 0
        fi
        # Check if the process is still alive
        if ! kill -0 "${pid}" 2>/dev/null; then
            return 1
        fi
        sleep 1
    done
    return 1
}

# ── Commands ────────────────────────────────────────────────────────────────

case "${COMMAND}" in
    help|--help|-h)
        _help
        ;;

    start)
        _kill_existing

        mkdir -p "${LOG_DIR}"

        echo "Starting ${APP_NAME}..."
        nohup uv run python app.py >"${OUT_LOG}" 2>"${ERR_LOG}" &
        started_pid=$!
        echo "${started_pid}" >"${PID_FILE}"

        if _wait_for_listen "${started_pid}"; then
            echo "Started ${APP_NAME} on PID ${started_pid}"
            echo "URL: ${URL}"
            echo "Logs:"
            echo "  ${OUT_LOG}"
            echo "  ${ERR_LOG}"
        else
            echo "ERROR: Timed out waiting for ${APP_NAME} to listen on ${URL}" >&2
            exit 1
        fi
        ;;

    stop)
        _kill_existing
        echo "${APP_NAME} stopped."
        ;;

    restart)
        _kill_existing
        exec bash "${SCRIPT_DIR}/start.sh" start
        ;;

    status)
        pid=""
        if [ -f "${PID_FILE}" ]; then
            pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
        fi

        # Find the listener PID if the file doesn't match
        listener_pid=""
        listener_pid="$(ss -tlnp 2>/dev/null | grep ":${PORT} " | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -1 || true)"

        if [ -n "${listener_pid}" ]; then
            # Update PID file if it's stale
            if [ "${pid}" != "${listener_pid}" ]; then
                echo "${listener_pid}" >"${PID_FILE}"
                pid="${listener_pid}"
            fi
            echo "${APP_NAME} is running on PID ${pid}"
            echo "URL: ${URL}"
            exit 0
        fi

        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            echo "${APP_NAME} is starting on PID ${pid} but is not listening on port ${PORT} yet."
            exit 1
        fi

        rm -f "${PID_FILE}"
        echo "${APP_NAME} is not running."
        exit 1
        ;;

    *)
        echo "Unknown command: ${COMMAND}"
        echo "Run 'start.sh help' for usage."
        exit 1
        ;;
esac
