# Grommunio exporter for Prometheus
[![License](https://img.shields.io/badge/license-GPLv3-blu.svg)](https://opensource.org/licenses/GPL-3.0)
[![Percentage of issues still open](http://isitmaintained.com/badge/open/netinvent/grommunio_exporter.svg)](http://isitmaintained.com/project/netinvent/grommunio_exporter "Percentage of issues still open")
[![GitHub Release](https://img.shields.io/github/release/netinvent/grommunio_exporter.svg?label=Latest)](https://github.com/netinvent/grommunio_exporter/releases/latest)
[![Linux linter](https://github.com/netinvent/grommunio_exporter/actions/workflows/pylint-linux.yaml/badge.svg)](https://github.com/netinvent/grommunio_exporter/actions/workflows/pylint-linux.yaml)


This program exposes Grommunio email system metrics for Prometheus  
Since we already have node_exporter for system metrics and postfix_exporter for email deliverability metrics, this closes the gap with mailbox metrics.


### Grafana Dashboard

You can find an [example dashboard](examples/grafana_dashboard_v0.2.1.json) in the examples directory

![image](examples/grafana_dashboard_v0.1.0.png)
![image](examples/grafana_dashboard_v0.1.0b.png)

### Automatic installation

On current Grommunio appliances based on OpenSuSE, you can use the following all-in-one installer script
```
curl -sSfL https://raw.githubusercontent.com/netinvent/grommunio_exporter/refs/heads/main/install.sh | sh -
```

### Manual Install

Easiest way to install grommunio_exporter is to use python pip:
```
python3 -m pip install grommunio_exporter
```

#### Special notes for Grommunio appliances
Note that on Grommunio appliances based on OpenSuSE 15.5, you'll have to install pip first and update wheel package via the following commands.
Also note that installing the requested requirements for grommunio_exporter will fail if `pip` and `wheel` package isn't up to date in the Grommunio appliance (zypper installs pip 10.0.1, and pip 21.3.1 is required). 
Lastly, the message `pygobject 3.42.2 requires pycairo>=1.16.0, which is not installed.` can be ignored on these systems.  
```
zypper install -y python3-pip
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install grommunio_exporter
```

Installing via pip will create `/usr/bin/grommunio_exporter`. This file can be run manually for testing purposes, or run as service.

The exporter needs to be installed on the host that has grommunio-admin cli interface.  
Once installed, you can create a systemd service file from the [systemd unit file](examples/grommunio_exporter.service) in the example dir.  
Once the service is running, you may query the exporter with:
```
curl http://localhost:9769/metrics
```

### Firewall

The default exporter-port is 9799/tcp, which you can change in the config file.
Keep in mind that you need to create a firewall rule if you want to query it's output.

You can create the firewall rule with the following command on a Grommunio appliance
```
firewall-cmd --add-port=9799/tcp --permanent && firewall-cmd --reload
```

### Metrics

The exporter currently produces the following metrics:  

- `grommunio_api_status` is 0 when no errors where found in api calls
- `grommunio_mailbox_count`
- `grommunio_shared_mailbox_count`

The follwoing metrics are per user and have labels `hostname,domain,username`:

- `grommunio_mailbox_messagesize`
- `grommunio_mailbox_storage_quota_limit`
- `grommunio_mailbox_prohibit_receive_limit`
- `grommunio_mailbox_prohibit_send_quota`
- `grommunio_mailbox_creation_time`


### Alert rules:

```
    - alert: Storage Quota
      expr: (1-((grommunio_mailbox_storage_quota_limit - grommunio_mailbox_messagesize)/grommunio_mailbox_storage_quota_limit))*100 > 95
      for: 5m

    - alert: Prohibit Send Quota
      expr: (1-((grommunio_mailbox_prohibit_send_quota - grommunio_mailbox_messagesize)/grommunio_mailbox_prohibit_send_quota))*100 > 95
      for: 5m

    - alert: Prohibit Receive Quota
      expr:  (1-((grommunio_mailbox_prohibit_receive_limit - grommunio_mailbox_messagesize)/grommunio_mailbox_prohibit_receive_limit))*100 > 95
      for: 5m
```

### Customization

You may create a `grommunio_exporter.yaml` that can be added to the exporter via `--config-file=/etc/grommunio_exporter.yaml` argument.  
This file can override the following:
- http listen ip
- http listen port
- http authentication
- grommunio api concurrency
- grommunio hostname
- path to grommunio-admin

### Troubeshooting

This program has currently been tested on grommunio-admin-api-1.16.8.

By default, the exporter will log to `/var/log/grommunio_exporter.log`  
You can override this in the config file.

You may also run the exporter with `--debug` in order to gain more information.

In order to be quick, `grommunio_exporter` uses concurrency to the grommunio_api.
By default, this concurrency is set to 4. You can increase the concurrency if querying is to slow.
Nevertheless, you should never query more than every 5 minutes to keep the server load down.

You can set the following scrape settings in the prometheus job:
```
scrape_interval: 300s
scrape_timeout: 240s
```

### Misc

This version of the grommunio exporter uses the locally installed grommunio-admin cli interface instead of the REST API.  
Pros:
- No need for authentication

Cons:
- Not all commands output parseable json
- Probably slower than REST UI

If the project gains some traction, we can add REST UI support.

### License

Licensed under GPLv3.0... Contributions are welcome  
(C) 2024 NetInvent SASU  
