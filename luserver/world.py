from enum import auto, Enum

# instance singleton
# can't just use a variable because it can't be updated when using from world import server
_server = None
class _Instance:
	def __getattribute__(self, name: str) -> object:
		return getattr(_server, name)

	def __setattr__(self, name: str, value: object) -> None:
		setattr(_server, name, value)

	def __delattr__(self, name: str) -> None:
		delattr(_server, name)

server: "WorldServer" = _Instance()

class Event(Enum):
	ProximityRadius = auto()
	Spawn = auto()

class World(Enum):
	VentureExplorer = 1000
	VE = VentureExplorer
	ReturnToTheVentureExplorer = 1001
	AvantGardens = 1100
	AG = AvantGardens
	AvantGardensSurvival = 1101
	AGSurvival = AvantGardensSurvival
	AGS = AvantGardensSurvival
	SpiderQueenBattle = 1102
	BlockYard = 1150
	AvantGrove = 1151
	AGPropLarge = 1152
	NimbusStation = 1200
	NS = NimbusStation
	PetCove = 1201
	PC = PetCove
	VertigoLoop = 1203
	TheBattleOfNimbusStation = 1204
	NimbusRock = 1250
	NimbusIsle = 1251
	GnarledForest = 1300
	GF = GnarledForest
	CannonCoveShootingGallery = 1302
	KeelhaulCanyon = 1303
	ChanteyShanty = 1350
	ForbiddenValley = 1400
	FV = ForbiddenValley
	FVSiege = 1401
	ForbiddenValleyDragonBattle = 1402
	DragonmawChasm = 1403
	RavenBluff = 1450
	Starbase3001 = 1600
	DeepFreeze = 1601
	RobotCity = 1602
	MoonBase = 1603
	Portabello = 1604
	LEGOClub = 1700
	CruxPrime = 1800
	CP = CruxPrime
	NexusTower = 1900
	NT = NexusTower
	NinjagoMonastery = 2000
	Ninjago = NinjagoMonastery
	BattleAgainstFrakjaw = 2001

import __main__
import asyncio
import atexit
import importlib.util
import logging
import os.path
from contextlib import AbstractContextManager as ACM
from ssl import SSLContext
from typing import Any, Callable, cast, Dict, List, Optional, Tuple

import BTrees
import ZODB
from persistent.mapping import PersistentMapping
from ZODB.Connection import Connection

import pyraknet.server
from bitstream import ReadStream
from pyraknet.messages import Address
from pyraknet.replicamanager import ReplicaManager
from pyraknet.transports.abc import ConnectionEvent, ConnectionType, TransportEvent
from .auth import Account
from .commonserver import DisconnectReason, Server, WorldData
from .game_object import CallbackID, Config, GameObject, ObjectID, Player, ScriptObject, SpawnerObject
from .messages import MessageType, WorldServerMsg
from .math.vector import Vector3
from .math.quaternion import Quaternion
from .modules.char import CharHandling
from .modules.chat import ChatHandling
from .modules.general import GeneralHandling
from .modules.mail import MailHandling
from .modules.social import SocialHandling

log = logging.getLogger(__name__)

BITS_PERSISTENT = 1 << 60
BITS_LOCAL = 1 << 46
BITS_SPAWNED = 1 << 58 | BITS_LOCAL

class MultiInstanceAccess(ACM):
	"""
	Context manager to safely modify objects that are modified by multiple instances.
	Internally this means committing before and after, so that edits are immediately committed and the DB doesn't have conflicts.
	"""

	def __enter__(self) -> None:
		server.commit()

	def __exit__(self, exc_type, exc_value, traceback) -> None:
		server.commit()

