import __main__
import logging
import os
import time

import pyraknet.server
from .bitstream import c_uint, c_ushort
from .messages import msg_enum, GameMessage, WorldClientMsg, WorldServerMsg

log = logging.getLogger(__name__)

class Server:
	SERVER_PASSWORD = b"3.25 ND1"

	def __init__(self, address, max_connections):
		self._server = pyraknet.server.Server(address, max_connections, Server.SERVER_PASSWORD)
		self.not_console_logged_packets = set()
		self.file_logged_packets = set()
		self._server.add_handler("user_packet", self._on_lu_packet)

	def _on_lu_packet(self, data, address):
		self._log_packet(data, received=True)

	def _packetname(self, data):
		from .modules.mail import MailID
		if data[1] == WorldServerMsg.header() and data[3] == WorldServerMsg.Routing:
			data = b"\x53"+data[12:]
		if (data[1], data[3]) == (WorldServerMsg.header(), WorldServerMsg.GameMessage) or (data[1], data[3]) == (WorldClientMsg.header(), WorldClientMsg.GameMessage):
			message_name = GameMessage(c_ushort.unpack(data[16:18])[0]).name
			return "GameMessage/" + message_name
		if (data[1], data[3]) == (WorldServerMsg.header(), WorldServerMsg.Mail) or (data[1], data[3]) == (WorldClientMsg.header(), WorldClientMsg.Mail):
			packetname = MailID(c_uint.unpack(data[8:12])[0]).name
			return "Mail/" + packetname
		return msg_enum[data[1]](data[3]).name

	def _unknown_packetname(self, data):
		if data[1] == WorldServerMsg.header() and data[3] == WorldServerMsg.Routing:
			data = b"\x53"+data[12:]
		if (data[1], data[3]) == (WorldServerMsg.header(), WorldServerMsg.GameMessage) or (data[1], data[3]) == (WorldClientMsg.header(), WorldClientMsg.GameMessage):
			return "GameMessage/%i" % c_ushort.unpack(data[16:18])[0]
		return msg_enum[data[1]].__name__ + "/%.2x" % data[3]

	def _log_packet(self, data, received):
		try:
			packetname = self._packetname(data)
			console_log = packetname not in self.not_console_logged_packets
		except ValueError:
			packetname = self._unknown_packetname(data)
			console_log = True

		if packetname in self.file_logged_packets:
			with open(os.path.normpath(os.path.join(__main__.__file__, "..", "logs", packetname+str(time.time())+".bin")), "wb") as file:
				file.write(bytes(data))

		if console_log:
			if received:
				log.debug("got %s", packetname)
			else:
				log.debug("snd %s", packetname)

	def send(self, data, address=None, broadcast=False):
		self._log_packet(data, received=False)
		self._server.send(data, address, broadcast)
