from __future__ import annotations
from .channel import Channel


def _is_bit(byte, bit):
    return bool(byte & (1 << bit))


def _clear_bit(byte, bit):
    return byte & ~(1 << bit)


class Response:
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return str(self.data)


class DumpResponse(Response):
    ...


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
