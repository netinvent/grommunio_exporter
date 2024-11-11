#!/usr/bin/env bash

# Installer script for grommunio_exporter on Grommunio OpenSuSE based appliances
# Script 2024111101

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

log "Installing python3-pip package"

zypper install -y python3-pip || log_quit "Cannot install python3-pip"
python3 -m pip install --upgrade pip setuptools wheel || log "Failed to update python pip/setuptools/wheel" "ERROR"
python3 -m pip install grommunio_exporter || log_quit "Failed to install grommunio_exporter"

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
ExecStart=/usr/bin/grommunio_exporter
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF
[ $? -eq 0 ] || log "Failed to setup systemd unit file" "ERROR"

systemctl enable grommunio_exporter || log "Cannot enable grommunio_exporter service" "ERROR"
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
    exit 0
fi
