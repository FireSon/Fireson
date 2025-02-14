"""The Zendure Integration integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .coordinator import ZendureCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type MyConfigEntry = ConfigEntry[RuntimeData]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: MyConfigEntry) -> bool:
    """Set up Zendure Integration from a config entry."""

    # Create the coordinator
    coordinator = ZendureCoordinator(hass, config_entry)

    # Add the coordinator and update listener to config runtime data
    config_entry.runtime_data = RuntimeData(coordinator)

    # This calls the async_setup method in each of your entity type files.
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    await coordinator.async_config_entry_first_refresh()
    if not coordinator.api.connected:
        raise ConfigEntryNotReady

    # Initialise a listener for config flow options changes.
    config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    # Return true to denote a successful setup.
    return True


async def _async_update_listener(hass: HomeAssistant, config_entry):
    """Handle config options update."""
    # Reload the integration when the options change.
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Delete device if selected from UI."""
    # Adding this function shows the delete device option in the UI.
    # Remove this function if you do not want that option.
    # You may need to do some checks here before allowing devices to be removed.
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: MyConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when you remove your integration or shutdown HA.
    # If you have created any custom services, they need to be removed here too.

    # Unload platforms and return result
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
