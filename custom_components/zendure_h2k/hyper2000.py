from __future__ import annotations
import asyncio
import logging
import hashlib
import json
from paho.mqtt import client as mqtt_client
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class Hyper2000():
    addSensor: AddEntitiesCallback

    def __init__(self, hass: HomeAssistant, h_id, h_prod, name, device: dict) -> None:
        """Initialise."""
        self._hass = hass
        self.hid = h_id
        self.prodkey = h_prod 
        self.name = name 
        self.unique = "".join(name.split())
        self.properties : dict[str, any] = {}
        self.sensors : dict[str, Hyper2000Entity] = {}
        # for key, value in device.items():
        #     self.properties[key] = value
        self._client: mqtt_client = None
        self._loop = asyncio.get_running_loop()
        self._lock = asyncio.Lock()
        self.connected : bool = False
        self._topic_refresh = f"iot/{self.prodkey}/{self.hid}/properties/read"
        self.mqttUrl: str = None
        self.appKey: str = None
        self.secret: str = None

    def connect(self):
        try:
            _LOGGER.info(f'Connect Hyper2000: {self.hid} {self.prodkey} {self.name}')
            self.onAddSensor("hyperTemp")
            if self.mqttUrl:
                self._client = mqtt_client.Client(client_id=f'ha-{self.hid}', clean_session=False)
                self._client.username_pw_set(username=str(self.appKey), password=str(self.secret))
                self._client.on_message = self.onMessageCloud
                state = self._client.connect(self.mqttUrl, 1883, 120)
                self._client.subscribe(f'{self.appKey}/{self.hid}/state')
                self._client.subscribe(f'{self.appKey}/sensor/#')
                self._client.subscribe(f'{self.appKey}/switch/#')
                _LOGGER.info(f"Ready cloud {self.hid} {self.name}")
            else:
                self._client = mqtt_client.Client(client_id=str(self.hid), clean_session=False)
                pwd = hashlib.md5(self.hid.encode()).hexdigest().upper()[8:24]
                self._client.username_pw_set(username=str(self.hid), password=str(pwd))
                self._client.on_message = self.onMessage
                state = self._client.connect("mqtteu.zen-iot.com", 1883, 120)
                self._client.subscribe(f'/{self.prodkey}/{self.hid}/#')
                self._client.subscribe(f"iot/{self.prodkey}/{self.hid}/#")
                _LOGGER.info(f"Ready local {self.hid} {self.name}")

            self._client.suppress_exceptions = True
            self._client.loop()
            self._client.loop_start()
            self._client.on_connect = self.onConnect
            self._client.on_disconnect = self.onDisconnect
            self.connected = self._client.is_connected()

        except Exception as err:
            _LOGGER.error("Error while connecting : %s", self.hid)
            _LOGGER.error(err)

    def refresh(self):
        try:
            if not self.mqttUrl:
                _LOGGER.info(f'Refresh Hyper2000: {self._topic_refresh}')
                self._client.publish(self._topic_refresh,'{"properties": ["getAll"]}')
            else:
                self._client.publish(self._topic_refresh,'{"properties": ["getAll"]}')
        except Exception as err:
            _LOGGER.error("Error while refreshing : %s", self.hid)
            _LOGGER.error(err)

    @callback
    def onMessage(self, client, userdata, msg):
        try:
            _LOGGER.info(f"Receive: {self.hid} => {msg.topic}")
            value = msg.payload.decode()
            _LOGGER.info(value)
        except Exception as err:
            _LOGGER.error(err)
            
    @callback
    def onMessageCloud(self, client, userdata, msg):
        try:
            if not msg.payload:
                _LOGGER.info(f"Cloud property: {msg.topic} => {msg}")
                return
            payload = json.loads(msg.payload.decode())
            parameter = msg.topic.split('/')[-1]
            if parameter == 'config':
                propertyName = payload['name']
                if not propertyName in self.properties:
                    try:
                        _LOGGER.info(f"Cloud property: {self.hid} {msg.topic} => {payload}")
                        self._hass.loop.call_soon_threadsafe(self.onAddSensor, propertyName)
                    except Exception as err:
                        _LOGGER.error(f"Error {err} create sensor:  {self.hid} {msg.topic}")
            elif parameter == 'state':
                for p in payload:
                    if sensor := self.sensors.get(p, None):
                        try:
                            _LOGGER.info(f"Update sensor:  {self.hid} {msg.topic}")
                            sensor.update_value(payload[p])
                        except ValueError:
                            _LOGGER.error(f"Error value: {p} => {payload[p]}")
                    else:
                        _LOGGER.info(f"Found unknown state value: {self.hid} {msg.topic}")
            else:
                _LOGGER.info(f"Cloud property: {parameter} => {payload}")

        except Exception as err:
            _LOGGER.error(err)

    def onAddSensor(self, propertyName: Str):
        try:
            _LOGGER.info(f"{self.hid} new sensor: {propertyName}")
            sensor = Hyper2000Sensor(self, propertyName)
            self.properties[propertyName] = sensor
            self.sensors[propertyName] = sensor
            self.addSensor([sensor])
        except Exception as err:
            _LOGGER.error(err)

    def onConnect(self, _client, userdata, flags, rc):
        _LOGGER.info(f"{self.hid} has been connected successfully")
        self.connected = True

    def onDisconnect(self, _client, userdata, rc):
        self._client.disconnect()

    def disconnect(self):
        _LOGGER.info(f"Disconnecting and clean subs")
        # self._client.unsubscribe(self._topic)
        self._client.disconnect()
        self._client.loop_stop()
        self.connected = False

    @property
    def is_connected(self) -> bool:
        return self._client and self._client.is_connected()

    def dumps_payload(payload):
        return str(payload).replace("'", '"').replace('"{', "{").replace('}"', "}")


class Hyper2000Sensor(SensorEntity):
    def __init__(
        self, hyper: Hyper2000, name
    ) -> None:
        """Initialize a Hyper2000 entity."""
        self._attr_available = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hyper.name)},
            "name": hyper.name,
            "manufacturer": "Zendure",
            "model": hyper.prodkey,
        }
        self._attr_name = f"{hyper.name} {name}"
        self._attr_should_poll = False
        self._attr_unique_id = f"{hyper.unique}-{name}"
        self.hyper = hyper

    def update_value(self, state):
        try:
            self._attr_native_value = state
            self.schedule_update_ha_state()
        except Exception as err:
            _LOGGER.error(f"Error {err} setting state value: {self.hyper.name} => {state}")

    # @property
    # def native_unit_of_measurement(self) -> str | None:
    #     """Return unit of temperature."""
    #     return UnitOfTemperature.CELSIUS

    @property
    def state_class(self) -> str | None:
        """Return state class."""
        # https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes
        return SensorStateClass.MEASUREMENT

    @property 
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        if self._attr_native_value is not None:
            try:
                return float(round(self._attr_native_value, 3))
            except Exception as err:
                _LOGGER.error(f"Error {err} convert state value: {self.hyper.name} => {self._attr_native_value}")
        return None
