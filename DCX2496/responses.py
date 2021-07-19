from DCX2496 import Channel


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
    ...


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
