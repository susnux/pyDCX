from typing import Union, Optional
from logging import getLogger
from enum import IntEnum

from .channel import Channel, InputChannel, OutputChannel, _15db_range
from .connector import SerialConnector, DaemonConnector
from .constants import DCX_HEADER, FunctionBytes, OutputConfiguration, TransmitMode
from .dump_lut import dump_lut
from .responses import DumpResponse

logger = getLogger("pyDCX")
logger.setLevel("DEBUG")


class Device:
    def __init__(self, connection: str, batch_mode=True, device_id=0):
        """
        Create the DCX class for communication
        :param device_id: Set the DCX device ID (valid 0 - 15, displayed as +1)
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
        self._remote_mode = TransmitMode.RECEIVE
        if connection.startswith(("com", "COM", "/")):
            self._connector = SerialConnector(connection)
        else:
            self._connector = DaemonConnector(connection)
        # For batch mode
        self.__commands = []

    def search_device(self):
        """
        Search serial connection for DCX device
        :return: SearchResponse
        """
        backup_id = self.device_id
        self.device_id = 0x20
        try:
            return self.__do_call(FunctionBytes.SEARCH)
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
            return self.__do_call(FunctionBytes.TRANSMIT, data)

    def ping(self):
        """
        Get status of current DCX device
        :return: PingResponse
        """
        response = self.__do_call(FunctionBytes.PING, b"\x00\x00")
        for channel in self.channels.keys():
            self.channels[channel].level = response.channels[channel].level
            self.channels[channel].limited = response.channels[channel].limited
        return response

    def dump(self, part=None):
        """
        Dump all settings of current DCX device
        Call to refresh internal storage of settings (no parameter needed)
        :param part: Data part 0 or 1, None means both
        :return: DumpResponse
        """
        if part is None:
            dr = DumpResponse(self.dump(0).data + self.dump(1).data)
            self._parse_dump_with_lut(dr.payload)
            return dr
        else:
            assert 0 <= part <= 1
            data = bytearray(b"\x01\x00")
            data.append(part)
            return self.__do_call(FunctionBytes.DUMP, data)

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
        return self._invoke(0x15, Channel.SETUP, int(mute))

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

    def _parse_dump_with_lut(self, dump):
        for parameter in dump_lut.keys():
            for channel in Channel:
                if dump_lut[parameter][channel]:
                    value = 0
                    for idx, mapping in enumerate(dump_lut[parameter][channel]):
                        shift = min(1, idx) * 7 + 1 * max(0, idx - 1)
                        if isinstance(mapping, tuple):
                            value += (dump[mapping[0]] & (1 << mapping[1])) << shift
                        else:
                            value += dump[mapping[0]] << shift
                    if channel is not Channel.SETUP:
                        self.channels[channel][parameter] = value
                    else:
                        self[parameter] = value

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
        call = bytearray(DCX_HEADER)
        call.append(self.device_id)
        call.append(0x0E)
        call.append(function)
        if data is not None:
            call.extend(data)
        call.append(0xF7)
        return self._connector.handle_command(call)
