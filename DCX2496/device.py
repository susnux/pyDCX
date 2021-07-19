from typing import Union, Optional
from logging import getLogger
from enum import IntEnum
import re

from .channel import Channel, InputChannel, OutputChannel, _15db_range
from .connector import SerialConnector, DaemonConnector


logger = getLogger("pyDCX")
logger.setLevel("DEBUG")


class TransmitMode(IntEnum):
    REMOTE_RECEIVE = 0x04
    REMOTE_TRANSMIT = 0x08
    REMOTE_TRANSCEIVE = REMOTE_RECEIVE | REMOTE_TRANSMIT


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


class Device:
    DCX_HEADER = b"\xF0\x00\x20\x32"  # Identification header for serial com

    def __init__(self, connection, batch_mode=False, device_id=0):
        """
        Create the DCX class for communication
        :param device_id: Set the DCX device ID (default is 0, valid 0 - 15)
        :param connection: Serial port or network address
        """
        assert 0 <= device_id < 16
        self.batch_mode = batch_mode
        self.device_id = device_id
        self.channels: dict[Channel, Union[InputChannel, OutputChannel]] = {
            **{
                idx: InputChannel(channel=Channel(idx), device=self)
                for idx in range(Channel.INPUT_A, Channel.INPUT_SUM + 1)
            },
            **{
                idx: OutputChannel(channel=Channel(idx), device=self)
                for idx in range(Channel.OUTPUT_1, Channel.OUTPUT_6 + 1)
            },
        }
        self._remote_mode = TransmitMode.REMOTE_RECEIVE
        if re.match(r"(COM\d+|/dev/tty.+)", connection, re.IGNORECASE):
            self._connector = SerialConnector(connection)
        else:
            self._connector = DaemonConnector(connection)
        # For batch mode
        self.__commands = []

    def search_device(self):
        """
        Search serial connection for DCX device
        :return: None or PING response if async is set to False
        """
        backup_id = self.device_id
        self.device_id = 0x20
        try:
            return self.__do_call(0x40)
        finally:
            self.device_id = backup_id

    def transmit_mode(self, mode: Optional[TransmitMode] = None):
        """
        Set transmit remote mode of current DCX device
        :param mode: REMOTE_RECEIVE or REMOTE_TRANSMIT (or both)
        :return: Current mode if mode was set to None, else None
        """
        if mode is None:
            return self._remote_mode
        else:
            self._remote_mode = mode
            data = bytearray(bytes([mode]))
            data.append(0x00)
            return self.__do_call(0x3F, data)

    def ping(self):
        """
        Get status of current DCX device
        :return: PingResponse
        """
        return self.__do_call(0x44, b"\x00\x00")

    def dump(self, part=0):
        """
        Dump all settings of current DCX device
        :param part: Data part 0 or 1
        :return: DumpResponse
        """
        data = bytearray(b"\x01\x00")
        data.append(part)
        return self.__do_call(0x50, data)

    def set_out_configuration(self, configuration: OutputConfiguration):
        """
        OUT CONFIGURATION selects the general operating mode, see section 4.2.1 of the manual
        :param configuration: OutputConfiguration
        """
        return self._invoke(0x05, Channel.SETUP, configuration.value)

    def enable_stereo_link(self, enable=True):
        """
        Determine whether processing with EQs, limiter, etc. is effective on the linked outputs,
         or whether the settings for each output can be made independently.
         See section 4.2.1 on page 8 of manual.
        :param enable: True to enable, False to disable
        """
        return self._invoke(0x06, Channel.SETUP, int(enable))

    def set_input_stereo_link(self, configuration: int):
        """
        Set input link, if enabled settings for Input A are copied to selected channel.
        See section 4.2.1, page 9 of manual.
        :param configuration: 0 (disable), 1 (A+B), 2 (A+B+C), 3 (A+B+C+SUM)
        """
        assert 0 <= configuration <= 3
        return self._invoke(0x07, Channel.SETUP, configuration)

    def mute_outputs(self, mute: bool = True):
        """
        Mute all outputs
        :param mute: True to mute, False to unmute
        """
        self._invoke(0x15, Channel.SETUP, int(mute))

    def set_sum_input_gain(self, input_channel: Channel, gain: float):
        """
        Set input gain for channel into the SUM channel
        :param input_channel: A ... C
        :param gain: -15.0 .. 15.0 dB
        """
        assert Channel.INPUT_A <= input_channel <= Channel.INPUT_C
        return self._invoke(0x16 + input_channel - Channel.INPUT_A, Channel.SETUP, _15db_range(gain))

    def send(self):
        """
        When in batch mode, this will send the previous commands
        :return: self
        """
        if len(self.__commands) > 0:
            data = bytearray([len(self.__commands)])
            for command in self.__commands:
                data.extend(command)
            self.__do_call(0x20, data)
            self.__commands.clear()
        return self

    def _invoke(self, parameter, channel, value):
        logger.debug(f"Invoke command {value} on channel {channel} with parameter {parameter}")
        print(f"Invoke command with parameter {parameter} on channel {channel} with data {value}")
        data = self.__command(channel, parameter, value)
        self.__commands.append(data)
        if self.batch_mode:
            return self
        else:
            self.send()

    def __command(self, channel, parameter, value):
        value = int(value)
        value_low = value & 0x7F
        value_high = (value >> 7) & 0xFF
        b = bytearray(bytearray(bytes([channel])))
        b.append(parameter)
        b.append(value_high)
        b.append(value_low)
        return b

    def __do_call(self, function, data=None):
        call = bytearray(self.DCX_HEADER)
        call.append(self.device_id)
        call.append(0x0E)
        call.append(function)
        if data is not None:
            call.extend(data)
        call.append(0xF7)
        return self._connector.handle_command(call)
