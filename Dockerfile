# ============================================================
# Dockerfile — AnatoliaX Trading System v2.0
# Node.js + Python ortami
# ============================================================
FROM node:18-slim AS node_base

# Python kurulumu
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Node bagimliliklari
COPY package*.json ./
RUN npm install --production

# Python bagimliliklari
COPY PYTHON/requirements.txt ./PYTHON/
RUN python3 -m pip install --no-cache-dir -r PYTHON/requirements.txt

# Tum kaynak kodu
COPY . .

# Portlar
EXPOSE 3001 8080

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD node SCRIPTS/monitor/health_check.js --docker || exit 1

# Varsayilan komut
CMD ["node", "SCRIPTS/main.js"]
