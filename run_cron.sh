#!/bin/bash
# ---------------------------------------------------------------------------
# Chintu's Tech Adventures - Automated Cron Wrapper
# This script ensures the correct environment is loaded before pipeline execution.
# ---------------------------------------------------------------------------

# Exit immediately if a command exits with a non-zero status
set -e

# 1. Define Paths
PROJECT_DIR="/home/yashyv357/sketch-spark-engine"
VENV_PATH="$PROJECT_DIR/vm_server/venv"
LOG_FILE="$PROJECT_DIR/chintu_pipeline.log"

# 2. Navigate to project root
cd "$PROJECT_DIR" || { echo "Failed to cd to $PROJECT_DIR"; exit 1; }

# 3. Source environment variables (if separate from Python dotenv)
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# 4. Activate virtual environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Virtual environment not found at $VENV_PATH" | tee -a "$LOG_FILE"
    exit 1
fi

# 5. Log execution start
echo "=========================================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting automated pipeline run..." >> "$LOG_FILE"

# 6. Execute Orchestrator (Multi-Platform)
# We append stdout and stderr (2>&1) to the persistent log file
python -m orchestrator run --platform all >> "$LOG_FILE" 2>&1

# 7. Log execution completion
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pipeline run finished." >> "$LOG_FILE"
