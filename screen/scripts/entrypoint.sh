#!/usr/bin/env bash
# Boot the virtual desktop, then hand off to the control API (PID 1).
set -e

: "${DISPLAY:=:99}"
: "${SCREEN_RESOLUTION:=1280x800x24}"
export DISPLAY

echo "[entrypoint] Xvfb on $DISPLAY ($SCREEN_RESOLUTION)"
Xvfb "$DISPLAY" -screen 0 "$SCREEN_RESOLUTION" -ac +extension GLX +render -noreset &

# Wait for the display to accept connections before starting anything on it.
for _ in $(seq 1 40); do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then break; fi
  sleep 0.25
done

echo "[entrypoint] solid background (avoids fbsetbg wallpaper warning)"
xsetroot -solid "#2e3440"
# Pre-seed fluxbox so it uses xsetroot for the root background instead of fbsetbg.
mkdir -p /root/.fluxbox
printf 'session.screen0.rootCommand: xsetroot -solid #2e3440\n' > /root/.fluxbox/init

echo "[entrypoint] window manager (fluxbox)"
fluxbox >/tmp/fluxbox.log 2>&1 &

echo "[entrypoint] dbus session bus (gnome-calculator needs it)"
eval "$(dbus-launch --sh-syntax)"
export DBUS_SESSION_BUS_ADDRESS DBUS_SESSION_BUS_PID

echo "[entrypoint] test apps: gnome-calculator + xterm"
gnome-calculator >/tmp/calc.log 2>&1 &
# cursorBlink off so a static desktop stays byte-stable between screenshots
xterm -geometry 80x24+760+60 -xrm 'XTerm*cursorBlink:false' >/tmp/xterm.log 2>&1 &

echo "[entrypoint] live view: x11vnc + noVNC on :6080"
x11vnc -display "$DISPLAY" -forever -shared -nopw -rfbport 5900 -quiet -bg >/tmp/x11vnc.log 2>&1 || true
websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 &

echo "[entrypoint] control API on :8000"
exec python /app/server/app.py
