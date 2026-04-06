# Topic handler
"""
Topic handler for using in app in order to inject a little flexibility instead of hardcoding mqtt topics.
Required QoS has been commented for each topic.
"""
import os

ROOT = os.getenv("MQTT_TOPIC_ROOT", "smartlab")
SITE = os.getenv("MQTT_SITE", "polito") 

# Operational topics
def alerts(site=SITE, root=ROOT):
    # QoS = 1
    return f"{root}/{site}/alerts"

def recommendations(site=SITE, root=ROOT):
    # QoS = 1
    return f"{root}/{site}/recommendations"

def notifications(site=SITE, root=ROOT):
    # QoS = 1
    return f"{root}/{site}/notifications"

def device_cmd(device_id, root=ROOT, site=SITE):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/cmd"

def device_ack(device_id, root=ROOT, site=SITE):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/ack"

# Raw data topics
def raw_telemetry(device_id, root=ROOT, site=SITE):
    # QoS = 0
    return f"{root}/{site}/devices/{device_id}/telemetry"

def raw_heartbeat(device_id, root=ROOT, site=SITE):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/heartbeat"

def raw_status(device_id, root=ROOT, site=SITE):
    # QoS = 1
    return f"{root}/{site}/devices/{device_id}/status"

# Normalized data topics
def normalized_status(device_id, root=ROOT, site=SITE):
    # QoS = 1
    return f"{root}/{site}/normalized/{device_id}/status"

def normalized_telemetry(device_id, root=ROOT, site=SITE):
    # QoS = 0
    return f"{root}/{site}/normalized/{device_id}/telemetry"

def normalized_heartbeat(device_id, root=ROOT, site=SITE):
    # QoS = 1
    return f"{root}/{site}/normalized/{device_id}/heartbeat"

# Wildcards topics
def all_raw_telemetry(site=SITE, root=ROOT):
    # QoS = 0
    return f"{root}/{site}/devices/+/telemetry"

def all_raw_heartbeat(site=SITE, root=ROOT):
    # QoS = 1
    return f"{root}/{site}/devices/+/heartbeat"

def all_raw_status(site=SITE, root=ROOT):
    # QoS = 1
    return f"{root}/{site}/devices/+/status"

def all_normalized_telemetry(site=SITE, root=ROOT):
    # QoS = 0
    return f"{root}/{site}/normalized/+/telemetry"

def all_normalized_heartbeat(site=SITE, root=ROOT):
    # QoS = 1
    return f"{root}/{site}/normalized/+/heartbeat"

def all_normalized_status(site=SITE, root=ROOT):
    # QoS = 1
    return f"{root}/{site}/normalized/+/status"