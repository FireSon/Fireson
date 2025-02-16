"""API Placeholder.

You should create your api seperately and have it hosted on PYPI.  This is included here for the sole purpose
of making this Zendure code executable.
"""

from dataclasses import dataclass
from enum import StrEnum
import os
import sys
import logging
import json
from flask import session
import requests

from random import choice, randrange
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

SF_API_BASE_URL = "https://app.zendure.tech"


class DeviceType(StrEnum):
    """Device types."""

    TEMP_SENSOR = "temp_sensor"
    DOOR_SENSOR = "door_sensor"
    OTHER = "other"


DEVICES = [
    {"id": 1, "type": DeviceType.TEMP_SENSOR},
    {"id": 1, "type": DeviceType.DOOR_SENSOR},
    {"id": 2, "type": DeviceType.TEMP_SENSOR},
    {"id": 2, "type": DeviceType.DOOR_SENSOR},
    {"id": 3, "type": DeviceType.TEMP_SENSOR},
    {"id": 3, "type": DeviceType.DOOR_SENSOR},
    {"id": 4, "type": DeviceType.TEMP_SENSOR},
    {"id": 4, "type": DeviceType.DOOR_SENSOR},
    {"id": 5, "type": DeviceType.TEMP_SENSOR},
    {"id": 5, "type": DeviceType.DOOR_SENSOR},
]


class Hyper2000:
    def __init__(self, id: str) -> None:
        """Initialise."""
        self.id = id
        self.connected: bool = False
        self.properties : dict[str, any]
        # self.sensors : dict[str, hyperSensor]


@dataclass
class Device:
    """API device."""

    device_id: int
    device_unique_id: str
    device_type: DeviceType
    name: str
    state: int | bool
    isNew: bool
  

class API:
    """Class for Zendure API."""
    def __init__(self, hass: HomeAssistant, zen_api, username, password):
        self.hass = hass
        self.baseUrl = f'{SF_API_BASE_URL}'
        self.zen_api = zen_api
        self.username = username
        self.password = password
        self.session = None

    async def connect(self):
        self.session = async_get_clientsession(self.hass, headers = {
                'Content-Type':'application/json',
                'Accept-Language': 'en-EN',
                'appVersion': '4.3.1',
                'User-Agent': 'Zendure/4.3.1 (iPhone; iOS 14.4.2; Scale/3.00)',
                'Accept': '*/*',
                'Blade-Auth': 'bearer (null)'
            })
        #retry = Retry(connect=3, backoff_factor=0.5)
        #adapter = HTTPAdapter(max_retries=retry)
        # self.session.mount('http://', adapter)
        # self.session.mount('https://', adapter)
        # self.session.headers = {
        #         'Content-Type':'application/json',
        #         'Accept-Language': 'en-EN',
        #         'appVersion': '4.3.1',
        #         'User-Agent': 'Zendure/4.3.1 (iPhone; iOS 14.4.2; Scale/3.00)',
        #         'Accept': '*/*',
        #         'Blade-Auth': 'bearer (null)'
        #     }

        SF_AUTH_PATH = "/auth/app/token"
        authBody = {
                'password': self.password,
                'account': self.username,
                'appId': '121c83f761305d6cf7e',
                'appType': 'iOS',
                'grantType': 'password',
                'tenantId': ''
            }
        
        try:
            url = f'{self.zen_api}{SF_AUTH_PATH}'
            _LOGGER.info("Authenticating with Zendure ...")

            response = await self.session.post(url=url, json=authBody)
            if response.ok:
                respJson = response.json()
                token = respJson["data"]["accessToken"]
                _LOGGER.info('Got bearer token!')
                self.session.headers["Blade-Auth"] = f'bearer {token}'
                return token
            else:
                _LOGGER.error("Authentication failed!")
                _LOGGER.error(response.text)
        except Exception as e:
            _LOGGER.exception(e)

    def disconnect(self):
        self.session.close()
        self.session = None

    async def getHypers(self, hypers: dict[str, Hyper2000]) -> dict[str, Hyper2000]:
        SF_DEVICELIST_PATH = "/productModule/device/queryDeviceListByConsumerId"
        SF_DEVICEDETAILS_PATH = "/device/solarFlow/detail"
        try:
            if self.session is None:
                await self.connect()
            url = f'{self.zen_api}{SF_DEVICELIST_PATH}'
            _LOGGER.info("Getting device list ...")
          
            response = await self.session.post(url=url)
            if response.ok:
                respJson = response.json()
                _LOGGER.info(json.dumps(respJson["data"], indent=2))
                devices = respJson["data"]
                ids = []
                for dev in devices:
                    if dev["productName"] == 'SolarFlow2.0':
                        payload = {"deviceId": dev["id"]}
                        try:
                            url = f'{self.zen_api}{SF_DEVICEDETAILS_PATH}'
                            _LOGGER.info(f'Getting device details for [{dev["id"]}] ...')
                            response = await self.session.post(url=url, json=payload)
                            if response.ok:
                                respJson = response.json()
                                _LOGGER.info(json.dumps(respJson["data"], indent=2))
                                device = respJson["data"]
                                h = hypers.get(dev["id"], None)
                                if h is None:
                                    hypers[dev["id"]] = h = Hyper2000(dev["id"])
                                for key, value in device.items():
                                    h.properties[key] = value
                                _LOGGER.info(f'Hyper2000[{dev["id"]}]: {h.properties}')
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
        return hypers


    @property
    def controller_name(self) -> str:
        """Return the name of the controller."""
        return self.zen_api.replace(".", "_")

    def get_devices(self) -> list[Device]:
        """Get devices on api."""
        return [
            Device(
                device_id=device.get("id"),
                device_unique_id=self.get_device_unique_id(
                    device.get("id"), device.get("type")
                ),
                device_type=device.get("type"),
                name=self.get_device_name(device.get("id"), device.get("type")),
                state=self.get_device_value(device.get("id"), device.get("type")),
                isNew=False,
            )
            for device in DEVICES
        ]

    def get_device_unique_id(self, device_id: str, device_type: DeviceType) -> str:
        """Return a unique device id."""
        if device_type == DeviceType.DOOR_SENSOR:
            return f"{self.controller_name}_D{device_id}"
        if device_type == DeviceType.TEMP_SENSOR:
            return f"{self.controller_name}_T{device_id}"
        return f"{self.controller_name}_Z{device_id}"

    def get_device_name(self, device_id: str, device_type: DeviceType) -> str:
        """Return the device name."""
        if device_type == DeviceType.DOOR_SENSOR:
            return f"DoorSensor{device_id}"
        if device_type == DeviceType.TEMP_SENSOR:
            return f"TempSensor{device_id}"
        return f"OtherSensor{device_id}"

    def get_device_value(self, device_id: str, device_type: DeviceType) -> int | bool:
        """Get device random value."""
        if device_type == DeviceType.DOOR_SENSOR:
            return choice([True, False])
        if device_type == DeviceType.TEMP_SENSOR:
            return randrange(15, 28)
        return randrange(1, 10)


class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""
