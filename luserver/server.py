import __main__
import logging
import os
import struct
import time
from typing import Callable, cast, Iterable, Set, SupportsBytes, Union

import pyraknet.server
from pyraknet.bitstream import c_ubyte, c_uint, c_ushort, ReadStream
from pyraknet.messages import Address, Message
from pyraknet.server import Event
from .messages import ENUM_TO_MSG, MSG_TO_ENUM, GameMessage, LUMessage, MessageType, WorldClientMsg, WorldServerMsg

log = logging.getLogger(__name__)

class Server:
	SERVER_PASSWORD = b"3.25 ND1"

	def __init__(self, address: Address, max_connections: int):
		self._server = pyraknet.server.Server(address, max_connections, Server.SERVER_PASSWORD)
		self.not_console_logged_packets: Set[str] = set()
		self.file_logged_packets: Set[str] = set()
		self._packet_handlers: Dict[Tuple[int, int], List[Callable[..., None]]] = {}
		self._server.add_handler(Event.UserPacket, self._on_lu_packet)

	def _on_lu_packet(self, data: bytes, address: Address) -> None:
		self._log_packet(data, received=True)
		stream = ReadStream(data, unlocked=True)
		stream.skip_read(1)
		header = stream.read(c_ushort)
		subheader = stream.read(c_ubyte)
		stream.skip_read(4)
		if header == MessageType.WorldServer.value and subheader == WorldServerMsg.Routing:
			stream.skip_read(4)
			header = stream.read(c_ushort)
			subheader = stream.read(c_ubyte)
			stream.skip_read(4)
		read_offset = stream.read_offset
		if (header, subheader) in self._packet_handlers:
			for handler in self._packet_handlers[(header, subheader)]:
				stream.read_offset = read_offset
				handler(stream, address)

	def register_handler(self, packet_id: LUMessage, handler: Callable[[ReadStream, Address], None]) -> None:
		header = ENUM_TO_MSG[type(packet_id)]
		subheader = packet_id
		self._packet_handlers.setdefault((header, subheader), []).append(handler)

	def _packetname(self, data: bytes) -> str:
		from .modules.mail import MailID
		header = data[1]
		subheader = data[3]
		if header == MessageType.WorldServer.value and subheader == WorldServerMsg.Routing:
			header = data[13]
			subheader = data[15]
		if (header, subheader) == (MessageType.WorldServer.value, WorldServerMsg.GameMessage) or (header, subheader) == (MessageType.WorldClient.value, WorldClientMsg.GameMessage):
			message_id = cast(int, c_ushort._struct.unpack(data[16:18])[0])
			try:
				message_name = GameMessage(message_id).name
			except ValueError:
				message_name = str(message_id)
			return "GameMessage/" + message_name
		if (header, subheader) == (MessageType.WorldServer.value, WorldServerMsg.Mail) or (header, subheader) == (MessageType.WorldClient.value, WorldClientMsg.Mail):
			mail_id = cast(int, c_uint._struct.unpack(data[8:12])[0])
			try:
				packetname = MailID(mail_id).name
			except ValueError:
				packetname = str(mail_id)
			return "Mail/" + packetname
		try:
			return MSG_TO_ENUM[header](subheader).name
		except ValueError:
			return MSG_TO_ENUM[header].__name__ + "/%.2x" % subheader

	def _log_packet(self, data: bytes, received: bool) -> None:
		packetname = self._packetname(data)
		console_log = packetname not in self.not_console_logged_packets

		if packetname in self.file_logged_packets:
			with open(os.path.normpath(os.path.join(__main__.__file__, "..", "logs", packetname+str(time.time())+".bin")), "wb") as file:
				file.write(data)

		if console_log:
			if received:
				log.debug("got %s", packetname)
			else:
				log.debug("snd %s", packetname)

	def send(self, data: Union[bytes, SupportsBytes], recipients: Union[Address, Iterable[Address]]=None, broadcast: bool=False) -> None:
		data = bytes(data)
		if data[0] == Message.UserPacket:
			self._log_packet(data, received=False)
		self._server.send(data, recipients, broadcast)
