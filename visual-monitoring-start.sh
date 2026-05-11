#!/usr/bin/env bash
set -euo pipefail
mkdir -p /root/.openclaw/workspace/state/visual-monitor
for pid in $(pgrep -f '^ssh -L 6080:127\.0\.0\.1:6080 root@138\.199\.175\.88$' || true); do kill "$pid" || true; done
for pid in $(pgrep -f '^x11vnc .* -rfbport 5900' || true); do kill "$pid" || true; done
for pid in $(pgrep -f '^/usr/bin/python3 .*websockify.*127\.0\.0\.1:6080' || pgrep -f '^websockify .*127\.0\.0\.1:6080' || true); do kill "$pid" || true; done
tmux kill-session -t visual-monitor 2>/dev/null || true
sleep 1
if ! pgrep -f '^Xvfb :99 ' >/dev/null 2>&1; then
  Xvfb :99 -screen 0 1440x1000x24 -ac >/root/.openclaw/workspace/state/visual-monitor/xvfb.log 2>&1 &
fi
cat > /root/.openclaw/workspace/state/visual-monitor/start.sh <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:99
x11vnc -display :99 -localhost -nopw -forever -shared -rfbport 5900 -o /root/.openclaw/workspace/state/visual-monitor/x11vnc.log &
sleep 1
websockify --web=/usr/share/novnc --wrap-mode=ignore 127.0.0.1:6080 127.0.0.1:5900 > /root/.openclaw/workspace/state/visual-monitor/websockify.log 2>&1 &
sleep 1
if command -v chromium >/dev/null 2>&1 && ! pgrep -f 'visual-monitor-chromium' >/dev/null 2>&1; then
  chromium --no-sandbox --disable-dev-shm-usage --disable-gpu --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir=/tmp/visual-monitor-chromium https://puter.com >/root/.openclaw/workspace/state/visual-monitor/chromium.log 2>&1 &
elif command -v chromium-browser >/dev/null 2>&1 && ! pgrep -f 'visual-monitor-chromium' >/dev/null 2>&1; then
  chromium-browser --no-sandbox --disable-dev-shm-usage --disable-gpu --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir=/tmp/visual-monitor-chromium https://puter.com >/root/.openclaw/workspace/state/visual-monitor/chromium.log 2>&1 &
fi
tail -F /root/.openclaw/workspace/state/visual-monitor/x11vnc.log /root/.openclaw/workspace/state/visual-monitor/websockify.log
EOS
chmod +x /root/.openclaw/workspace/state/visual-monitor/start.sh
tmux new-session -d -s visual-monitor /root/.openclaw/workspace/state/visual-monitor/start.sh
sleep 3
curl -fsS -I --max-time 5 http://127.0.0.1:6080/vnc.html >/dev/null
ss -ltnp | grep -E ':(6080|5900)\b'
