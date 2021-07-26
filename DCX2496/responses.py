from __future__ import annotations
from .channel import Channel
from .constants import DCX_HEADER, TERMINATOR_BYTE


def _is_bit(byte, bit):
    return bool(byte & (1 << bit))


def _clear_bit(byte, bit):
    return byte & ~(1 << bit)


class Response:
    def __init__(self, data: bytearray):
        assert data.startswith(DCX_HEADER) and len(data) > 8 and data[-1] == TERMINATOR_BYTE
        self.data = data

    def __str__(self):
        return str(self.data)

    @property
    def payload(self):
        """
        Return the payload of the response, meaning the data without header and terminator
        :return: bytearray
        """
        return self.data[6:-1]


class DumpResponse(Response):
    LENGTH_PART0 = 1015
    LENGTH_PART1 = 911

    @property
    def payload(self):
        return self.part_0 + self.part_1

    @property
    def part_0(self):
        return self.data[6 : self.LENGTH_PART0 - 1] if len(self.data) >= self.LENGTH_PART0 else bytearray()

    @property
    def part_1(self):
        if len(self.data) > self.LENGTH_PART0:
            # Both parts are set
            return self.data[self.LENGTH_PART0 + 6 : -1]
        elif len(self.data) == self.LENGTH_PART1:
            # Only second part set
            return super().payload
        else:
            return bytearray()


class SearchResponse(Response):
    device_id: int = None
    """Device ID, do not mix up with the shown one on the device screen"""

    def __init__(self, data):
        assert len(data) == 26
        super().__init__(data)
        self.device_id = data[4]

    @property
    def shown_id(self):
        """
        Returns the displayed device ID (screen of the DCX device)
        :return: Displayed device ID
        """
        return self.device_id + 1


class PingResponse(Response):
    class _PingData:
        def __init__(self, data):
            self.limited = _is_bit(data, 5)
            self.level = _clear_bit(data, 5)

    channels: dict[Channel, _PingData] = {}

    def __init__(self, data):
        assert len(data) == 25
        super().__init__(data)
        start = 8
        for channel in range(Channel.INPUT_A, Channel.OUTPUT_6 + 1):
            self.channels[Channel(channel)] = self._PingData(self.data[start + channel])
