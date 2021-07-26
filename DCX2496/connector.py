import socket
import serial
import re

from .constants import FunctionBytes, FUNCTION_BYTE
from .exceptions import DCXSerialException, DCXConnectorException
from .logger import logger
from .responses import SearchResponse, PingResponse, DumpResponse, Response


class Connector:
    HAVE_RESPONSE = [FunctionBytes.SEARCH, FunctionBytes.PING, FunctionBytes.DUMP]

    def handle_command(self, command):
        """
        Handle sending commands to DCX and receiving responses
        :param command: DCX command bytes
        :return: Response|None - Response if available else None
        """
        self.write_command(command)
        return self.get_response() if command[FUNCTION_BYTE] in self.HAVE_RESPONSE else None

    def write_command(self, command):
        pass

    def read_response(self):
        pass

    def close(self):
        pass

    def get_response(self):
        data = self.read_response()
        response_type = {0x00: SearchResponse, 0x04: PingResponse, 0x10: DumpResponse}
        return response_type.get(data[FUNCTION_BYTE], Response)(data)


class DaemonConnector(Connector):
    """
    Connect to daemon process handling the serial connection

    If there are multiple client applications using one DCX device,
    a daemon process can be used which multiplexes the requests.
    """

    sock: socket.socket = None

    def __init__(self, connection: str):
        """
        Create Daemon Connector
            Example for connection strings are (default port is 4444):
            - Unix socket: `unix:///some/path/socket`
            - IPv4 `192.168.0.1:1234`
            - IPv6 `[::1]:1234`
            - Hostname `localhost:1234`
        :param connection: String defining the interface
        """
        unix = re.compile(r"unix://(.+)")
        host_port = re.compile(r":(\d\d+)$")

        match = unix.match(connection)
        if match:
            logger.debug(f"Daemon connector on UNIX socket {match.group()}")
            addresses = [(socket.AF_UNIX, socket.SOCK_STREAM, 0, "", match.group())]
        else:
            port = host_port.search(connection)
            if port:
                port = port.groups()[0]
                connection = connection[: -(len(port) + 1)]
            else:
                port = 4444
            print(f"Daemon connector on TCP socket {connection} port {port}")
            logger.debug(f"Daemon connector on TCP socket {connection} port {port}")
            addresses = socket.getaddrinfo(connection, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if not addresses:
                raise DCXConnectorException

        for res in addresses:
            af, socktype, proto, _, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
            except socket.error as msg:
                self.sock = None
                continue
            try:
                self.sock.connect(sa)
            except socket.error as msg:
                self.sock.close()
                self.sock = None
                continue
            break
        if self.sock is None:
            logger.error("Could not open socket for daemon communication")
            raise DCXSerialException("Could not open socket for daemon communication")

    def close(self):
        self.sock.close()

    def write_command(self, command: bytearray):
        try:
            self.sock.sendall(command)
        except:  # For convenience we only provide one type of exception
            raise DCXSerialException()

    def read_response(self):
        EOL = b"\xF7"
        data = bytearray()
        while True:
            buf = self.sock.recv(256)
            if buf:
                data.extend(buf)
                if EOL in buf:
                    break
        return data


class SerialConnector(Connector):
    """
    Helper for serial data communication
    """

    def __init__(self, serial_port):
        self.serial = serial.Serial(serial_port, baudrate=38400)

    def write_command(self, command):
        written = self.serial.write(command)
        if written != len(command):
            raise DCXSerialException()

    def read_response(self):
        EOL = b"\xF7"
        data = bytearray()
        while True:
            c = self.serial.read(1)
            if c:
                data += c
                if data[-1:] == EOL:
                    break
            else:
                break
        return data
