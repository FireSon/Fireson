import asyncio
import logging
import hashlib
import json
import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)


class Hyper2000(mqtt.Client):
    def __init__(self, h_id, h_prod, device: dict) -> None:
        """Initialise."""
        self.hid = h_id
        self.prodkey = h_prod 
        self.properties : dict[str, any] = {}
        super().__init__(client_id=f"HA-{self.hid}, clean_session=True)
        self.enable_logger()
        pwd = hashlib.md5(self.hid.encode()).hexdigest().upper()[8:24]
        
        self.username_pw_set(username=str(self.hid), password=str(pwd))
        self.on_message = self.onMessage
        self.on_connect = self.onConnect
        self.connect("mqtteu.zen-iot.com")
        self.on_disconnect = self.onDisconnect

        self.loop_start()


        # for key, value in device.items():
        #     self.properties[key] = value
        # self.connected: bool = False
        # self._loop = asyncio.get_running_loop()
        # self._client: mqtt.Client = None
        # self._lock = asyncio.Lock()

    async def async_connect(self):
        _LOGGER.log(f"Connecting {self.hid}")

        # def setup_connection():
        #     client = mqtt.Client(f"HA-{self.hid}")
        #     pwd = hashlib.md5(self.hid.encode()).hexdigest().upper()[8:24]
        #     client.username_pw_set(username=str(self.hid), password=str(pwd))

        #     state = client.connect("mqtteu.zen-iot.com")
        #     client.loop()
        #     client.loop_start()
        #     client.on_message = self.onMessage
        #     client.on_connect = self.onConnect
        #     client.on_disconnect = self.onDisconnect

        #     self.connected = client.is_connected()
        #     self._client = client

        #     topic = f"/{self.prodkey}/{self.hid}/properties/report"
        #     client.subscribe(topic)
        #     _LOGGER.log(f"subscribed {self.hid} {topic}")

        #     topic = f"/{self.prodkey}/{self.hid}/log"
        #     client.subscribe(topic)
        #     _LOGGER.log(f"subscribed {self.hid} {topic}")

        #     topic = f"iot/{self.prodkey}/{self.hid}/properties/write"
        #     client.subscribe(topic)
        #     _LOGGER.log(f"subscribed {self.hid} {topic}")

        #     _LOGGER.log(f"ready {self.hid}")
        #     return state

        #setup_connection()
        if not self.connected:
            raise ConnectionError(f"Could not connect to MQTT server.")

    def onMessage(self, _client, userdata, msg) -> dict:
        payload = json.loads(msg.payload.decode())
        self._payload = payload.copy()
        _LOGGER.log(f"Publishing: {self._payload}")

    def onConnect(self, _client, userdata, flags, rc):
        _LOGGER.log(f"Has been connected successfully")

    def onDisconnect(self, _client, userdata, rc):
        self.disconnect()

    def disconnect(self):
        _LOGGER.log(f"Disconnecting from {self._host}:{self._port} and clean subs")
        self._client.unsubscribe(self._topic)
        self._client.disconnect()
        self._client.loop_stop()
        self.connected = None

    def dumps_payload(payload):
        return str(payload).replace("'", '"').replace('"{', "{").replace('}"', "}")

    async def publish(self, instance, msg: dict, wait=False) -> bool:
        async with self._lock:
            if not self.is_connected:
                return _LOGGER.log(f"publish fails {msg}, broker isn't connected.")
            self._payload = None

            # Change selected index.
            async def publish_and_wait():
                self._client.publish(self._topic_push, self.dumps_payload(msg))
                while True:
                    await asyncio.sleep(0.2)
                    if self._payload is not None:
                        break

            # We will wait for any message for the next 3 seconds else we will return
            _LOGGER.log(f"Publishing: {self.dumps_payload(msg)}")
            task = self._loop.create_task(publish_and_wait())
            if wait:
                await asyncio.wait_for(task, 5)

    @property
    def is_connected(self) -> bool:
        return self._client and self._client.is_connected()
