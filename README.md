# Zendure Integration

This integration Integrates the Hyper2000 into Home Assistant.
It seems possible to set the actual charge and discarge values, but this is not implemented yet.But testing seems hopefull :-)

## Features

- Get all telemetry data from your Hyper 2000

### 1.0.6 (2025-02-27) ALPHA

- First try to adjust battery output based upon home assistant sensor (for example P1 meter).

### 1.0.5 (2025-02-24) ALPHA

- The values are read from the Hyper 2000 and displayed in Home Assistant. Each 90 seconds the values are updated, or sooner when they are changing.
- You need to specify your Zendure username + password during the configuration of the integration. All your hyper2000 devices are found in the cloud. If you want to see the details enable the debug logging for the integration.
- Not all the sensors have the correct unit of measurement. This will be fixed in a later version.

## License

MIT License
