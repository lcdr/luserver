import logging
from typing import cast, Container

from event_dispatcher import EventDispatcher

from bitstream import c_uint, c_ushort
from pyraknet.messages import Message
from pyraknet.transports.abc import Connection, ConnectionEvent

from .messages import MSG_TO_ENUM, GameMessage, MessageType, WorldServerMsg, WorldClientMsg

log = logging.getLogger(__name__)

class PacketLogger:
	def __init__(self, dispatcher: EventDispatcher, excluded_packets: Container[str]=None):
		if excluded_packets is None:
			self._excluded_packets = set()
		else:
			self._excluded_packets = excluded_packets
		dispatcher.add_listener(ConnectionEvent.Receive, self._on_receive_packet)
		dispatcher.add_listener(ConnectionEvent.Send, self._on_send_packet)

	def _on_receive_packet(self, data: bytes, conn: Connection) -> None:
		if data[0] == Message.UserPacket.value:
			self._log_packet(data, True)

	def _on_send_packet(self, data: bytes, conn: Connection) -> None:
		if data[0] == Message.UserPacket.value:
			self._log_packet(data, False)

	def _packetname(self, data: bytes) -> str:
		from .modules.mail import MailID
		header = data[1]
		subheader = data[3]
		if header == MessageType.WorldServer.value and subheader == WorldServerMsg.Routing:
			header = data[13]
			subheader = data[15]
		if (header, subheader) == (MessageType.WorldServer.value, WorldServerMsg.GameMessage.value) or (header, subheader) == (MessageType.WorldClient.value, WorldClientMsg.GameMessage.value):
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

		if packetname not in self._excluded_packets:
			if received:
				log.debug("got %s", packetname)
			else:
				log.debug("snd %s", packetname)
