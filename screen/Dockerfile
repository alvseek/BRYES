# BRYES — Phase 1: The Screen
# A disposable Ubuntu desktop the agent can screenshot and click inside.
# Xvfb is the (existing) virtual display server — we do NOT hand-roll one.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    SCREEN_RESOLUTION=1280x800x24

# Display stack + input tooling + screenshot + a visible test app + live viewer + python
RUN apt-get update && apt-get install -y --no-install-recommends \
      xvfb \
      x11-utils \
      fluxbox \
      x11-xserver-utils \
      feh \
      xdotool \
      scrot \
      x11-apps \
      xterm \
      gnome-calculator \
      dbus-x11 \
      x11vnc \
      novnc \
      websockify \
      python3 \
      python3-venv \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Real browser for web tasks: Google Chrome from the official .deb. (Ubuntu's apt
# 'chromium'/'chromium-browser' is a snap transitional that won't run in a container.)
# Runs headful on Xvfb; launch with --no-sandbox since we are root.
RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg ca-certificates \
    && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm -f /tmp/chrome.deb && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 marks the system Python as externally-managed (PEP 668),
# so install app deps into an isolated venv.
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY server /app/server
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app
# 8000 = control API (screenshot + action) · 6080 = noVNC live desktop view
EXPOSE 8000 6080

CMD ["/app/entrypoint.sh"]
