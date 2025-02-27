"""Zendure Integration integration using DataUpdateCoordinator."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import (
    Event,
    EventStateChangedData,
    callback,
)

from .api import API, Hyper2000
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


class ZendureCoordinator(DataUpdateCoordinator[int]):
    """My Zendure coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        # Set variables from values entered in config flow setup
        self._hass = hass
        self.host = config_entry.data[CONF_HOST]
        self.user = config_entry.data[CONF_USERNAME]
        self.pwd = config_entry.data[CONF_PASSWORD]
        self._outpower = 0

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
            always_update=True,
        )

        # Set variables from values entered in config flow setup
        self.consumed: str = config_entry.data[CONF_CONSUMED]
        self.produced: str = config_entry.data[CONF_PRODUCED]

        if self.consumed and self.produced:
            # Set variables from values entered in config flow setup
            _LOGGER.info(f"Energy sensors: {self.consumed} - {self.produced} to _async_update_energy")
            async_track_state_change_event(self._hass, [self.consumed, self.produced], self._async_update_energy)

        # Initialise your api here
        self.api = API(self._hass, self.host, self.user, self.pwd)

    async def initialize(self) -> bool:
        _LOGGER.info("Start initialize")
        try:
            if not await self.api.connect():
                return False
            await self.api.getHypers(self._hass)
            self.api.initialize()
            _LOGGER.info(f"Found: {len(self.api.hypers)} hypers")

        except Exception as err:
            _LOGGER.error(err)
        return True

    async def async_update_data(self):
        _LOGGER.debug("async_update_data")
        self.api.refresh()
        self._schedule_refresh()

    @callback
    def _async_update_energy(self, event: Event[EventStateChangedData]) -> None:
        """Publish state change to MQTT."""
        try:
            _LOGGER.info("_async_update_energy")
            if (new_state := event.data["new_state"]) is None:
                return

            h: Hyper2000 = list(self.api.hypers.values())[0]
            currpower = int(h.sensors["outputHomePower"].state)
            power = int(float(new_state.state))

            if event.data["entity_id"] == self.consumed:
                currpower += power
            elif event.data["entity_id"] == self.consumed:
                currpower -= power

            # Update the power
            self.api.update_outpower(h, currpower)

        except Exception as err:
            _LOGGER.error(err)