class WorldServer(Server):
	_PEER_TYPE = MessageType.WorldServer.value

	def __init__(self, address: Address, external_host: str, world_id: Tuple[int, int], max_connections: int, db_conn: Connection, ssl: Optional[SSLContext]):
		excluded_packets = {"PositionUpdate", "GameMessage/DropClientLoot", "GameMessage/PickupItem", "GameMessage/ReadyForUpdates", "GameMessage/ScriptNetworkVarUpdate"}
		super().__init__(address, max_connections, db_conn, ssl, excluded_packets)
		self.replica_manager = ReplicaManager(self._dispatcher)
		global _server
		_server = self
		self.external_host = external_host
		self._dispatcher.add_listener(TransportEvent.NetworkInit, self._on_network_init)
		self._dispatcher.add_listener(ConnectionEvent.Close, self._on_conn_close)
		self.multi = MultiInstanceAccess()
		self._handlers: Dict[Event, List[Callable[..., None]]] = {}
		self.char = CharHandling()
		self.chat = ChatHandling()
		self.general = GeneralHandling()
		self.mail = MailHandling()
		SocialHandling()

		self.instance_id = self.db.current_instance_id
		self.db.current_instance_id += 1
		self.commit()
		self.current_object_id = 0
		self.current_spawned_id = BITS_SPAWNED
		self.world_data: WorldData = None
		self.game_objects: Dict[ObjectID, GameObject] = {}
		self.player_data: Dict[Player, Dict] = {}
		self.models = []
		self.last_callback_id = CallbackID(0)
		self.callback_handles: Dict[ObjectID, Dict[CallbackID, asyncio.Handle]] = {}
		self.accounts: Dict[Connection, Account] = {}
		atexit.register(self.shutdown)
		asyncio.get_event_loop().call_later(60 * 60, self._check_shutdown)
		self._dispatcher.add_listener(WorldServerMsg.SessionInfo, self._on_session_info)
		self._load_plugins()
		self.set_world_id(world_id)

	def _on_network_init(self, conn_type: ConnectionType, address: Address) -> None:
		print(conn_type, address)
		external_address = self.external_host, address[1] # update port (for OS-chosen port)
		with self.multi:
			if self.world_id not in self.db.servers:
				self.db.servers[self.world_id] = PersistentMapping()
			self.db.servers[self.world_id][conn_type] = external_address

	def _check_shutdown(self) -> None:
		# shut down instances with no players every 60 minutes
		if not self.accounts:
			self.shutdown()
		else:
			asyncio.get_event_loop().call_later(60 * 60, self._check_shutdown)

	def shutdown(self) -> None:
		self.commit()
		for address in self.accounts.copy():
			self.close_connection(address, DisconnectReason.ServerShutdown)
		if self.world_id in self.db.servers:
			with self.multi:
				del self.db.servers[self.world_id]
		asyncio.get_event_loop().stop()
		log.info("Shutdown complete")

	def set_world_id(self, world_id: Tuple[int, int]) -> None:
		self.world_id = world_id[0], self.instance_id, world_id[1]
		if self.world_id[0] != 0: # char
			custom_script, world_control_lot = self.db.world_info[self.world_id[0]]
			if world_control_lot is None:
				world_control_lot = 2365
			self.world_control_object = cast(ScriptObject, self.spawn_object(world_control_lot, set_vars={"custom_script": custom_script}, is_world_control=True))

			self.spawners: Dict[str, SpawnerObject] = {}
			wd = self.db.world_data[self.world_id[0]]
			objs: Dict[ObjectID, GameObject] = {}
			for id, data in wd.objects.items():
				objs[id] = GameObject(*data)
			self.world_data = WorldData(objs, wd.paths, wd.spawnpoint)
			for obj in self.world_data.objects.values():
				obj.handle("startup", silent=True)
			if self.world_id[2] != 0:
				self.models = []
				for spawner_id, spawn_data in self.db.properties[self.world_id[0]][self.world_id[2]].items():
					lot, position, rotation = spawn_data
					self.spawn_model(spawner_id, lot, position, rotation)

	def add_handler(self, event: Event, handler: Callable[..., None]) -> None:
		self._handlers.setdefault(event, []).append(handler)

	def remove_handler(self, event: Event, handler: Callable[..., None]) -> None:
		if event not in self._handlers or handler not in self._handlers[event]:
			raise RuntimeError("handler not found")
		self._handlers[event].remove(handler)

	def handle(self, event: Event, *args: Any) -> None:
		if event not in self._handlers:
			return
		for handler in self._handlers[event]:
			handler(*args)

	def _load_plugins(self) -> None:
		plugin_dir = os.path.normpath(os.path.join(__main__.__file__, "..", "plugins"))

		with os.scandir(plugin_dir) as it:
			for entry in it:
				if entry.is_dir():
					spec = importlib.util.spec_from_file_location("luserver.plugins."+entry.name, os.path.join(entry.path, "__init__.py"))
					module = importlib.util.module_from_spec(spec)
					spec.loader.exec_module(module)

	def spawn_model(self, spawner_id: ObjectID, lot: int, position: Vector3, rotation: Quaternion) -> None:
		spawned_vars = {"position": position, "rotation": rotation}
		spawner_vars = {"spawntemplate": lot, "spawner_waypoints": (spawned_vars,)}
		spawner = cast(SpawnerObject, GameObject(176, spawner_id, set_vars=spawner_vars))
		self.models.append((spawner, spawner.spawner.spawn()))

	def _on_conn_close(self, conn: Connection) -> None:
		if self.world_id[0] != 0:
			player = self.accounts[conn].selected_char()
			if player in self.replica_manager._network_ids: # might already be destructed if "switch character" is selected:
				self.replica_manager.destruct(player)
		#self.accounts[conn].address = None
		del self.accounts[conn]
		self.commit()

	def _on_session_info(self, session_info: ReadStream, conn: Connection) -> None:
		self.commit()
		self.conn.sync()
		username = session_info.read(str, allocated_length=33)
		session_key = session_info.read(str, allocated_length=33)

		if username not in self.db.accounts:
			log.error("User %s not found in database", username)
			conn.close()
			return
		if self.db.accounts[username].session_key != session_key:
			log.error("Database session key %s does not match supplied session key %s", self.db.accounts[username].session_key, session_key)
			self.close_connection(conn, reason=DisconnectReason.InvalidSessionKey)
			return

		account = self.db.accounts[username]
		self.accounts[conn] = account

		self.general.on_validated(conn)

	def new_spawned_id(self) -> ObjectID:
		self.current_spawned_id += 1
		return self.current_spawned_id

	def new_object_id(self) -> ObjectID:
		self.current_object_id += 1
		return (self.instance_id << 16) | self.current_object_id | BITS_PERSISTENT

	def new_clone_id(self) -> ObjectID:
		current = self.db.current_clone_id
		self.db.current_clone_id += 1
		self.commit()
		return current

	def commit(self) -> None:
		# failsafe on conflict error: abort transaction
		try:
			self.conn.transaction_manager.commit()
		except ZODB.POSException.ConflictError as e:
			log.exception("Conflict error, aborting transaction")
			obj = self.conn.get(e.oid)
			old = self.conn.oldstate(obj, e.get_old_serial())
			new = self.conn.oldstate(obj, e.get_new_serial())
			if isinstance(new, (dict, PersistentMapping, BTrees.OOBTree.BTree, BTrees.IOBTree.BTree)):
				change_detected = False
				for key, value in new.items():
					if key not in old:
						log.error("other transaction added %s", key)
						change_detected = True
					if old[key] != new[key] and not hasattr(new[key], "__dict__") and not isinstance(new[key], list) and not isinstance(new[key], dict):
						log.error("other transaction changed %s from %s to %s",key, old[key], new[key])
						change_detected = True
				if not change_detected:
					log.error("no change detected, class is %s", type(new))
			else:
				log.error("old %s", old)
				log.error("new %s", new)

			self.conn.transaction_manager.abort()

	def spawn_object(self, lot: int, set_vars: Config=None, is_world_control: bool=False) -> GameObject:
		if set_vars is None:
			set_vars = {}

		if is_world_control:
			object_id = ObjectID(70368744177662)
		else:
			object_id = self.new_spawned_id()
		obj = GameObject(lot, object_id, set_vars)
		self.game_objects[obj.object_id] = obj
		self.replica_manager.construct(obj)
		obj.handle("startup", silent=True)
		self.handle(Event.Spawn, obj)
		return obj

	def get_object(self, object_id: ObjectID) -> GameObject:
		if object_id == 0:
			raise ValueError
		if object_id in self.game_objects:
			return self.game_objects[object_id]
		elif self.world_id[0] != 0 and object_id in self.world_data.objects:
			return self.world_data.objects[object_id]
		log.warning("Object %i not found", object_id)
		raise KeyError(object_id)

	def get_objects_in_group(self, group: str) -> List[GameObject]:
		matches = []
		for obj in self.game_objects.values():
			if group in obj.groups:
				matches.append(obj)
		if self.world_id[0] != 0:
			for obj in self.world_data.objects.values():
				if group in obj.groups:
					matches.append(obj)
		return matches

	def find_player_by_name(self, name: str) -> Player:
		for acc in self.db.accounts.values():
			for char in acc.characters.values():
				if char.name == name:
					return char
		raise KeyError
