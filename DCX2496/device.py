from typing import Union, Optional
from logging import getLogger
from enum import IntEnum
import re

from .channel import Channel, InputChannel, OutputChannel
from .connector import SerialConnector, DaemonConnector


logger = getLogger("pyDCX")
logger.setLevel("DEBUG")


class TransmitMode(IntEnum):
    REMOTE_RECEIVE = 0x04
    REMOTE_TRANSMIT = 0x08
    REMOTE_TRANSCEIVE = REMOTE_RECEIVE | REMOTE_TRANSMIT


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
        if re.match(r'(COM\d+|/dev/tty.+)', connection, re.IGNORECASE):
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
