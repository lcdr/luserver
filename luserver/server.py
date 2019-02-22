import __main__
import logging
import os
import struct
import time
from ssl import SSLContext
from typing import Container, Optional, SupportsBytes

from event_dispatcher import EventDispatcher

import pyraknet.server
from bitstream import c_ubyte, c_ushort, ReadStream
from pyraknet.messages import Address, Message
from pyraknet.transports.abc import Connection, ConnectionEvent, Reliability

from .logger import PacketLogger
from .messages import MSG_TO_ENUM, MessageType, WorldServerMsg

log = logging.getLogger(__name__)

class Server:
	SERVER_PASSWORD = b"3.25 ND1"

	def __init__(self, address: Address, max_connections: int, ssl: Optional[SSLContext], excluded_packets=None):
		self._dispatcher = EventDispatcher()
		self._server = pyraknet.server.Server(address, max_connections, Server.SERVER_PASSWORD, ssl, self._dispatcher, excluded_packets={Message.InternalPing, Message.ConnectedPong, Message.ReplicaManagerSerialize, Message.UserPacket})
		self._logger = PacketLogger(self._dispatcher, excluded_packets)
		self._dispatcher.add_listener(Message.UserPacket, self._on_lu_packet)

	def _on_lu_packet(self, data: bytes, conn: Connection) -> None:
		header = c_ushort._struct.unpack(data[:2])[0]
		subheader = data[2]
		if header == MessageType.WorldServer.value and subheader == WorldServerMsg.Routing:
			print("todo")
			"""stream.skip_read(4)
			header = stream.read(c_ushort)
			subheader = stream.read(c_ubyte)
			stream.skip_read(4)"""
		try:
			enum = MSG_TO_ENUM[header](subheader)
		except ValueError:
			return
		self._dispatcher.dispatch_callable(enum, lambda: ((ReadStream(data[7:]), conn), {}))

	def broadcast(self, data: SupportsBytes, reliability: Reliability=Reliability.ReliableOrdered, exclude: Container["Connection"]=()) -> None:
		data = bytes(data)
		self._dispatcher.dispatch(ConnectionEvent.Broadcast, data, reliability, exclude)
