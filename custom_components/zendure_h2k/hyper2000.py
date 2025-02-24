
from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class Hyper2000():
    addSensors: AddEntitiesCallback
 
    def __init__(self, hass: HomeAssistant, h_id, h_prod, name, device: dict) -> None:
        """Initialise."""
        self._hass = hass
        self.hid = h_id
        self.prodkey = h_prod 
        self.name = name 
        self.unique = "".join(name.split())
        self.properties : dict[str, any] = {}
        self.sensors : dict[str, Hyper2000Sensor] = {}
        # for key, value in device.items():
        #     self.properties[key] = value
        self._topic_read = f"iot/{self.prodkey}/{self.hid}/properties/read"
        self._topic_write = f"iot/{self.prodkey}/{self.hid}/properties/write"
        self._topic_function = f"iot/{self.prodkey}/{self.hid}/function/invoke"

    def create_sensors(self):

        def add(uniqueid: str, name: str, template: str = None, uom: str = None, deviceclass: str = None) -> Hyper2000Sensor:
            if template:
                s = Hyper2000Sensor(self, uniqueid, name, Template(template, self._hass), uom, deviceclass)
            else: 
                s = Hyper2000Sensor(self, uniqueid, name, None, uom, deviceclass)
            self.sensors[uniqueid] = s
            return s

        """Add Hyper2000 sensors."""
        _LOGGER.info(f"Adding sensors Hyper2000 {self.name}")
        sensors = [
            add('hubState', 'Hub State'),
            add('solarInputPower', 'Solar Input Power', None, 'W', 'power'),
            add('packInputPower', 'Pack Input Power', None, 'W', 'power'),
            add('outputPackPower', 'Output Pack Power', None, 'W', 'power'),
            add('outputHomePower', 'Output Home Power', None, 'W', 'power'),
            add('outputLimit', 'Output Limit', None, 'W'),
            add('inputLimit', 'Input Limit', None, 'W'),
            add('remainOutTime', 'Remain Out Time', None, 'min', 'duration'),
            add('remainInputTime', 'Remain Input Time', None, 'min', 'duration'),
            add('packState', 'Pack State', None),
            add('packNum', 'Pack Num', None),
            add('electricLevel', 'Electric Level', None, '%', 'battery'),
            add('socSet', 'socSet', '{{ value | int / 10 }}', '%'),
            add('minSoc', 'minSOC', '{{ value | int / 10 }}', '%'),
            add('inverseMaxPower', 'Inverse Max Power', None, 'W'),
            add('wifiState', 'WiFi State', '{{ value | bool('') }}'),
            add('heatState', 'Heat State', '{{ value | bool('') }}'),
            add('acMode', 'AC Mode', None),
            add('solarPower1', 'Solar Power 1', None, 'W', 'power'),
            add('solarPower2', 'Solar Power 2', None, 'W', 'power'),
            add('passMode', 'Pass Mode', None),
            add('hyperTmp', 'Hyper Temperature', '{{ (value | float/10 - 273.15) | round(2) }}', '°C', 'temperature'),

            # add('Batterie1maxTemp', 'Batterie 1 maxTemp', '{{ (value | float/10 - 273.15) | round(2) }}', '°C', 'temperature'),
            # add('Batterie1minVol', 'Batterie 1 minVol', '{{ (value | float/100) | round(2) }}', 'V', 'voltage'),
            # add('Batterie1maxVol', 'Batterie 1 maxVol', '{{ (value | float/100) | round(2) }}', 'V', 'voltage'),
            # add('Batterie1totalVol', 'Batterie 1 totalVol', '{{ (value | float/100) | round(2) }}', 'V', 'voltage'),
        ]
        Hyper2000.addSensors(sensors)


    def onAddSensor(self, propertyName: str, value = None):
        try:
            _LOGGER.info(f"{self.hid} new sensor: {propertyName}")
            sensor = Hyper2000Sensor(self, propertyName, propertyName)
            self.sensors[propertyName] = sensor
            Hyper2000.addSensors([sensor])
            if (value):
                sensor.update_value(value)
        except Exception as err:
            _LOGGER.error(err)

    def update_battery(self, data):
        _LOGGER.info(f"update_battery: {self.hid} => {data}")

    def dumps_payload(payload):
        return str(payload).replace("'", '"').replace('"{', "{").replace('}"', "}")


class Hyper2000Sensor(SensorEntity):
    def __init__(
        self, hyper: Hyper2000, uniqueid: str, name: str, template: Template | None = None, uom: str = None, deviceclass: str = None
    ) -> None:
        """Initialize a Hyper2000 entity."""
        self._attr_available = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hyper.name)},
            "name": hyper.name,
            "manufacturer": "Zendure",
            "model": hyper.prodkey,
        }
        self.hyper = hyper
        self._attr_name = f"{hyper.name} {name}"
        self._attr_should_poll = False
        self._attr_unique_id = f"{hyper.unique}-{uniqueid}"
        self._attr_native_unit_of_measurement = uom
        self._value_template: Template | None = template
        self._attr_device_class = deviceclass

    def update_value(self, value):
        try:
            _LOGGER.info(f"Update sensor:  {self._attr_name} => {value}")

            if self._value_template is not None:
                self._attr_native_value = self._value_template.async_render_with_possible_json_value(value, None)
                self.schedule_update_ha_state()
            elif isinstance(value, (int, float)):
                self._attr_native_value =  int(value)
                self.schedule_update_ha_state()
        except Exception as err:
            _LOGGER.error(f"Error {err} setting state: {self._attr_name} => {value}")
