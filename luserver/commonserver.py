
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
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from ZODB.Connection import Connection

from pyraknet.bitstream import c_ubyte, c_uint, c_ushort, ReadStream
from pyraknet.messages import Address
from pyraknet.server import Event
from .auth import Account
from .bitstream import WriteStream
if TYPE_CHECKING:
	from .game_object import ObjectID, GameObject
	from .components.behaviors import Behavior
from .messages import ENUM_TO_MSG, GeneralMsg, LUMessage, MessageType, WorldServerMsg
from .server import Server as _Server
from .math.vector import Vector3
from .math.quaternion import Quaternion

LootTableEntry = Sequence[Tuple[int, bool, int]]
MissionData = Tuple[Tuple[int, int, bool, Sequence[Sequence[Sequence[int]]], Optional[int], int, int, int], Tuple[Tuple[Tuple[int, ...], ...], ...], Sequence[Tuple[int, int, int, str]], bool, bool, Sequence[int]]

class WorldData:
	def __init__(self, objects: "Dict[ObjectID, GameObject]", paths: Dict[str, Tuple[int, Sequence]], spawnpoint: Tuple[Vector3, Quaternion]):
		self.objects = objects
		self.paths = paths
		self.spawnpoint = spawnpoint

class ServerDB:
	accounts: Dict[str, Account]
	activities: Dict[int, Tuple[int]]
	activity_rewards: Dict[int, Sequence[Tuple[int, Tuple[Optional[int], Optional[int], Optional[int]]]]]
	behavior: Dict[int, Any]
	config: Dict[str, object]
	colors: Dict[int, bool]
	components_registry: Dict[int, Sequence[Tuple[int, int]]]
	current_clone_id: int
	current_instance_id: int
	destructible_component: Dict[int, Tuple[int, Tuple[Optional[int], Optional[int], Optional[int]], int, Optional[int], int, bool]]
	inventory_component: Dict[int, Sequence[Tuple[int, bool]]]
	item_component: Dict[int, Tuple[int, int, int, Sequence[int]]]
	item_sets: List[Tuple[Sequence[int], Sequence[int], Sequence[int], Sequence[int], Sequence[int], Sequence[int]]]
	factions: Dict[int, Sequence[int]]
	launchpad_component: Dict[int, Tuple[int, int, str]]
	level_rewards: Dict[int, Sequence[Tuple[int, int]]]
	level_scores: Sequence[int]
	loot_table: Dict[int, LootTableEntry]
	mission_mail: Dict[int, Sequence[Tuple[int, Optional[int]]]]
	mission_npc_component: Dict[int, Sequence[Tuple[int, bool, bool]]]
	missions: Dict[int, MissionData]
	predef_names: Tuple[Sequence[str], Sequence[str], Sequence[str]]
	object_skills: Dict[int, Sequence[Tuple[int, int]]]
	package_component: Dict[int, LootTableEntry]
	property_template: Sequence[Tuple[float, float, float]]
	properties: Dict[int, Dict[int, Dict[int, Tuple[int, Vector3, Quaternion]]]]
	rebuild_component: Dict[int, Tuple[float, float, float, int, int]]
	script_component: Dict[int, str]
	servers: Dict[Address, Tuple[int, int, int]]
	skill_behavior: Dict[int, Tuple["Behavior", int]]
	vendor_component: Dict[int, LootTableEntry]
	world_data: Dict[int, WorldData]
	world_info: Dict[int, Tuple[str, int]]

log = logging.getLogger(__name__)

class Server(_Server, ABC):
	_NETWORK_VERSION = 171022
	_EXPECTED_PEER_TYPE = MessageType.WorldClient.value

	@property
	@abstractmethod
	def _PEER_TYPE(self) -> int:
		pass

	def __init__(self, address: Address, max_connections: int, db_conn: Connection):
		super().__init__(address, max_connections)
		self.conn = db_conn
		self.db: ServerDB = self.conn.root
		self._packet_handlers: Dict[Tuple[int, int], List[Callable[..., None]]] = {}
		self._server.add_handler(Event.UserPacket, self._on_lu_packet)
		self.register_handler(GeneralMsg.Handshake, self._on_handshake)

	def _on_lu_packet(self, data: bytes, address: Address) -> None:
		super()._on_lu_packet(data, address)
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

	def _send_handshake(self, address: Address) -> None:
		out = WriteStream()
		out.write_header(GeneralMsg.Handshake)
		out.write(c_uint(self._NETWORK_VERSION))
		out.write(bytes(4))
		out.write(c_uint(self._PEER_TYPE))
		self.send(out, address)

	def _on_handshake(self, handshake: ReadStream, address: Address) -> None:
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

	def close_connection(self, address: Address, reason: int=None) -> None:
		if reason is not None:
			disconnect_message = WriteStream()
			disconnect_message.write_header(GeneralMsg.DisconnectNotify)
			disconnect_message.write(c_uint(reason))
			self.send(disconnect_message, address)

		self._server.close_connection(address)

	async def address_for_world(self, world_id: Tuple[int, int, int], include_self: bool=False) -> Address:
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
