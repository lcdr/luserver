import asyncio
import os

import pyraknet.server
from .bitstream import BitStream, c_uint, c_ushort
from .messages import msg_enum, AuthServerMsg, GameMessage, GeneralMsg, Message, SocialMsg, WorldClientMsg, WorldServerMsg
from .modules.mail import MailID

class Server(pyraknet.server.Server):
	NETWORK_VERSION = 171022
	SERVER_PASSWORD = b"3.25 ND1"
	EXPECTED_PEER_TYPE = WorldClientMsg.__int__()

	def __init__(self, address, max_connections, db_conn):
		super().__init__(address, max_connections, self.SERVER_PASSWORD)
		self.not_console_logged_packets.add("ReplicaManagerSerialize")
		self.not_console_logged_packets.add("PositionUpdate")
		self.not_console_logged_packets.add("GameMessage/ReadyForUpdates")

		self.conn = db_conn
		self.db = self.conn.root
		self.register_handler(GeneralMsg.Handshake, self.on_handshake)

	def packetname(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.__int__() and data[3] == WorldServerMsg.Routing:
				data = b"\x53"+data[12:]
			if (data[1], data[3]) == (WorldServerMsg.__int__(), WorldServerMsg.GameMessage) or (data[1], data[3]) == (WorldClientMsg.__int__(), WorldClientMsg.GameMessage):
				message_name = GameMessage(c_ushort.unpack(data[16:18])[0]).name
				return "GameMessage/" + message_name
			if (data[1], data[3]) == (WorldServerMsg.__int__(), WorldServerMsg.Mail) or (data[1], data[3]) == (WorldClientMsg.__int__(), WorldClientMsg.Mail):
				packetname = MailID(c_uint.unpack(data[8:12])[0]).name
				return "Mail/" + packetname
			return msg_enum[data[1]](data[3]).name
		return super().packetname(data)

	def unknown_packetname(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.__int__() and data[3] == WorldServerMsg.Routing:
				data = b"\x53"+data[12:]
			if (data[1], data[3]) == (WorldServerMsg.__int__(), WorldServerMsg.GameMessage) or (data[1], data[3]) == (WorldClientMsg.__int__(), WorldClientMsg.GameMessage):
				return "GameMessage/%i" % c_ushort.unpack(data[16:18])[0]
			return msg_enum[data[1]].__name__ + "/%.2x" % data[3]
		return super().unknown_packetname(data)

	def packet_id(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.__int__() and data[3] == WorldServerMsg.Routing:
				return data[12], data[14]
			return data[1], data[3]
		return super().packet_id(data)

	def handler_data(self, data):
		if data[0] == Message.LUPacket:
			if data[1] == WorldServerMsg.__int__() and data[3] == WorldServerMsg.Routing:
				return data[19:]
			return data[8:]
		return super().handler_data(data)

	def register_handler(self, packet_id, callback, origin=None):
		if isinstance(packet_id, (GeneralMsg, AuthServerMsg, SocialMsg, WorldServerMsg, WorldClientMsg)):
			header = type(packet_id).__int__()
			subheader = packet_id
			packet_id = header, subheader
		return super().register_handler(packet_id, callback, origin)

	def send_handshake(self, address):
		out = BitStream()
		out.write_header(GeneralMsg.Handshake)
		out.write(c_uint(self.NETWORK_VERSION))
		out.write(bytes(4))
		out.write(c_uint(self.PEER_TYPE))
		self.send(out, address)

	def on_handshake(self, handshake, address):
		remote_network_version = handshake.read(c_uint)
		handshake.skip_read(4)
		remote_peer_type = handshake.read(c_uint)

		try:
			if remote_network_version != self.NETWORK_VERSION:
				raise ValueError("Unexpected network version %i!" % remote_network_version)
			if remote_peer_type != self.EXPECTED_PEER_TYPE:
				raise ValueError("Unexpected peer type %i!" % remote_peer_type)
		except ValueError:
			import traceback
			traceback.print_exc()
			self.close_connection(address)
		else:
			self.send_handshake(address)

	def close_connection(self, address, reason=None):
		if reason is not None:
			disconnect_message = BitStream()
			disconnect_message.write_header(GeneralMsg.DisconnectNotify)
			disconnect_message.write(c_uint(reason))
			self.send(disconnect_message, address)

		super().close_connection(address)

	def conn_sync(self):
		self.conn.sync()

	async def address_for_world(self, world_id):
		while True:
			self.conn_sync()
			for server_address, server_world in self.db.servers.items():
				if server_world == world_id and (not hasattr(self, "external_address") or server_address != self.external_address):
					return server_address
			# no server found, spawn a new one
			# todo: os.system probably isn't the best way to do this
			os.system("start python __main__.py %i %i" % (world_id[0], world_id[2]))
			await asyncio.sleep(4)

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
