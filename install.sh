#!/usr/bin/env bash

# Installer script for grommunio_exporter on Grommunio OpenSuSE 15.6 based appliances
# Script 2025111201

LOG_FILE=./install_grommunio_exporter.log
SCRIPT_GOOD=true

function log {
    local log_line="${1}"
    local level="${2}"

    if [ "${level}" != "" ]; then
        log_line="${level}: ${log_line}"
    fi
    echo "${log_line}" >> "${LOG_FILE}"
    echo "${log_line}"

    if [ "${level}" == "ERROR" ]; then
        SCRIPT_GOOD=false
    fi
}

function log_quit {
    log "${1}" "${2}"
    exit 1
}

log "#### Setup grommunio_exporter"

log "Installing Python 3.11 if not present"
zypper install -y python311 || log_quit "Cannot install python 3.11" "ERROR"

log "Setting up venv environment"
python3.11 -m venv /usr/local/grommunio_exporter_venv || log_quit "Cannot create python venv" "ERROR"
/usr/local/grommunio_exporter_venv/bin/python -m pip install --upgrade pip setuptools wheel || log_quit "Cannot update pip/setuptools/wheel in venv" "ERROR"
/usr/local/grommunio_exporter_venv/bin/python -m pip install grommunio_exporter || log_quit "Cannot install grommunio_exporter in venv" "ERROR"

log "Setup systemd unit file"

cat << 'EOF' > /etc/systemd/system/grommunio_exporter.service
[Unit]
Description=Grommunio Exporter
After=syslog.target
After=network.target
AssertFileIsExecutable=/usr/bin/grommunio_exporter

[Service]
Type=simple
# You may prefer to use a different user or group on your system.
#User=grommunio
#Group=grommunio
ExecStart=/usr/local/grommunio_exporter_venv/bin/grommunio_exporter -c /etc/grommunio_exporter.yaml
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF
[ $? -eq 0 ] || log "Failed to setup systemd unit file" "ERROR"

log "Setup /etc/grommunio_exporter.yaml config file"
cat << 'EOF' > /etc/grommunio_exporter.yaml
http_server:
  port: 9799
  listen: 0.0.0.0
  log_file: /var/log/grommunio_exporter.log
  # Optional api authentication
  no_auth: true
  username:
  password:
grommunio:
  # Optional overrides
  # mysql settings, see /etc/gromox/mysql_adaptor.cfg
  #  mysql_username: grommunio
  #  mysql_password: database_password
  #  mysql_database: grommunio
  #  mysql_host: localhost
  alternative_hostname:
EOF
[ $? -eq 0 ] || log "Failed to setup grommunio_exporter config file" "ERROR"

systemctl daemon-reload
log "Enabling grommunio_exporter service"
systemctl enable grommunio_exporter || log "Cannot enable grommunio_exporter service" "ERROR"
if systemctl is-active grommunio_exporter; then
    systemctl stop grommunio_exporter || log_quit "Cannot stop grommunio_exporter service" "ERROR"
fi
systemctl start grommunio_exporter || log_quit "Cannot start grommunio_exporter service"    

log "Opening firewall port"

if firewall-cmd --add-port=9799/tcp --permanent; then
    firewall-cmd --reload || log "Cannot reload firewall" "ERROR"
else
    log "Cannot configure firewall" "ERROR"
fi

if [ "${SCRIPT_GOOD}" == false ]; then
    echo "#### WARNING Installation FAILED ####"
    exit 1
else
    echo "#### grommunio_exporter has been setup successfully"
    echo "Test with curl localhost:9799/metrics"
    exit 0
fi
