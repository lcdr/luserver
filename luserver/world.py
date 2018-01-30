from enum import Enum

# instance singleton
# can't just use a variable because it can't be updated when using from world import server
_server = None
class _Instance:
	def __getattribute__(self, name):
		return getattr(_server, name)

	def __setattr__(self, name, value):
		return setattr(_server, name, value)

	def __delattr__(self, name):
		return delattr(_server, name)

server = _Instance()

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
from typing import Callable, List, Optional

import BTrees
import ZODB
from persistent.mapping import PersistentMapping

from pyraknet.bitstream import ReadStream
from pyraknet.messages import Address
from pyraknet.replicamanager import ReplicaManager
from pyraknet.server import Event
from .commonserver import DisconnectReason, Server
from .game_object import GameObject, ObjectID
from .messages import WorldServerMsg
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

	def __enter__(self):
		server.commit()

	def __exit__(self, exc_type, exc_value, traceback):
		server.commit()

class WorldServer(Server):
	def __init__(self, address, external_host, world_id, max_connections, db_conn):
		super().__init__(address, max_connections, db_conn)
		self.replica_manager = ReplicaManager(self._server)
		global _server
		_server = self
		self.external_address = external_host, address[1]
		self._server.add_handler(Event.NetworkInit, self._on_network_init)
		self._server.add_handler(Event.Disconnect, self._on_disconnect_or_connection_lost)
		self._server.not_console_logged_packets.add("ReplicaManagerSerialize")
		self.not_console_logged_packets.add("PositionUpdate")
		self.not_console_logged_packets.add("GameMessage/DropClientLoot")
		self.not_console_logged_packets.add("GameMessage/PickupItem")
		self.not_console_logged_packets.add("GameMessage/ReadyForUpdates")
		self.not_console_logged_packets.add("GameMessage/ScriptNetworkVarUpdate")
		self.multi = MultiInstanceAccess()
		self._handlers = {}
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
		self.world_data = None
		self.game_objects = {}
		self.models = []
		self.last_callback_id = 0
		self.callback_handles = {}
		self.accounts = {}
		atexit.register(self.shutdown)
		asyncio.get_event_loop().call_later(60 * 60, self._check_shutdown)
		self.register_handler(WorldServerMsg.SessionInfo, self._on_session_info)
		self._load_plugins()
		self.set_world_id(world_id)

	def peer_type(self) -> int:
		return WorldServerMsg.header()

	def _on_network_init(self, address: Address) -> None:
		self.external_address = self.external_address[0], address[1] # update port (for OS-chosen port)
		with self.multi:
			self.db.servers[self.external_address] = self.world_id

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
		if self.external_address in self.db.servers:
			with self.multi:
				del self.db.servers[self.external_address]
		asyncio.get_event_loop().stop()
		log.info("Shutdown complete")

	def set_world_id(self, world_id) -> None:
		self.world_id = world_id[0], 0, world_id[1]
		if self.world_id[0] != 0: # char
			custom_script, world_control_lot = self.db.world_info[self.world_id[0]]
			if world_control_lot is None:
				world_control_lot = 2365
			self.world_control_object = self.spawn_object(world_control_lot, set_vars={"custom_script": custom_script}, is_world_control=True)

			self.spawners = {}
			self.world_data = self.db.world_data[self.world_id[0]]
			for obj in self.world_data.objects.values():
				obj.handle("on_startup", silent=True)
			if self.world_id[2] != 0:
				self.models = []
				for spawner_id, spawn_data in self.db.properties[self.world_id[0]][self.world_id[2]].items():
					lot, position, rotation = spawn_data
					self.spawn_model(spawner_id, lot, position, rotation)

	EVENT_NAMES = "proximity_radius", "spawn"

	def add_handler(self, event_name: str, handler: Callable[..., None]) -> None:
		if event_name not in WorldServer.EVENT_NAMES:
			raise ValueError("Invalid event name %s", event_name)
		self._handlers.setdefault(event_name, []).append(handler)

	def remove_handler(self, event_name: str, handler: Callable[..., None]) -> None:
		if event_name not in WorldServer.EVENT_NAMES:
			raise ValueError("Invalid event name %s", event_name)
		if event_name not in self._handlers or handler not in self._handlers[event_name]:
			raise RuntimeError("handler not found")
		self._handlers[event_name].remove(handler)

	def handle(self, event_name: str, *args) -> None:
		if event_name not in WorldServer.EVENT_NAMES:
			raise ValueError("Invalid event name %s", event_name)
		if event_name not in self._handlers:
			return
		for handler in self._handlers[event_name]:
			handler(*args)

	def _load_plugins(self) -> None:
		plugin_dir = os.path.normpath(os.path.join(__main__.__file__, "..", "plugins"))

		with os.scandir(plugin_dir) as it:
			for entry in it:
				if entry.is_dir():
					spec = importlib.util.spec_from_file_location("luserver.plugins."+entry.name, os.path.join(entry.path, "__init__.py"))
					module = importlib.util.module_from_spec(spec)
					spec.loader.exec_module(module)

	def spawn_model(self, spawner_id, lot, position: Vector3, rotation: Quaternion) -> None:
		spawned_vars = {"position": position, "rotation": rotation}
		spawner_vars = {"spawntemplate": lot, "spawner_waypoints": spawned_vars}
		spawner = GameObject(176, spawner_id, set_vars=spawner_vars)
		self.models.append((spawner, spawner.spawner.spawn()))

	def _on_disconnect_or_connection_lost(self, address: Address) -> None:
		if self.world_id[0] != 0:
			player = self.accounts[address].characters.selected()
			if player in self.replica_manager._network_ids: # might already be destructed if "switch character" is selected:
				self.replica_manager.destruct(player)
		#self.accounts[address].address = None
		del self.accounts[address]
		self.commit()

	def _on_session_info(self, session_info: ReadStream, address: Address) -> None:
		self.commit()
		self.conn.sync()
		username = session_info.read(str, allocated_length=33)
		session_key = session_info.read(str, allocated_length=33)

		try:
			if self.db.accounts[username].session_key != session_key:
				log.error("Database session key %s does not match supplied session key %s", self.db.accounts[username].session_key, session_key)
				self.close_connection(address, reason=DisconnectReason.InvalidSessionKey)
		except KeyError:
			log.error("User %s not found in database", username)
			self.close_connection(address)
		else:
			account = self.db.accounts[username]
			#account.address = address
			#self.conn.transaction_manager.commit()
			self.accounts[address] = account

			self.general.on_validated(address)

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

	def spawn_object(self, lot, set_vars=None, is_world_control=False) -> GameObject:
		if set_vars is None:
			set_vars = {}

		if is_world_control:
			object_id = ObjectID(70368744177662)
		else:
			object_id = self.new_spawned_id()
		obj = GameObject(lot, object_id, set_vars)
		self.game_objects[obj.object_id] = obj
		self.replica_manager.construct(obj)
		obj.handle("on_startup", silent=True)
		self.handle("spawn", obj)
		return obj

	def get_object(self, object_id) -> Optional[GameObject]:
		if object_id == 0:
			return
		if object_id in self.game_objects:
			return self.game_objects[object_id]
		elif self.world_id[0] != 0 and object_id in self.world_data.objects:
			return self.world_data.objects[object_id]
		log.warning("Object %i not found", object_id)

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

	def find_player_by_name(self, name: str) -> GameObject:
		for acc in self.db.accounts.values():
			for char in acc.characters.values():
				if char.name == name:
					return char
		raise KeyError
