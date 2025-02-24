"""Interfaces with the Zendure Integration api sensors."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .hyper2000 import Hyper2000

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: any,
    async_add_entities: AddEntitiesCallback,
):
    Hyper2000.addSensors = async_add_entities
