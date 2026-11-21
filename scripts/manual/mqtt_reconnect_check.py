from common.clients.mqtt.mqtt_client import MQTTClient
import logging
import time

def handler(msg):
    print(msg.topic, msg.payload.decode())

def main():
    logging.basicConfig(level=logging.INFO)
    # Explicit local settings for this diagnostic, not an application fallback.
    client = MQTTClient(
        clientID="smartlab-manual-reconnect",
        host="localhost",
        port=18883,
        site="polito-smartlab",
    )
    client.set_message_handler(handler)
    client.connect()
    time.sleep(1)
    client.subscribe("test/sensors/#")
    print("Now restart the broker container")
    time.sleep(30)
    client.disconnect()


if __name__ == "__main__":
    main()
