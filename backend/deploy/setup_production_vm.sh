#!/usr/bin/env bash
# ==============================================================================
# GetMeHire — Automated Cloud VM Setup Script (Oracle Cloud Always Free / Ubuntu)
# Provisions PostgreSQL 17, Python 3.10+, Systemd Services, and Caddy Reverse Proxy
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " Starting GetMeHire Automated Production Host Setup"
echo "=========================================================="

# 1. Update OS Packages
sudo apt-get update -y
sudo apt-get install -y curl gnupg lsb-release build-essential python3 python3-venv python3-pip git debian-keyring debian-archive-keyring apt-transport-https

# 2. Install PostgreSQL 17
if ! command -v psql &> /dev/null; then
    echo "Installing PostgreSQL 17..."
    sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/trustedkeys.gpg.d/postgresql.gpg
    sudo apt-get update -y
    sudo apt-get install -y postgresql-17 postgresql-client-17
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
fi

# 3. Create Service User & Directories
echo "Configuring user and application directories..."
if ! id "globaljobs" &>/dev/null; then
    sudo useradd -r -s /bin/bash -d /opt/globaljobs -m globaljobs
fi

sudo mkdir -p /opt/globaljobs /var/log/globaljobs
sudo chown -R globaljobs:globaljobs /opt/globaljobs /var/log/globaljobs

# 4. Clone or Deploy Repository Code into /opt/globaljobs
echo "Setting up Python virtual environment..."
sudo -u globaljobs python3 -m venv /opt/globaljobs/backend/venv
sudo -u globaljobs /opt/globaljobs/backend/venv/bin/pip install --upgrade pip
sudo -u globaljobs /opt/globaljobs/backend/venv/bin/pip install -r /opt/globaljobs/backend/requirements.txt

# 5. Install Caddy Web Server
if ! command -v caddy &> /dev/null; then
    echo "Installing Caddy Reverse Proxy with Automated HTTPS..."
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt-get update -y
    sudo apt-get install -y caddy
fi

# 6. Install Systemd Service Units
echo "Installing Systemd service units..."
sudo cp /opt/globaljobs/backend/deploy/getmehire-api.service /etc/systemd/system/
sudo cp /opt/globaljobs/backend/deploy/getmehire-worker.service /etc/systemd/system/
sudo cp /opt/globaljobs/backend/deploy/Caddyfile /etc/caddy/Caddyfile

sudo systemctl daemon-reload
sudo systemctl enable getmehire-api getmehire-worker caddy

echo "=========================================================="
echo " Setup Completed Successfully!"
echo " Next Steps:"
echo " 1. Restore database: pg_restore -U postgres -d job_discovery /opt/globaljobs/backups/<backup>.dump"
echo " 2. Configure /opt/globaljobs/backend/.env"
echo " 3. Start services: sudo systemctl start getmehire-api getmehire-worker caddy"
echo "=========================================================="
