#!/usr/bin/env bash
set -euo pipefail
set -x
export PATH="/usr/bin:/bin:/root/.local/bin:/root/.npm-global/bin:/root/bin:/root/.nix-profile/bin:/usr/local/bin:/snap/bin:/sbin:/usr/sbin"

# IMPORTANT: keep mobile visual monitoring off :99. Desktop Maestro/WebDriver uses :99.
export WAYDROID_X_DISPLAY="${WAYDROID_X_DISPLAY:-:98}"
export DISPLAY="$WAYDROID_X_DISPLAY"
export XDG_RUNTIME_DIR=/run/user/0
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus
export WAYLAND_DISPLAY=wayland-1
mkdir -p /run/user/0 /run/user/0/pulse /root/.openclaw/workspace/state
chmod 700 /run/user/0

/sbin/modprobe binder_linux devices=binder,hwbinder,vndbinder || true
mkdir -p /dev/binderfs
mountpoint -q /dev/binderfs || mount -t binder binder /dev/binderfs || true
ln -sf /dev/binderfs/binder /dev/binder || true
ln -sf /dev/binderfs/hwbinder /dev/hwbinder || true
ln -sf /dev/binderfs/vndbinder /dev/vndbinder || true

pgrep -x pipewire >/dev/null || nohup pipewire >/root/.openclaw/workspace/state/pipewire.log 2>&1 &
pgrep -x wireplumber >/dev/null || nohup wireplumber >/root/.openclaw/workspace/state/wireplumber.log 2>&1 &
pgrep -x pipewire-pulse >/dev/null || nohup pipewire-pulse >/root/.openclaw/workspace/state/pipewire-pulse.log 2>&1 &

# Start an isolated phone-sized X server for Waydroid visual output.
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  nohup Xvfb "$DISPLAY" -screen 0 430x920x24 -ac > /root/.openclaw/workspace/state/xvfb-waydroid-mobile.log 2>&1 &
  sleep 2
fi

# Stop stale Weston bound to this mobile display/socket, but don't touch desktop Xvfb :99.
python3 - <<'PY'
import os, signal, subprocess
me=os.getpid(); ppid=os.getppid()
try:
    lines=subprocess.check_output(['pgrep','-af','weston --backend=x11-backend.so|waydroid show-full-ui'], text=True, stderr=subprocess.DEVNULL).splitlines()
except subprocess.CalledProcessError:
    lines=[]
for line in lines:
    parts=line.split(maxsplit=1)
    if not parts: continue
    pid=int(parts[0]); cmd=parts[1] if len(parts)>1 else ''
    if pid in (me, ppid): continue
    if 'wayland-1' in cmd or 'show-full-ui' in cmd:
        try: os.kill(pid, signal.SIGTERM)
        except ProcessLookupError: pass
PY
sleep 1

# Phone-sized Waydroid display for mobile web monitoring.
waydroid prop set persist.waydroid.width 420 || true
waydroid prop set persist.waydroid.height 868 || true
waydroid prop set persist.waydroid.dpi 180 || true
sleep 2
systemctl restart waydroid-container
sleep 3
weston --backend=x11-backend.so --width=420 --height=900 --socket=wayland-1 --idle-time=0 > /root/.openclaw/workspace/state/weston-phone.log 2>&1 &
WESTON_PID=$!
sleep 6
waydroid session start > /root/.openclaw/workspace/state/waydroid-session-phone.log 2>&1 &
sleep 10
waydroid show-full-ui > /root/.openclaw/workspace/state/waydroid-show-phone.log 2>&1 &
(
  for i in $(seq 1 90); do
    if lxc-attach -P /var/lib/waydroid/lxc -n waydroid -- getprop sys.boot_completed 2>/dev/null | grep -q 1; then
      lxc-attach -P /var/lib/waydroid/lxc -n waydroid -- wm size 412x768 >/dev/null 2>&1 || true
      lxc-attach -P /var/lib/waydroid/lxc -n waydroid -- wm density 180 >/dev/null 2>&1 || true
      lxc-attach -P /var/lib/waydroid/lxc -n waydroid -- settings put system user_rotation 0 >/dev/null 2>&1 || true
      /root/.openclaw/workspace/state/start-tigervnc-bridge.sh >/root/.openclaw/workspace/state/start-tigervnc-bridge-from-waydroid.log 2>&1 || true
      break
    fi
    sleep 2
  done
) &
wait $WESTON_PID
