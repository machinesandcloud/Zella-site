# IBKR Gateway (IBController) Droplet Setup

Use this guide to run IBKR Gateway headlessly on the DigitalOcean droplet and expose the TWS API on port 4002 (paper) or 4001 (live).

## 0) Pre-flight

- Droplet OS: Ubuntu 22.04 LTS
- IB Gateway installed at `/home/ibkr/IBGateway`
- IBController extracted to `/home/ibkr/IBController`
- User: `ibkr`

## 1) Fix permissions and line endings

```bash
sudo systemctl stop ibgateway || true
sudo systemctl disable ibgateway || true

# If /home is mounted with noexec, move IBController to /opt
mount | grep " /home "

sudo mv /home/ibkr/IBController /opt/IBController
sudo chown -R ibkr:ibkr /opt/IBController
sudo chmod +x /opt/IBController/IBControllerStart.sh
sudo sed -i 's/\r$//' /opt/IBController/IBControllerStart.sh
```

If `/home` is not `noexec`, you may keep IBController in `/home/ibkr/IBController` and adjust paths below accordingly.

## 2) Install GUI dependencies + headless X

IB Gateway uses JavaFX/GTK. The error `Unable to load glass GTK library` indicates missing libs or no display.

```bash
sudo apt-get update
sudo apt-get install -y \
  xvfb \
  libgtk-3-0 \
  libxext6 \
  libxrender1 \
  libxtst6 \
  libxi6 \
  libxrandr2 \
  libasound2
```

## 3) IBController config

Create `/opt/IBController/ibcontroller.ini` (adjust credentials):

```bash
sudo tee /opt/IBController/ibcontroller.ini >/dev/null <<'EOF'
IbLoginId=YOUR_IBKR_USERNAME
IbPassword=YOUR_IBKR_PASSWORD
TradingMode=paper
ReadOnlyApi=false
ForceTwsApiPort=4002
AcceptNonBrokerageAccountWarning=yes
EOF
sudo chown ibkr:ibkr /opt/IBController/ibcontroller.ini
```

If you need live trading, set `TradingMode=live` and `ForceTwsApiPort=4001`.

## 4) Systemd service (headless)

```bash
sudo tee /etc/systemd/system/ibgateway.service >/dev/null <<'EOF'
[Unit]
Description=IBKR Gateway (IBController)
After=network.target

[Service]
Type=simple
User=ibkr
WorkingDirectory=/home/ibkr
Environment=DISPLAY=:99
ExecStart=/usr/bin/xvfb-run -a /opt/IBController/IBControllerStart.sh /home/ibkr/IBGateway
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ibgateway
sudo systemctl start ibgateway
```

## 5) Verify

```bash
sleep 10
ss -ltnp | grep 4002 || echo "NOT LISTENING"
journalctl -u ibgateway --no-pager -n 200
```

If `4002` is not listening, check:
- IBKR login/2FA prompts (first run may require manual login)
- Firewall rules (UFW)
- Incorrect TradingMode or port
- IBControllerStart.sh path/permissions

## 6) Render backend envs (must match droplet)

```
IBKR_HOST=143.198.229.169
IBKR_PAPER_PORT=4002
IBKR_LIVE_PORT=4001
USE_MOCK_IBKR=false
USE_FREE_DATA=false
USE_IBKR_WEBAPI=false
DEFAULT_TRADING_MODE=PAPER
```

Restart the Render service after updating envs.

