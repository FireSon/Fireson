import asyncio
import logging
import hashlib
import json
from paho.mqtt import client as mqtt_client

_LOGGER = logging.getLogger(__name__)


class Hyper2000():
    def __init__(self, h_id, h_prod, device: dict) -> None:
        """Initialise."""
        self.hid = h_id
        self.prodkey = h_prod 
        self.properties : dict[str, any] = {}
        # for key, value in device.items():
        #     self.properties[key] = value
        self._client: mqtt_client = None
        self._loop = asyncio.get_running_loop()
        self._lock = asyncio.Lock()
        self.connected : bool = False
        self._topic_refresh = f"iot/{self.prodkey}/{self.hid}/properties/read"

    def connect(self):
        try:
            _LOGGER.info(f'Connect Hyper2000: {self.hid} {self.prodkey}')
            client = mqtt_client.Client(client_id=str(self.hid), clean_session=False)

            pwd = hashlib.md5(self.hid.encode()).hexdigest().upper()[8:24]
            client.username_pw_set(username=str(self.hid), password=str(pwd))
            client.on_message = self.onMessage
            client.on_connect = self.onConnect
            client.on_disconnect = self.onDisconnect

            state = client.connect("mqtteu.zen-iot.com", 1883, 120)
            _LOGGER.info(f'Connect Hyper2000: {self.hid} {self.prodkey}')

            self._client = client
            self._client.subscribe(f'/{self.prodkey}/{self.hid}/#')
            self._client.subscribe(f"iot/{self.prodkey}/{self.hid}/#")

            # client.loop()
            self._client.loop_start()

            _LOGGER.info(f"ready {self.hid} {self.connected} {state}")

        except Exception as err:
            _LOGGER.error("Error while connecting : %s", self.hid)
            _LOGGER.error(err)

        if not self.connected:
            raise ConnectionError(f"Could not connect to MQTT server.")

    def refresh(self):
        try:
            if not is_connected():
                connect()
            _LOGGER.info(f'Refresh Hyper2000: {self._topic_refresh}')
            self._client.publish(self._topic_refresh,'{"properties": ["getAll"]}')
        except Exception as err:
            _LOGGER.error("Error while refreshing : %s", self.hid)
            _LOGGER.error(err)

    def onMessage(client, userdata, msg):
        try:
            _LOGGER.info(f"Receive: {msg}")
        except Exception as err:
            _LOGGER.error(err)

    def onConnect(self, _client, userdata, flags, rc):
        _LOGGER.info(f"Has been connected successfully")
        self.connected = True

    def onDisconnect(self, _client, userdata, rc):
        self._client.disconnect()

    def disconnect(self):
        _LOGGER.info(f"Disconnecting from {self._host}:{self._port} and clean subs")
        self._client.unsubscribe(self._topic)
        self._client.disconnect()
        self._client.loop_stop()
        self.connected = False

    def dumps_payload(payload):
        return str(payload).replace("'", '"').replace('"{', "{").replace('}"', "}")

    # async def publish(self, instance, msg: dict, wait=False) -> bool:
    #     async with self._lock:
    #         if not self.is_connected:
    #             return _LOGGER.info(f"publish fails {msg}, broker isn't connected.")
    #         self._payload = None

    #         # Change selected index.
    #         async def publish_and_wait():
    #             self._client.publish(self._topic_push, self.dumps_payload(msg))
    #             while True:
    #                 await asyncio.sleep(0.2)
    #                 if self._payload is not None:
    #                     break

    #         # We will wait for any message for the next 3 seconds else we will return
    #         _LOGGER.info(f"Publishing: {self.dumps_payload(msg)}")
    #         task = self._loop.create_task(publish_and_wait())
    #         if wait:
    #             await asyncio.wait_for(task, 5)

    @property
    def is_connected(self) -> bool:
        return self._client and self._client.is_connected()
