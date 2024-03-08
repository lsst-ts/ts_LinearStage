# This file is part of ts_linearstage.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["MockSerial", "MockLST"]

import inspect
import logging
import queue

import serial
from lsst.ts import tcpip


class LinearStageServer(tcpip.OneClientReadLoopServer):
    def __init__(self, *, port: int | None, log: logging.Logger) -> None:
        super().__init__(
            port=port, host=tcpip.LOCAL_HOST, log=log, name="Zaber Mock Server"
        )
        self.device = MockLST()

    async def read_and_dispatch(self) -> None:
        command = await self.read_str()
        self.log.info(f"{command=} received.")
        reply = self.device.parse_message(command)
        await self.write_str(reply)


class MockSerial:
    """Implements mock serial.

    Parameters
    ----------
    port : `str`
    baudrate : `int`
    bytesize : `int`
    parity
    stopbits
    timeout : `None` or `float`
    xonxoff : `bool`
    rtscts : `bool`
    write_timeout : `None` or `float`
    dsrdtr : `bool`
    inter_byte_timeout : `None` or `float`
    exclusive : `None`

    Attributes
    ----------
    log : `logging.Logger`
    name : `str`
    baudrate : `int`
    bytesize : `int`
    parity
    stopbits
    timeout : `None` or `float`
    xonxoff : `bool`
    rtscts : `bool`
    write_timeout : `None` or `float`
    dsrdts : `bool`
    inter_byte_timeout : `None` or `float`
    exclusive : `bool`
    opened : `bool`
    device : `MockLST`
    message_queue : `queue.Queue`
    """

    def __init__(
        self,
        port,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=None,
        xonxoff=False,
        rtscts=False,
        write_timeout=None,
        dsrdtr=False,
        inter_byte_timeout=None,
        exclusive=None,
    ):
        self.log = logging.getLogger(__name__)
        self.name = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.write_timeout = write_timeout
        self.dsrdtr = dsrdtr
        self.inter_byte_timeout = inter_byte_timeout
        self.exclusive = exclusive
        self.opened = False

        self.device = MockLST()
        self.message_queue = queue.Queue()

        self.log.info("MockSerial created")

    def readline(self, size=-1):
        """Read the line.

        Parameters
        ----------
        size : `int`, optional
            The size of the line.

        Returns
        -------
        msg : `bytes`
            The message from the queue.
        """
        self.log.info("Reading from queue")
        msg = self.message_queue.get()
        self.log.info(msg.encode())
        return msg.encode()

    def write(self, data):
        """Write the data.

        Parameters
        ----------
        data : `bytes`
            The command message.
        """
        self.log.info(data)
        msg = self.device.parse_message(data.decode())
        self.log.debug(msg)
        self.message_queue.put(msg)
        self.log.info("Putting into queue")

    def close(self):
        """Close the serial connection."""
        self.log.info("Closing serial connection")


class MockLST:
    """Implements mock LinearStage.

    Attributes
    ----------
    log : `logging.Logger`
    position : `int`
    status : `str`
    device_number : `int`

    """

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.position = 0
        self.status = "IDLE"
        self.device_number = 1
        self.log.info("MockLST created")

    def parse_message(self, msg):
        try:
            self.log.info(f"{msg=} received.")
            msg = msg.rstrip("\r\n").split(" ")
            msg[0].lstrip("/")
            msg[1]
            command = msg[2]
            parameters = msg[3:]
        except IndexError:
            reply = self.do_status()
            return reply
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if name == f"do_{command}":
                if parameters:
                    reply = func(*parameters)
                    return reply
                else:
                    reply = func()
                    return reply

        self.log.info(f"{command} not supported.")

    # def parse_message(self, msg):
    #     """Parse and return the result of the message.

    #     Parameters
    #     ----------
    #     msg : `bytes`
    #         The message to parse.

    #     Returns
    #     -------
    #     reply : `bytes`
    #         The reply of the command parsed.

    #     Raises
    #     ------
    #     NotImplementedError
    #         Raised when command is not implemented.
    #     """
    #     self.log.info(msg)
    #     msg = AsciiCommand(msg)
    #     self.log.info(msg)
    #     split_msg = msg.data.split(" ")
    #     self.log.debug(split_msg)
    #     if any(char.isdigit() for char in split_msg[-1]):
    #         parameter = split_msg[-1]
    #         command = split_msg[:-1]
    #     else:
    #         parameter = None
    #         command = split_msg
    #     self.log.debug(parameter)
    #     if command != []:
    #         command_name = "_".join(command)
    #     else:
    #         command_name = ""
    #     self.log.debug(command_name)
    #     methods = inspect.getmembers(self, inspect.ismethod)
    #     if command_name == "":
    #         return self.do_get_status()
    #     else:
    #         for name, func in methods:
    #             if name == f"do_{command_name}":
    #                 self.log.debug(name)
    #                 if parameter is None:
    #                     reply = func()
    #                 else:
    #                     reply = func(parameter)
    #                 self.log.debug(reply)
    #                 return reply
    #     raise NotImplementedError()

    def do_identify(self):
        return f"@{self.device_number} 0 OK {self.status} -- 0"

    def do_status(self):
        return f"@{self.device_number} 0 OK {self.status} -- 0"

    def do_get(self, field):
        """Return the position of the device.

        Returns
        -------
        str
            The formatted reply
        """
        match field:
            case "pos":
                return f"@{self.device_number} 0 OK {self.status} -- {self.position}"
            case "status":
                return f"@{self.device_number} 0 OK {self.status} -- 0"
            case "device.id":
                return f"@{self.device_number} 0 OK {self.status} -- 30342"
            case _:
                self.log.info(f"{field=} is not recognized.")

    def do_home(self):
        """Home the device.

        Returns
        -------
        str
            The formatted reply.
        """
        return f"@{self.device_number} 0 OK {self.status} -- 0"

    def do_move(self, mode, position):
        """Move the device using absolute position.

        Parameters
        ----------
        position : `int`

        Returns
        -------
        str
            The formatted reply
        """
        match mode:
            case "abs":
                self.position = int(position)
            case "rel":
                self.position += int(position)
            case _:
                self.log.info(f"{mode=} is not recognized.")
        return f"@{self.device_number} 0 OK {self.status} -- 0"
