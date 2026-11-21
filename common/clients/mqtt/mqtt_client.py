# Main MQTT Client helper for using in other microservices.

import json
import logging

import paho.mqtt.client as PahoMQTT

logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(
        self,
        clientID,
        host,
        port,
        *,
        site,
        cleanSession=True,
        qos=0,
        keepAlive=60,
        reconnectDelay=5,
    ):
        
        # Services supply settings. Obtained through Service Catalog discovery.
        self.host = host
        self.port = port
        self.clientID = clientID
        self.cleanSession = cleanSession
        self.qos = qos
        self.site = site
        self.keepAlive = keepAlive
        self._connected = False
        self._subscriptions = set()
        self._message_handler = None
        self.reconnectDelay = reconnectDelay

        # create an instance of paho.mqtt.client
        self.Client = PahoMQTT.Client(PahoMQTT.CallbackAPIVersion.VERSION2,
                                          client_id=clientID, 
                                          clean_session=self.cleanSession) 
        
		# callback registeration
        self.Client.on_connect = self.on_connect
        self.Client.on_message = self.on_message
        self.Client.on_disconnect = self.on_disconnect

        # connecting the logger
        self.Client.enable_logger(logger)

        # initializing the reconnection delay 
        self.Client.reconnect_delay_set(min_delay=self.reconnectDelay, max_delay=60)

    
    def on_connect(self, Client, userdata, flags, reason_code, properties):
        self._connected = (reason_code == 0)
        if reason_code==0:     
            logger.info(f"Connected to {self.host}:{self.port} with rc={reason_code}")
            if self._subscriptions:
                Client.subscribe(list(self._subscriptions))
                logger.info("Re-subscribed to %s", list(self._subscriptions))
        else:
            logger.warning("Connect failed with rc=%s", reason_code)
            
    def on_message(self, Client, userdata, msg):
        if self._message_handler is not None:
            self._message_handler(msg)
    
    def set_message_handler(self, handler):
        self._message_handler = handler

    def on_disconnect(self, Client, userdata, disconnect_flags, reason_code, properties):
        self._connected = False
        logger.info("Disconnected with rc=%s", reason_code)

    def subscribe(self, topic, qos=None):
        if qos is None:
            qos = self.qos

        self.Client.subscribe(topic, qos=qos)
        self._subscriptions.add((topic, qos))
        logger.info("Subscribed to topic=%s qos=%s", topic, qos)

    def subscribe_many(self, topics):
        # topics format: [("sensor/temp", 0), ("sensor/humidity", 1)]
        self.Client.subscribe(topics)

        for topic, qos in topics:
            self._subscriptions.add((topic, qos))

        logger.info("Subscribed to topics=%s", topics)

    def connect(self):
        try:
            self.Client.connect(self.host, self.port, keepalive=self.keepAlive)
            self.Client.loop_start()

        except Exception as e:
            logger.exception("Connection failed: %s", e)
            self.reconnect()
        
    def disconnect(self):
        for topic, _qos in self._subscriptions:
			# ensuring unsuscribe if it is working also as subscriber. 
            # unsubscribe only takes topics as strings
            self.Client.unsubscribe(topic)

        self._subscriptions.clear()
        logger.info(f"Unsubscribed from all topics")
        self.Client.disconnect()
        self.Client.loop_stop()
        logger.info(f"Disconnected successfully!")
    
    def publish_json(self, topic, payload, retain=False):
        body = json.dumps(payload)
        self.Client.publish(topic, body, qos=self.qos, retain=retain)
        logger.info("Published JSON to topic=%s", topic)

    def reconnect(self):
        try:
            self.Client.reconnect()
            logger.info("Trying to reconnect")
            
        except Exception:
            logger.exception("Reconnect failed")
