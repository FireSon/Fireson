from enum import StrEnum
import os
import sys
import logging
import json
from flask import session
import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .hyper2000 import Hyper2000

_LOGGER = logging.getLogger(__name__)

SF_API_BASE_URL = "https://app.zendure.tech"


class API:
    """Class for Zendure API."""
    def __init__(self, hass: HomeAssistant, zen_api, username, password):
        self.hass = hass
        self.baseUrl = f'{SF_API_BASE_URL}'
        self.zen_api = zen_api
        self.username = username
        self.password = password
        self.session = None

    async def connect(self) -> bool:
        _LOGGER.info("Connecting to Zendure")
        self.session = async_get_clientsession(self.hass)
        self.headers = {
                'Content-Type':'application/json',
                'Accept-Language': 'en-EN',
                'appVersion': '4.3.1',
                'User-Agent': 'Zendure/4.3.1 (iPhone; iOS 14.4.2; Scale/3.00)',
                'Accept': '*/*',
                'Blade-Auth': 'bearer (null)'
            }

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
            response = await self.session.post(url=url, json=authBody, headers=self.headers)
            if response.ok:
                respJson = await response.json()
                token = respJson["data"]["accessToken"]
                self.headers["Blade-Auth"] = f'bearer {token}'
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

    async def getHypers(self, hass: HomeAssistant) -> dict[str, Hyper2000]:
        SF_DEVICELIST_PATH = "/productModule/device/queryDeviceListByConsumerId"
        SF_DEVICEDETAILS_PATH = "/device/solarFlow/detail"
        SF_DEVICEDSECRET = "/developer/api/apply"
        hypers : dict[str, Hyper2000] = {}
        try:
            if self.session is None:
                await self.connect()
            url = f'{self.zen_api}{SF_DEVICELIST_PATH}'
            _LOGGER.info("Getting device list ...")

            response = await self.session.post(url=url, headers=self.headers)
            if response.ok:
                respJson = await response.json()
                devices = respJson["data"]
                for dev in devices:
                    _LOGGER.debug(f'prodname: {dev["productName"]}')
                    if dev["productName"] == 'Hyper 2000':
                        try:
                            h : hyper2000 = None
                            payload = {"deviceId": dev["id"]}
                            url = f'{self.zen_api}{SF_DEVICEDETAILS_PATH}'
                            _LOGGER.info(f'Getting device details for [{dev["id"]}] ...')
                            response = await self.session.post(url=url, json=payload, headers=self.headers)
                            if response.ok:
                                respJson = await response.json()
                                data = respJson["data"]
                                h = Hyper2000(hass, data["deviceKey"], data["productKey"], data["deviceName"], data)
                                if h.hid:
                                    _LOGGER.info(f'Hyper: [{h.hid}] ')
                                    hypers[data["deviceKey"]] = h
                                else:
                                    _LOGGER.info(f'Hyper: [??] ')

                                # Get the appsecret 
                                payload = {"account": self.username,"snNumber": data["snNumber"]}
                                url = f'{self.zen_api}{SF_DEVICEDSECRET}'
                                response = await self.session.post(url=url, json=payload, headers=self.headers)
                                if response.ok:
                                    respJson = await response.json()
                                    data = respJson["data"]
                                    h.mqttUrl = data["mqttUrl"]
                                    h.appKey = data["appKey"]
                                    h.secret = data["secret"]
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


class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""
