# zendure_h2k/README.md

# Zendure H2K Integration

This project is a custom integration for Home Assistant that allows users to connect and manage their Zendure devices, specifically the Hyper 2000 model.

## Overview

The Zendure H2K integration provides a seamless way to interact with Zendure's API, enabling users to retrieve device information, manage connections, and utilize MQTT for real-time updates.

## Files

- `custom_components/zendure_h2k/__init__.py`: Marks the directory as a Python package and may contain initialization code.
- `custom_components/zendure_h2k/api.py`: Contains the `API` class for handling connections to the Zendure API, managing authentication, and retrieving device information.
- `custom_components/zendure_h2k/hyper2000.py`: Defines the `Hyper2000` class, representing the Hyper 2000 device with relevant properties and methods.
- `custom_components/zendure_h2k/manifest.json`: Contains metadata about the custom component, including its name, version, and dependencies.
- `.gitignore`: Specifies files and directories to be ignored by Git.

## Installation

1. Clone this repository to your local machine.
2. Copy the `zendure_h2k` folder into your Home Assistant `custom_components` directory.
3. Restart Home Assistant to load the new integration.

## Usage

After installation, configure the integration in Home Assistant by providing your Zendure account credentials. The integration will automatically discover and manage your Hyper 2000 devices.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.