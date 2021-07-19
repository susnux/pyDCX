import argparse
import re
import select
import socket
from os import path, remove
from configparser import ConfigParser

from DCX2496.connector import SerialConnector


class DCXDaemon:
    server: socket.socket = None
    connections = {}

    def __init__(self, serial_port, host, port):
        self.connector = SerialConnector(serial_port)
        match = re.match(r"unix://(.+)", host)
        if match:
            addresses = [(socket.AF_UNIX, socket.SOCK_STREAM, 0, "", match.group())]
            if path.exists(match.group()):
                remove(match.group())
        else:
            addresses = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        for res in addresses:
            af, socktype, proto, _, sa = res
            try:
                self.server = socket.socket(af, socktype, proto)
            except OSError:
                self.server = None
                continue
            try:
                self.server.bind(sa)
                self.server.listen()
            except OSError:
                self.server.close()
                self.server = None
                continue
            break
        if self.server is None:
            self.connector.close()
            print(f"Could not open socket on {host}")
            exit(1)
        self.connections = {self.server: tuple()}

    def run(self):
        while True:
            readable, writeable, _ = select.select(self.connections.keys(), self.connections.keys(), [], 60)
            for sock in readable:
                if sock is self.server:
                    conn, _ = sock.accept()
                    self.connections[conn] = (bytearray(), bytearray())
                else:
                    self.read_client(sock)
            for sock in writeable:
                try:
                    self.write_client(sock)
                except:
                    sock.close()
                    del self.connections[sock]

    def read_client(self, sock):
        data = sock.recv(1024)
        if not data:
            del self.connections[sock]
            sock.close()
        else:
            self.connections[sock][0].extend(data)
            if len(self.connections[sock][0]) >= 8 and self.connections[sock][0][-1] == 0xF7:
                print(self.connections[sock][0])
                resp = self.connector.handle_command(self.connections[sock][0])
                self.connections[sock][1].extend(resp.data if resp else b"\xF7")
                self.connections[sock][0].clear()

    def write_client(self, sock):
        if self.connections[sock][1]:
            sock.sendall(self.connections[sock][1])
            self.connections[sock][1].clear()


def run_daemon():
    # Parse config flag
    conf_parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False
    )
    conf_parser.add_argument("-c", "--config", help="Specify configuration file", metavar="FILE")
    args, remaining_argv = conf_parser.parse_known_args()
    # Our own defaults
    defaults = {"port": 4444, "host": "localhost"}
    # Override defaults with config file
    if args.config:
        config = ConfigParser.SafeConfigParser()
        config.read([args.config])
        defaults.update(dict(config.items("Defaults")))
    # Parse rest of options and override config file with them
    parser = argparse.ArgumentParser(
        # Inherit options from config_parser
        parents=[conf_parser]
    )
    parser.set_defaults(**defaults)
    parser.add_argument("-p", "--port", help="Specify port to listen", type=int)
    parser.add_argument("-l", "--host", help="Specify host to listen", type=str)
    parser.add_argument("-s", "--serial", help="Serial port to use", type=str, required=True)
    args = parser.parse_args(remaining_argv)

    server = DCXDaemon(args.serial, args.host, args.port)
    server.run()
