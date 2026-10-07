#!/bin/bash
# deploy.sh: Turnkey deployment script for DigitalOcean Droplets (Ubuntu/Debian)

set -e

echo "=========================================================="
echo " Deploying Solana Alpha Tracker to DigitalOcean Droplet"
echo "=========================================================="

APP_DIR="/opt/solana-holder-scanner"

# Check if Docker and Docker Compose plugin/cli are installed
if command -v docker &> /dev/null && (docker compose version &> /dev/null || command -v docker-compose &> /dev/null); then
    echo "[Deploy] Using Docker Compose..."
    mkdir -p "$APP_DIR/data"
    cd "$APP_DIR"
    if docker compose version &> /dev/null; then
        docker compose down || true
        docker compose up -d --build
    else
        docker-compose down || true
        docker-compose up -d --build
    fi
    echo "=========================================================="
    echo " SUCCESS: Docker container is running 24/7!"
    echo " Check status with: docker compose ps"
    echo " View logs with:    docker compose logs -f"
    echo "=========================================================="
else
    echo "[Deploy] Docker not detected. Setting up Native Systemd service..."
    
    # Install Python 3, venv, and SQLite if needed
    apt-get update
    apt-get install -y python3 python3-pip python3-venv curl

    cd "$APP_DIR"
    
    # Create Python virtual environment if not present
    if [ ! -d "venv" ]; then
        echo "[Deploy] Creating Python virtualenv..."
        python3 -m venv venv
    fi

    # Install Python dependencies
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt

    # Install systemd service
    echo "[Deploy] Installing solana-tracker.service..."
    cp solana-tracker.service /etc/systemd/system/solana-tracker.service
    systemctl daemon-reload
    systemctl enable solana-tracker
    systemctl restart solana-tracker

    echo "=========================================================="
    echo " SUCCESS: Systemd service is running 24/7!"
    echo " Check status with: systemctl status solana-tracker"
    echo " View logs with:    journalctl -u solana-tracker -f"
    echo "=========================================================="
fi

echo "Access the dashboard at: http://$(curl -s ifconfig.me)"
