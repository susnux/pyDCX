VERSION = "0.0.1a"
__version__ = VERSION

from .device import Device, TransmitMode
from .channel import Channel


class DCX2496(Device):
    """
    Main class for communication with the DCX2496
    """

    pass
