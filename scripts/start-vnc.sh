#!/bin/bash
# start-vnc.sh - Start VNC server for noVNC

# Kill existing
pkill -f 'websockify.*6080' 2>/dev/null
pkill -f 'x11vnc' 2>/dev/null
pkill -f 'Xvfb.*:97' 2>/dev/null
sleep 2

# Start Xvfb
Xvfb :97 -screen 0 1440x1000x24 -ac +extension RANDR > /tmp/xvfb.log 2>&1 &
sleep 2

# Start x11vnc
x11vnc -display :97 -rfbport 5902 -shared -forever -nopw -noxdamage > /tmp/x11vnc.log 2>&1 &
sleep 2

# Start websockify
websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5902 > /tmp/websockify.log 2>&1 &
sleep 2

echo "VNC server started on http://127.0.0.1:6080/vnc.html"
echo "Display: :97, VNC port: 5902, WebSocket: 6080"
ps aux | grep -E 'Xvfb :97|x11vnc|websockify' | grep -v grep
