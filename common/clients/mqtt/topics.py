# Topic handler
"""
Topic handler for using in app in order to inject a little flexibility instead of hardcoding mqtt topics.
Required QoS has been commented for each topic.
"""
# The root and site: returned by Service Catalog.

# Operational topics
def alerts(*, site, root):
    # QoS = 1
    return f"{root}/{site}/alerts"

def recommendations(*, site, root):
    # QoS = 1
    return f"{root}/{site}/recommendations"

def notifications(*, site, root):
    # QoS = 1
    return f"{root}/{site}/notifications"

def device_cmd(device_id, *, root, site):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/cmd"

def device_ack(device_id, *, root, site):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/ack"


# Raw data topics
def raw_telemetry(device_id, *, root, site):
    # QoS = 0
    return f"{root}/{site}/devices/{device_id}/telemetry"

def raw_heartbeat(device_id, *, root, site):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/heartbeat"

def raw_status(device_id, *, root, site):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/status"


# Normalized data topics
def normalized_status(device_id, *, root, site):
    # QoS = 1
    return f"{root}/{site}/normalized/{device_id}/status"

def normalized_telemetry(device_id, *, root, site):
    # QoS = 0
    return f"{root}/{site}/normalized/{device_id}/telemetry"

def normalized_heartbeat(device_id, *, root, site):
    # QoS = 1
    return f"{root}/{site}/normalized/{device_id}/heartbeat"


# Wildcards topics
def all_raw_telemetry(*, site, root):
    # QoS = 0
    return f"{root}/{site}/devices/+/telemetry"

def all_raw_heartbeat(*, site, root):
    # QoS = 1
    return f"{root}/{site}/devices/+/heartbeat"

def all_raw_status(*, site, root):
    # QoS = 1
    return f"{root}/{site}/devices/+/status"

def all_normalized_telemetry(*, site, root):
    # QoS = 0
    return f"{root}/{site}/normalized/+/telemetry"

def all_normalized_heartbeat(*, site, root):
    # QoS = 1
    return f"{root}/{site}/normalized/+/heartbeat"

def all_normalized_status(*, site, root):
    # QoS = 1
    return f"{root}/{site}/normalized/+/status"
