import logging

_LOGGER = logging.getLogger(__name__)


class Hyper2000:
    properties : dict[str, any]

    def __init__(self, id: str) -> None:
        """Initialise."""
        self.id = id
        self.connected: bool = False
        # self.sensors : dict[str, hyperSensor]

