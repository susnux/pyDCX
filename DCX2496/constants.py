from enum import IntEnum

# Structure of serial communication:
# HEADER DEVICE_ID SEPARATOR FUNCTION PAYLOAD TERMINATOR

DCX_HEADER = b"\xF0\x00\x20\x32"
"""Identification header of serial communication"""

SEPARATOR_BYTE = 0x0E
"""Separator between device ID and function"""

TERMINATOR_BYTE = 0xF7
"""Terminal byte"""

FUNCTION_BYTE = 6
"""Index of the function byte"""


class FunctionBytes(IntEnum):
    """Known function bytes"""

    COMMAND = 0x20
    TRANSMIT = 0x3F
    SEARCH = 0x40
    PING = 0x44
    DUMP = 0x50


class TransmitMode(IntEnum):
    RECEIVE = 0x04
    TRANSMIT = 0x08
    TRANSCEIVE = RECEIVE | TRANSMIT


class OutputConfiguration(IntEnum):
    """Output configuration, see section 4.2.1 and Fig. 4.2 of manual"""

    MONO = 0
    """In MONO mode input A is the preset signal source for all outputs"""

    LMHLMH = 1
    """Input A routed to outputs 1, 2 and 3, and input B routed to outputs 4, 5 and 6"""

    LLMMHH = 2
    """Input A to outputs 1, 3 and 5, and input B to outputs 2, 4 and 6"""

    LHLHLH = 3
    """Input A can be routed to outputs 1 and 2, B to outputs 3 and 4, and C to outputs 5 and 6"""
