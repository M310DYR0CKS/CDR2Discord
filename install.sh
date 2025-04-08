#!/bin/bash

sudo apt update
sudo apt install -y python3 python3-pip ffmpeg mysql-client curl python3-venv

VENV_DIR="/opt/call_monitor/venv"
python3 -m venv "$VENV_DIR"

source "$VENV_DIR/bin/activate"
pip install -r requirements.txt
deactivate

SCRIPT_DIR="/opt/call_monitor"
mkdir -p "$SCRIPT_DIR"

cp your_script.py "$SCRIPT_DIR/monitor_calls.py"

chmod +x "$SCRIPT_DIR/monitor_calls.py"

SERVICE_FILE="/etc/systemd/system/call_monitor.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Call Monitor Service
After=network.target

[Service]
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/monitor_calls.py
WorkingDirectory=$SCRIPT_DIR
User=root
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable call_monitor.service
sudo systemctl start call_monitor.service

rm -rf "$VENV_DIR"
echo "Installation complete. The call monitor service is now running."
