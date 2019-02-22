
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
from ssl import SSLContext
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from ZODB.Connection import Connection

from bitstream import c_ubyte, c_uint, c_ushort, ReadStream
from pyraknet.messages import Address
from pyraknet.transports.abc import Connection, ConnectionType
from .auth import Account
from .bitstream import WriteStream
if TYPE_CHECKING:
	from .game_object import ObjectID, GameObject
	from .components.behaviors import Behavior
from .messages import GeneralMsg, MessageType, WorldServerMsg
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

	def __init__(self, address: Address, max_connections: int, db_conn: Connection, ssl: Optional[SSLContext], excluded_packets=None):
		super().__init__(address, max_connections, ssl, excluded_packets)
		self.conn = db_conn
		self.db: ServerDB = self.conn.root
		self._dispatcher.add_listener(GeneralMsg.Handshake, self._on_handshake)

	def _send_handshake(self, conn: Connection) -> None:
		out = WriteStream()
		out.write_header(GeneralMsg.Handshake)
		out.write(c_uint(self._NETWORK_VERSION))
		out.write(bytes(4))
		out.write(c_uint(self._PEER_TYPE))
		conn.send(out)

	def _on_handshake(self, stream: ReadStream, conn: Connection) -> None:
		remote_network_version = stream.read(c_uint)
		stream.skip_read(4)
		remote_peer_type = stream.read(c_uint)

		try:
			if remote_network_version != self._NETWORK_VERSION:
				raise ValueError("Unexpected network version %i!" % remote_network_version)
			if remote_peer_type != self._EXPECTED_PEER_TYPE:
				raise ValueError("Unexpected peer type %i!" % remote_peer_type)
		except ValueError:
			import traceback
			traceback.print_exc()
			conn.close()
		else:
			self._send_handshake(conn)

	def close_connection(self, conn: Connection, reason: int=None) -> None:
		if reason is not None:
			disconnect_message = WriteStream()
			disconnect_message.write_header(GeneralMsg.DisconnectNotify)
			disconnect_message.write(c_uint(reason))
			conn.send(disconnect_message)

		conn.close()

	async def address_for_world(self, world_id: Tuple[int, int, int], conn_type: ConnectionType, include_self: bool=False) -> Address:
		first = True
		servers = {}
		while True:
			self.conn.sync()
			if world_id[0] % 100 == 0 or not first:
				for server_world, server_addresses in self.db.servers.items():
					if server_world[0] == world_id[0] and server_world[2] == world_id[2] and (world_id[0] % 100 == 0 or server_world not in servers):
						if not include_self and hasattr(self, "world_id") and self.world_id == server_world:
							continue
						return server_addresses[conn_type]
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
