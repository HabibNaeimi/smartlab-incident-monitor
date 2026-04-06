# MQTT Client helper

## Design structure
### Handeling Responsibilites
- broker connection
- connect/disconnect lifecycle
- publish
- subscribe
- callback registration 
- message dispatch  
- JSON serialization/deserialization        
- logging                                  
- reconnect behavior
- topic helper integration                  

### API
Call back API Version 2 is used as recommended in documentation. 

## Public Interface
Using this helper, a service should be able to create a client from config, connect to broker, subscribe to some topics, publish a JSON payload to a topic, attach its own message-handling behavior to those subscriptions, and handling restart and shut down cleanly. 

## Message representation
The MQTT helper should decode JSON dict.

## Subscribtion Behaviour
- Client can register multiple handlers
- The wildcards and topic filters are allowed where ever needed
- The handler exceptions must not kill the whole client
- We need to log bad messages clearly
- The messages dispatched in a simple callback model
- Since we may need to subscribe in different topics with different qos, topics should represent in this format:  list(toules(topic, qos)) -> [("sensor/temp", 0), ("sensor/humidity", 1)]

## Reconnection and Failure Policy
- If broker is down on startup or if connection drops later, it has to retry automatically
- Reconnect attempts will be logged
- Do not crash the whole service on temporary broker loss
- Reject malformed JSON clearly and log topic/payload context




## Config
- Imported through the rooted .env
