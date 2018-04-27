import __main__
import logging
import os
import struct
import time
from typing import cast, Iterable, Set, SupportsBytes, Union

import pyraknet.server
from pyraknet.messages import Address, Message
from .messages import MSG_TO_ENUM, GameMessage, MessageType, WorldClientMsg, WorldServerMsg

log = logging.getLogger(__name__)

c_uint = struct.Struct("<I")
c_ushort = struct.Struct("<H")

class Server:
	SERVER_PASSWORD = b"3.25 ND1"

	def __init__(self, address: Address, max_connections: int):
		self._server = pyraknet.server.Server(address, max_connections, Server.SERVER_PASSWORD)
		self.not_console_logged_packets: Set[str] = set()
		self.file_logged_packets: Set[str] = set()

	def _on_lu_packet(self, data: bytes, address: Address) -> None:
		self._log_packet(data, received=True)

	def _packetname(self, data: bytes) -> str:
		from .modules.mail import MailID
		header = data[1]
		subheader = data[3]
		if header == MessageType.WorldServer.value and subheader == WorldServerMsg.Routing:
			header = data[13]
			subheader = data[15]
		if (header, subheader) == (MessageType.WorldServer.value, WorldServerMsg.GameMessage) or (header, subheader) == (MessageType.WorldClient.value, WorldClientMsg.GameMessage):
			message_id = cast(int, c_ushort.unpack(data[16:18])[0])
			try:
				message_name = GameMessage(message_id).name
			except ValueError:
				message_name = str(message_id)
			return "GameMessage/" + message_name
		if (header, subheader) == (MessageType.WorldServer.value, WorldServerMsg.Mail) or (header, subheader) == (MessageType.WorldClient.value, WorldClientMsg.Mail):
			mail_id = cast(int, c_uint.unpack(data[8:12])[0])
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
