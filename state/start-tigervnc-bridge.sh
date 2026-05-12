#!/usr/bin/env bash
set -euo pipefail
mkdir -p /root/.openclaw/workspace/state

# Mobile visual monitor is isolated from desktop Maestro on :99.
export DISPLAY="${WAYDROID_X_DISPLAY:-${DISPLAY:-:98}}"

# Stop old VNC proxies/servers for the mobile monitor only. Avoid pkill -f matching this script's own command line.
python3 - <<'PY'
import os, signal, subprocess
me=os.getpid(); ppid=os.getppid()
try:
    lines=subprocess.check_output(['pgrep','-af','X0tigervnc|x0vncserver|websockify'], text=True, stderr=subprocess.DEVNULL).splitlines()
except subprocess.CalledProcessError:
    lines=[]
for line in lines:
    parts=line.split(maxsplit=1)
    if not parts: continue
    pid=int(parts[0]); cmd=parts[1] if len(parts)>1 else ''
    if pid in (me, ppid):
        continue
    if ('-rfbport 5901' in cmd or '127.0.0.1:6080' in cmd or '127.0.0.1:5901' in cmd):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
PY
sleep 1

# Ensure the isolated X display exists. Desktop cron uses :99; mobile uses :98.
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  X_NUM="${DISPLAY#:}"
  X_NUM="${X_NUM%%.*}"
  nohup Xvfb "$DISPLAY" -screen 0 430x920x24 -ac > /root/.openclaw/workspace/state/xvfb-waydroid-mobile.log 2>&1 &
  sleep 2
fi

# The noVNC view must follow the Waydroid/Weston phone window, not Selenium desktop Chromium.
WESTON_ID=""
if command -v xdotool >/dev/null 2>&1; then
  WESTON_ID=$(xdotool search --name 'Weston Compositor' 2>/dev/null | head -n1 || true)
fi
if [[ -z "$WESTON_ID" ]] && command -v xwininfo >/dev/null 2>&1; then
  WESTON_ID=$(xwininfo -root -tree 2>/dev/null | awk '/"Weston Compositor/ {print $1; exit}' || true)
fi
if [[ -n "$WESTON_ID" ]] && command -v xdotool >/dev/null 2>&1; then
  xdotool windowmove "$WESTON_ID" 0 0 2>/dev/null || true
  xdotool windowraise "$WESTON_ID" 2>/dev/null || true
fi

GEOM="420x900+0+0"
if [[ -n "$WESTON_ID" ]] && command -v xwininfo >/dev/null 2>&1; then
  INFO=$(xwininfo -id "$WESTON_ID" 2>/dev/null || true)
  W=$(awk -F: '/Width:/ {gsub(/ /,"",$2); print $2}' <<<"$INFO" | head -n1)
  H=$(awk -F: '/Height:/ {gsub(/ /,"",$2); print $2}' <<<"$INFO" | head -n1)
  X=$(awk -F: '/Absolute upper-left X:/ {gsub(/ /,"",$2); print $2}' <<<"$INFO" | head -n1)
  Y=$(awk -F: '/Absolute upper-left Y:/ {gsub(/ /,"",$2); print $2}' <<<"$INFO" | head -n1)
  if [[ -n "${W:-}" && -n "${H:-}" && -n "${X:-}" && -n "${Y:-}" ]]; then
    GEOM="${W}x${H}+${X}+${Y}"
  fi
fi

echo "Using mobile noVNC display: $DISPLAY crop: $GEOM" | tee /root/.openclaw/workspace/state/tigervnc-geometry.log
nohup x0vncserver -display "$DISPLAY" -rfbport 5901 -localhost yes -SecurityTypes None -Geometry "$GEOM" -fg > /root/.openclaw/workspace/state/tigervnc-x0.log 2>&1 &
sleep 1
nohup websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5901 > /root/.openclaw/workspace/state/novnc-tigervnc.log 2>&1 &
sleep 1
ss -ltnp | grep -E ':(5901|6080)\b' || true
