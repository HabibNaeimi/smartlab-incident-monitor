from common.clients.mqtt.mqtt_client import MQTTClient
import time

def handler(msg):
    print(msg.topic, msg.payload.decode())

def main():
    client = MQTTClient()
    client.set_message_handler(handler)
    client.connect()
    time.sleep(1)
    client.subscribe("test/sensors/#")
    print("Now restart the broker container")
    time.sleep(30)
    client.disconnect()


if __name__ == "__main__":
    main()
