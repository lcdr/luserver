
class DisconnectReason:
	UnknownServerError = 0
	DuplicateLogin = 4
	ServerShutdown = 5
	UnableToLoadMap = 6
	InvalidSessionKey = 7
	AccountNotInPendingList = 8 # Whatever that means
	CharacterNotFound = 9
	CharacterCorruption = 10
	Kick = 11
	FreeTrialExpired = 13
	PlayScheduleTimeDone = 14

class NotifyReason:
	DuplicateDisconnected = 0

import __main__
import asyncio
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from typing import Callable

from .bitstream import c_ubyte, c_uint, c_ushort, ReadStream, WriteStream
from .messages import Address, GeneralMsg, WorldClientMsg, WorldServerMsg
from .server import Server as _Server

log = logging.getLogger(__name__)

class Server(_Server, ABC):
	_NETWORK_VERSION = 171022
	_EXPECTED_PEER_TYPE = WorldClientMsg.header()

	def __init__(self, address, max_connections, db_conn):
		super().__init__(address, max_connections)
		self.conn = db_conn
		self.db = self.conn.root
		self._packet_handlers = {}
		self.register_handler(GeneralMsg.Handshake, self._on_handshake)

	def _on_lu_packet(self, data: ReadStream, address: Address):
		super()._on_lu_packet(data, address)
		header = data.read(c_ushort)
		subheader = data.read(c_ubyte)
		data.skip_read(4)
		if header == WorldServerMsg.header() and subheader == WorldServerMsg.Routing:
			data.skip_read(4)
			header = data.read(c_ushort)
			subheader = data.read(c_ubyte)
			data.skip_read(4)
		read_offset = data.read_offset
		if (header, subheader) in self._packet_handlers:
			for handler in self._packet_handlers[(header, subheader)]:
				data.read_offset = read_offset
				if asyncio.iscoroutinefunction(handler):
					asyncio.ensure_future(handler(data, address))
				else:
					handler(data, address)

	def register_handler(self, packet_id, handler: Callable[[ReadStream, Address], None]) -> None:
		header = packet_id.header()
		subheader = packet_id
		packet_id = header, subheader
		self._packet_handlers.setdefault((header, subheader), []).append(handler)

	@abstractmethod
	def peer_type(self) -> int:
		pass

	def _send_handshake(self, address):
		out = WriteStream()
		out.write_header(GeneralMsg.Handshake)
		out.write(c_uint(self._NETWORK_VERSION))
		out.write(bytes(4))
		out.write(c_uint(self.peer_type()))
		self.send(out, address)

	def _on_handshake(self, handshake, address):
		remote_network_version = handshake.read(c_uint)
		handshake.skip_read(4)
		remote_peer_type = handshake.read(c_uint)

		try:
			if remote_network_version != self._NETWORK_VERSION:
				raise ValueError("Unexpected network version %i!" % remote_network_version)
			if remote_peer_type != self._EXPECTED_PEER_TYPE:
				raise ValueError("Unexpected peer type %i!" % remote_peer_type)
		except ValueError:
			import traceback
			traceback.print_exc()
			self.close_connection(address)
		else:
			self._send_handshake(address)

	def close_connection(self, address: Address, reason=None) -> None:
		if reason is not None:
			disconnect_message = WriteStream()
			disconnect_message.write_header(GeneralMsg.DisconnectNotify)
			disconnect_message.write(c_uint(reason))
			self.send(disconnect_message, address)

		self._server.close_connection(address)

	async def address_for_world(self, world_id, include_self=False) -> Address:
		first = True
		servers = {}
		while True:
			self.conn.sync()
			if world_id[0] % 100 == 0 or not first:
				for server_address, server_world in self.db.servers.items():
					if server_world == world_id and (world_id[0] % 100 == 0 or server_address not in servers):
						if not include_self and hasattr(self, "external_address") and server_address == self.external_address:
							continue
						return server_address
			# no server found, spawn a new one
			servers = dict(self.db.servers)
			command = "\"%s\" %i %i" % (__main__.__file__, world_id[0], world_id[2])
			if os.name == "nt":
				subprocess.Popen("cmd /K \"python "+command+" && exit || pause && exit\"", creationflags=subprocess.CREATE_NEW_CONSOLE)
			else:
				subprocess.Popen("python3 "+command, shell=True)
			if first:
				await asyncio.sleep(8)
				first = False
			else:
				await asyncio.sleep(30)
