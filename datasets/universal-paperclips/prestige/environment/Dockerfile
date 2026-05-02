FROM mcr.microsoft.com/playwright/python:v1.56.0-noble

ENV PYTHONUNBUFFERED=1 \
    PAPERCLIPS_GAME_DIR=/opt/paperclips-game \
    PAPERCLIPS_URL=http://127.0.0.1:8000/index2.html \
    REQUIRED_PRESTIGE_COUNT=1

RUN useradd --create-home --shell /bin/bash agent \
    && mkdir -p /app /logs/browser /logs/verifier /run/paperclips /opt/paperclips-game \
    && chown -R agent:agent /app /logs/browser \
    && chmod 755 /logs \
    && chmod 700 /logs/verifier /run/paperclips

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir playwright==1.56.0

COPY vendor/ /opt/paperclips-game/
COPY bin/game_server.py /usr/local/bin/game_server.py
COPY bin/browser_daemon.py /usr/local/bin/browser_daemon.py
COPY bin/browser /usr/local/bin/browser
COPY bin/paperclips_mcp /usr/local/bin/paperclips_mcp
COPY bin/paperclips_verify.py /usr/local/bin/paperclips_verify.py
COPY bin/start-paperclips /usr/local/bin/start-paperclips

RUN chmod 700 /opt/paperclips-game \
    && chmod 600 /opt/paperclips-game/* \
    && chmod 755 /usr/local/bin/browser /usr/local/bin/paperclips_mcp /usr/local/bin/start-paperclips \
    && chmod 744 /usr/local/bin/game_server.py /usr/local/bin/browser_daemon.py /usr/local/bin/paperclips_verify.py \
    && chown -R root:root /opt/paperclips-game /run/paperclips /logs/verifier

WORKDIR /app

ENTRYPOINT ["/usr/local/bin/start-paperclips"]
CMD ["sleep", "infinity"]
