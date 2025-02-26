import logging
import json
from enum import StrEnum
from paho.mqtt import client as mqtt_client
from base64 import b64decode

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .hyper2000 import Hyper2000

_LOGGER = logging.getLogger(__name__)

SF_API_BASE_URL = "https://app.zendure.tech"


class API:
    """Class for Zendure API."""

    def __init__(self, hass: HomeAssistant, zen_api, username, password):
        self.hass = hass
        self.baseUrl = f"{SF_API_BASE_URL}"
        self.zen_api = zen_api
        self.username = username
        self.password = password
        self.session = None
        self.token: str = None
        self.mqttUrl: str = None
        self.hypers: dict[str, Hyper2000] = {}
        self.clients: dict[str, mqtt_client] = {}

    async def connect(self) -> bool:
        _LOGGER.info("Connecting to Zendure")
        self.session = async_get_clientsession(self.hass)
        self.headers = {
            "Content-Type": "application/json",
            "Accept-Language": "en-EN",
            "appVersion": "4.3.1",
            "User-Agent": "Zendure/4.3.1 (iPhone; iOS 14.4.2; Scale/3.00)",
            "Accept": "*/*",
            "Blade-Auth": "bearer (null)",
        }

        SF_AUTH_PATH = "/auth/app/token"
        authBody = {
            "password": self.password,
            "account": self.username,
            "appId": "121c83f761305d6cf7e",
            "appType": "iOS",
            "grantType": "password",
            "tenantId": "",
        }

        try:
            url = f"{self.zen_api}{SF_AUTH_PATH}"
            response = await self.session.post(url=url, json=authBody, headers=self.headers)
            if response.ok:
                respJson = await response.json()
                json = respJson["data"]
                self.token = json["accessToken"]
                self.mqttUrl = json["iotUrl"]
                self.headers["Blade-Auth"] = f"bearer {self.token}"
            else:
                _LOGGER.error("Authentication failed!")
                _LOGGER.error(response.text)
                return False

        except Exception as e:
            _LOGGER.exception(e)
            _LOGGER.info("Unable to connected to Zendure!")
            return False

        _LOGGER.info("Connected to Zendure!")
        return True

    def disconnect(self):
        self.session.close()
        self.session = None

    async def getHypers(self, hass: HomeAssistant):
        SF_DEVICELIST_PATH = "/productModule/device/queryDeviceListByConsumerId"
        SF_DEVICEDETAILS_PATH = "/device/solarFlow/detail"
        self.hypers: dict[str, Hyper2000] = {}
        try:
            if self.session is None:
                await self.connect()

            cloud = self.mqtt(
                self.token,
                "zenApp",
                b64decode("SDZzJGo5Q3ROYTBO".encode()).decode("latin-1"),
            )
            self.clients["cloud"] = cloud

            url = f"{self.zen_api}{SF_DEVICELIST_PATH}"
            _LOGGER.info("Getting device list ...")

            response = await self.session.post(url=url, headers=self.headers)
            if response.ok:
                respJson = await response.json()
                devices = respJson["data"]
                for dev in devices:
                    _LOGGER.debug(f"prodname: {dev['productName']}")
                    if dev["productName"] == "Hyper 2000":
                        try:
                            h: Hyper2000 = None
                            payload = {"deviceId": dev["id"]}
                            url = f"{self.zen_api}{SF_DEVICEDETAILS_PATH}"
                            _LOGGER.info(f"Getting device details for [{dev['id']}] ...")
                            response = await self.session.post(url=url, json=payload, headers=self.headers)
                            if response.ok:
                                respJson = await response.json()
                                data = respJson["data"]
                                h = Hyper2000(
                                    hass,
                                    data["deviceKey"],
                                    data["productKey"],
                                    data["deviceName"],
                                    data,
                                )
                                if h.hid:
                                    _LOGGER.info(f"Hyper: [{h.hid}]")
                                    self.hypers[data["deviceKey"]] = h
                                    _LOGGER.info(f"Data: {data}")
                                    cloud.subscribe(f"/{h.prodkey}/{h.hid}/#")
                                    cloud.subscribe(f"iot/{h.prodkey}/{h.hid}/#")
                                else:
                                    _LOGGER.info(f"Hyper: [??]")
                            else:
                                _LOGGER.error("Fetching device details failed!")
                                _LOGGER.error(response.text)
                        except Exception as e:
                            _LOGGER.exception(e)
            else:
                _LOGGER.error("Fetching device list failed!")
                _LOGGER.error(response.text)
        except Exception as e:
            _LOGGER.exception(e)

    def initialize(self):
        _LOGGER.info("init hypers")
        try:
            for k, h in self.hypers.items():
                h.create_sensors()

        except Exception as err:
            _LOGGER.error(err)

    def refresh(self):
        _LOGGER.info("refresh hypers")
        try:
            cloud = self.clients["cloud"]
            for k, h in self.hypers.items():
                cloud.publish(h._topic_read, '{"properties": ["getAll"]}')

            # if (h := self.hypers.get('ajNtx5P6', None)):
            #     cloud.publish(h._topic_function,'{"deviceKey": "ajNtx5P6", "function": "deviceAutomation", "arguments": [{"autoModelProgram": 1, "autoModelValue": { "outPower": 123} , "msgType": 1, "autoModel": 8}]}')
        except Exception as err:
            _LOGGER.error(err)

    @property
    def controller_name(self) -> str:
        """Return the name of the controller."""
        return self.zen_api.replace(".", "_")

    def mqtt(self, client, username, password) -> mqtt_client:
        _LOGGER.info(f"Create mqtt client!! {client}")
        client = mqtt_client.Client(client_id=client, clean_session=False)
        client.username_pw_set(username=username, password=password)
        client.on_connect = self.onConnect
        client.on_disconnect = self.onDisconnect
        client.on_message = self.onMessage
        client.connect(self.mqttUrl, 1883, 120)

        client.suppress_exceptions = True
        client.loop()
        client.loop_start()
        return client

    def onConnect(self, _client, userdata, flags, rc):
        _LOGGER.info(f"Client has been connected")

    def onDisconnect(self, _client, userdata, rc):
        _LOGGER.info(f"Client has been disconnected")

    def onMessage(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            parameter = msg.topic.split("/")[-1]
            if parameter == "report":
                deviceid = payload["deviceId"]
                if (properties := payload.get("properties", None)) and (hyper := self.hypers.get(deviceid, None)):
                    try:
                        for key, value in properties.items():
                            if sensor := hyper.sensors.get(key, None):
                                try:
                                    self.hass.loop.call_soon_threadsafe(sensor.update_value, value)
                                    sensor.update_value(value)
                                except Exception as err:
                                    _LOGGER.error(f"Error value: {deviceid} {err} {key} => {value}")
                            elif isinstance(value, (int, float)):
                                self.hass.loop.call_soon_threadsafe(hyper.onAddSensor, key)
                            else:
                                _LOGGER.info(f"Found unknown state value:  {deviceid} {key} => {value}")

                    except Exception as err:
                        _LOGGER.error(f"Error update: {err} {deviceid} => {payload}")
                else:
                    _LOGGER.info(f"Found unknown state value: {deviceid} {msg.topic} {payload}")
            elif parameter == "log" and payload["logType"] == 2:
                # battery information
                deviceid = payload["deviceId"]
                if hyper := self.hypers.get(deviceid, None):
                    data = payload["log"]["params"]
                    hyper.update_battery(data)
            else:
                _LOGGER.info(f"Receive: {msg.topic} => {payload}")
        except Exception as err:
            _LOGGER.error(err)
