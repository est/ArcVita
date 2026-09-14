#!/bin/bash
# 看门狗：pipeline 死了或心跳超 45 分钟没更新 → 杀掉重启
# 用法：nohup bash scripts/watch_pipeline.sh > tmp/watchdog.log 2>&1 &
cd "$(dirname "$0")/.."
HB="tmp/pipeline_heartbeat.json"
STALE_SECS=2700
RESTARTS=0
log() { echo "[$(date -u +%FT%TZ)] $*" >> tmp/watchdog.log; }

log "watchdog start"
while true; do
  ALIVE=0
  if pgrep -f "[s]creen_pipeline\.py" > /dev/null 2>&1; then
    ALIVE=1
  fi
  STALE=1
  if [ -f "$HB" ]; then
    MTIME=$(stat -c %Y "$HB" 2>/dev/null || stat -f %m "$HB" 2>/dev/null)
    NOW=$(date +%s)
    AGE=$((NOW - MTIME))
    if [ "$AGE" -lt "$STALE_SECS" ]; then
      STALE=0
    fi
    HB_AGE=$AGE
  else
    HB_AGE="none"
  fi

  if [ "$ALIVE" -eq 0 ]; then
    log "pipeline dead -> restart (restarts=$RESTARTS)"
    rm -f "$HB"
    nohup uv run python -u scripts/screen_pipeline.py >> tmp/screen_pipeline.log 2>&1 &
    RESTARTS=$((RESTARTS + 1))
  elif [ "$STALE" -eq 1 ]; then
    log "pipeline STALE (heartbeat age ${HB_AGE}s) -> kill + restart (restarts=$RESTARTS)"
    pkill -9 -f "[s]creen_pipeline\.py"
    sleep 3
    rm -f "$HB"
    nohup uv run python -u scripts/screen_pipeline.py >> tmp/screen_pipeline.log 2>&1 &
    RESTARTS=$((RESTARTS + 1))
  fi
  sleep 120
done
