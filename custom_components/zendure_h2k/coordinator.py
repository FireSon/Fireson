"""Zendure Integration integration using DataUpdateCoordinator."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HassJobType,
    State,
    callback as ha_callback,
)

from .api import API, APIAuthError, Device, DeviceType, Hyper2000
from .const import (
    DEFAULT_SCAN_INTERVAL,
    CONF_CONSUMED,
    CONF_PRODUCED,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZendureAPIData:
    """Class to hold api data."""

    controller_name: str
    devices: list[Device]


class ZendureCoordinator(DataUpdateCoordinator):
    """My Zendure coordinator."""

    data: ZendureAPIData
    hypers: dict[str, Hyper2000] = {}
    addSensor: AddEntitiesCallback

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        # Set variables from values entered in config flow setup
        self._hass = hass
        self.host = config_entry.data[CONF_HOST]
        self.user = config_entry.data[CONF_USERNAME]
        self.pwd = config_entry.data[CONF_PASSWORD]
        self._hyper_callbacks = []

        # async_track_state_change_event(
        #     self._hass,
        #     self.produced,
        #     self._async_update_energy,
        # )

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
        )

        # Set variables from values entered in config flow setup
        self.consumed: str = config_entry.data[CONF_CONSUMED]
        self.produced: str = config_entry.data[CONF_PRODUCED]
        _LOGGER.debug(f"Energy sensors: {self.consumed} - {self.produced}")

        async_track_state_change_event(
            self._hass,
            self.consumed,
            self._async_update_energy,
            job_type=HassJobType.Callback,
        )
        async_track_state_change_event(
            self._hass,
            self.produced,
            self._async_update_energy,
            job_type=HassJobType.Callback,
        )
        _LOGGER.debug(f"Energy initalized: {self.consumed} - {self.produced}")

        # Initialise your api here
        self.api = API(host=self.host, user=self.user, pwd=self.pwd)

    @ha_callback
    def _async_update_energy(self, event: Event[EventStateChangedData]) -> None:
        """Handle linked battery charging sensor state change listener callback."""
        _LOGGER.debug('Energy usage callback')

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            if not self.hypers:
                self.hypers =   {
                    "123", Hyper2000("123"),
                    "456", Hyper2000("456"),
                    "789", Hyper2000("789"),
                }

            if not self.api.connected:
                await self.hass.async_add_executor_job(self.api.connect)
            devices = await self.hass.async_add_executor_job(self.api.get_devices)
            self.do_callback()
        except APIAuthError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err
        except Exception as err:
            # This will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # What is returned here is stored in self.data by the DataUpdateCoordinator
        return ZendureAPIData(self.api.controller_name, devices)

    def subscribe_hyper_callback(self, callback):
        """ Subscribe callback to execute """
        self._hyper_callbacks.append(callback)

    def unsubscribe_hyper_callback(self, callback):
        """ Register callback to execute """
        self._hyper_callbacks.remove(callback)

    def do_callback(self, callback_arg=None):
        """ Execute callbacks registered for specified callback type """
        for callback in self._hyper_callbacks:
            try:
                if callback_arg is None:
                    callback()
                else:
                    callback(callback_arg)
            except Exception as e:
                self.logger.error("Error while executing callback : %s", e)

    def get_device_by_id(
        self, device_type: DeviceType, device_id: int
    ) -> Device | None:
        """Return device by device id."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        try:
            return [
                device
                for device in self.data.devices
                if device.device_type == device_type and device.device_id == device_id
            ][0]
        except IndexError:
            return None
