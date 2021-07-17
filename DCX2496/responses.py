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
    def __init__(self, data):
        assert len(data) == 25
        super().__init__(data)
        index = 8
        for channel in ["a", "b", "c", "1", "2", "3", "4", "5", "6"]:
            setattr(
                self,
                "channel_" + channel,
                {"level": _clear_bit(self.data[index], 5), "limited": _is_bit(self.data[index], 5)},
            )
            index += 1
