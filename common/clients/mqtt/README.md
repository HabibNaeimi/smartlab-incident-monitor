# MQTT Client helper checkpoint

The helper uses Paho callback API version 2. Importing this module does not read
environment values, create a client, connect, or configure application logging.

Application callers must pass `clientID`, `host`, `port`, and keyword-only `site`
explicitly. Broker/session values come from Service Catalog global configuration;
topic helpers require explicit keyword arguments `root` and `site`. There are no
environment-derived defaults. `AppConfig` contains local bootstrap and secrets,
not discovered broker configuration.

The manual reconnection diagnostic supplies its own explicit local settings.
It is not an example of production service discovery.

Current behavior includes connection callbacks, subscription tracking,
resubscription after connection, JSON publication, and one raw-message handler.
The handler currently receives a Paho message; JSON decoding and handler error
isolation are not implemented yet.

F05 completes per-publication QoS, checked publication results, bounded startup
retry, malformed-message rejection, handler isolation, and real broker checks.
The current `qos` constructor default is provisional; it does not override the
topic-specific requirements in `docs/contracts/TOPICS.md`.


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
- Suppliy through Service Catalog.
