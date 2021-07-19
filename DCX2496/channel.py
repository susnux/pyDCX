from enum import IntEnum


def _map_numbers(s_min, s_max, t_min, t_max, value):
    return round(
        ((t_max - t_min) * max(min(value, s_max), s_min) + (t_min * s_max) - (s_min * t_max)) / (s_max - s_min)
    )


def _15db_range(value):
    return _map_numbers(-15.0, 15.0, 0.0, 300.0, value)


class Channel(IntEnum):
    SETUP = 0x00
    """Setup channel is used for internal purpose"""

    INPUT_A = 0x01
    INPUT_B = 0x02
    INPUT_C = 0x03
    INPUT_SUM = 0x04

    OUTPUT_1 = 0x05
    OUTPUT_2 = 0x06
    OUTPUT_3 = 0x07
    OUTPUT_4 = 0x08
    OUTPUT_5 = 0x09
    OUTPUT_6 = 0x0A


class InputChannel:
    """
    Class representing a device channel object
    """

    def __init__(self, channel: Channel, device):
        self.channel = channel
        self._device = device

    def set_gain(self, value: float):
        """
        Set gain of channel
        :param value: gain in dB from -15 up to 15, 0.1 step
        """
        return self._invoke(0x02, _15db_range(value))

    def mute(self, value=True):
        """
        Mute or unmute a channel
        :param value: True if channel should be muted, False otherwise
        """
        return self._invoke(0x03, int(value))

    def delay(self, value=True):
        """
        Enable or disable delay of channel
        :param value: True if delay should be enabled, False otherwise
        """
        self._invoke(0x04, int(value))

    def set_delay(self, value=True, channel=None):
        """
        Set the long delay of the channel. For output channels set_short_delay can be used for finer settings.
        :param value: delay in meters [0, 200], step: 0.05m
        """
        # 0 ... 200m -> values 0 ... 4000 (= step of 5cm)
        self._invoke(0x05, _map_numbers(0.0, 200.0, 0.0, 4000.0))

    def send(self):
        """
        When in batch mode, this will send the previous commands
        :return: self
        """
        self._device.send()
        return self

    def _invoke(self, parameter, value):
        print(f"Channel OBJ: {parameter} - {value}")
        self._device._invoke(parameter, self.channel, value)


class OutputChannel(InputChannel):
    def set_source(self, channel: Channel):
        """
        Set source of the output channel
        :param channel: Channel A ... SUM
        """
        assert Channel.INPUT_A <= channel <= Channel.INPUT_SUM
        self._invoke(0x41, int(channel - Channel.INPUT_A))  # 0 ... 3 = A ... SUM

    def set_polarity(self, inverse=False):
        """
        Inverse polarity
        :param inverse: True if polarity should be inverted
        """
        self._invoke(0x49, int(inverse))

    def set_phase(self, phase):
        """
        Set phase of output in degree, input values are rounded
        :param phase: phase in deg 0 ... 180 (step 5 deg)
        :return:
        """
        self._invoke(0x4A, _map_numbers(0, 180, 0, 36))  # 0 ... 36

    def set_short_delay(self, value=True):
        """
        Set the short delay of an output channel.
        :param value: delay in millimeters [0, 4000], step: 2mm
        """
        self._invoke(0x4B, _map_numbers(0.0, 4000.0, 0.0, 2000.0))
