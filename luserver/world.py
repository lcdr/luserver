from enum import Enum

class World(Enum):
	VentureExplorer = 1000
	VE = VentureExplorer
	ReturnToTheVentureExplorer = 1001
	AvantGardens = 1100
	AG = AvantGardens
	AvantGardensSurvival = 1101
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
	FVSiege = 58001

import atexit
import logging
import os.path
import time

import pyraknet.replicamanager
from . import server
from .game_object import GameObject
from .messages import WorldServerMsg
from .modules.char import CharHandling
from .modules.chat import ChatHandling
from .modules.general import GeneralHandling
from .modules.mail import MailHandling
from .modules.social import SocialHandling

log = logging.getLogger(__name__)

BITS_PERSISTENT = 1 << 60
BITS_LOCAL = 1 << 46
BITS_SPAWNED = 1 << 58 | BITS_LOCAL

class WorldServer(server.Server, pyraknet.replicamanager.ReplicaManager):
	PEER_TYPE = WorldServerMsg.header()

	def __init__(self, address, external_host, world_id, max_connections, db_conn):
		server.Server.__init__(self, address, max_connections, db_conn)
		pyraknet.replicamanager.ReplicaManager.__init__(self)
		self.external_address = external_host, address[1]
		self.not_console_logged_packets.add("ReplicaManagerSerialize")
		self.not_console_logged_packets.add("PositionUpdate")
		self.not_console_logged_packets.add("GameMessage/DropClientLoot")
		self.not_console_logged_packets.add("GameMessage/PickupItem")
		self.not_console_logged_packets.add("GameMessage/ReadyForUpdates")
		self.not_console_logged_packets.add("GameMessage/ScriptNetworkVarUpdate")
		self.modules = []
		self.char = CharHandling(self)
		self.chat = ChatHandling(self)
		self.general = GeneralHandling(self)
		self.mail = MailHandling(self)
		self.social = SocialHandling(self)

		self.instance_id = self.db.current_instance_id
		self.db.current_instance_id += 1
		self.conn.transaction_manager.commit()
		self.current_object_id = 0
		self.current_spawned_id = BITS_SPAWNED
		self.world_data = None
		self.game_objects = {}
		self.models = []
		self.last_callback_id = 0
		self.callback_handles = {}
		self.set_world_id(world_id)
		self.accounts = {}
		atexit.register(self.shutdown)

	async def init_network(self):
		await super().init_network()
		self.external_address = self.external_address[0], self._address[1] # update port (for OS-chosen port)
		self.db.servers[self.external_address] = self.world_id
		self.commit()

	def shutdown(self):
		self.conn_sync()
		for address in self.accounts.copy():
			self.close_connection(address, server.DisconnectReason.ServerShutdown)
		del self.db.servers[self.external_address]
		self.conn.transaction_manager.commit()
		log.info("Shutdown complete")

	def log_packet(self, data, address, received):
		try:
			packetname = self.packetname(data)
			console_log = packetname not in self.not_console_logged_packets
		except ValueError:
			packetname = self.unknown_packetname(data)
			console_log = True

		if packetname in self.file_logged_packets:
			with open(os.path.join(__file__, "..", "..", "runtime", "logs", packetname+str(time.time())+".bin"), "wb") as file:
				file.write(data)

		if console_log:
			if received:
				log.debug("got %s", packetname)
			else:
				log.debug("snd %s", packetname)

	def conn_sync(self):
		super().conn_sync()
		self.reset_v_()

	def commit(self):
		try:
			self.conn.transaction_manager.commit()
		finally:
			self.reset_v_()

	def reset_v_(self):
		if self.world_id[0] != 0: # char
			for obj in self.world_data.objects.values():
				obj._v_server = self
			for obj in self.game_objects.values():
				obj._v_server = self

	def set_world_id(self, world_id):
		self.world_id = world_id[0], 0, world_id[1]
		if self.world_id[0] != 0: # char
			custom_script, world_control_lot = self.db.world_info[self.world_id[0]]
			if world_control_lot is None:
				world_control_lot = 2365
			self.world_control_object = self.spawn_object(world_control_lot, set_vars={"custom_script": custom_script}, is_world_control=True)

			self.spawners = {}
			self.world_data = self.db.world_data[self.world_id[0]]
			self.reset_v_()
			for obj in self.world_data.objects.values():
				obj.handle("on_startup", silent=True)
			if self.world_id[2] != 0:
				self.models = []
				for spawner_id, spawn_data in self.db.properties[self.world_id[0]][self.world_id[2]].items():
					lot, position, rotation = spawn_data
					self.spawn_model(spawner_id, lot, position, rotation)

	def spawn_model(self, spawner_id, lot, position, rotation):
		spawned_vars = {}
		spawned_vars["position"] = position
		spawned_vars["rotation"] = rotation
		spawner_vars = {}
		spawner_vars["spawntemplate"] = lot
		spawner_vars["spawner_waypoints"] = spawned_vars,
		spawner = GameObject(self, 176, spawner_id, set_vars=spawner_vars)
		self.models.append((spawner, spawner.spawner.spawn()))

	def on_disconnect_or_connection_lost(self, data, address):
		super().on_disconnect_or_connection_lost(data, address)
		pyraknet.replicamanager.ReplicaManager.on_disconnect_or_connection_lost(self, data, address)
		if self.world_id[0] != 0:
			player = self.accounts[address].characters.selected()
			if player in self._network_ids: # might already be destructed if "switch character" is selected:
				self.destruct(player)
		self.accounts[address].address = None
		del self.accounts[address]
		self.commit()

	def on_handshake(self, data, address):
		super().on_handshake(data, address)
		self.register_handler(WorldServerMsg.SessionInfo, self.on_session_info, address)

	def on_session_info(self, session_info, address):
		self.conn_sync()
		username = session_info.read(str, allocated_length=66)
		session_key = session_info.read(str, allocated_length=66)

		try:
			if self.db.accounts[username.lower()].session_key != session_key:
				log.error("Database session key %s does not match supplied session key %s", self.db.accounts[username.lower()].session_key, session_key)
				self.close_connection(address, reason=server.DisconnectReason.InvalidSessionKey)
		except KeyError:
			log.error("User %s not found in database", username.lower())
			self.close_connection(address)
		else:
			account = self.db.accounts[username.lower()]
			account.address = address
			self.commit()
			self.accounts[address] = account

			for module in self.modules:
				module.on_validated(address)

	def construct(self, obj, recipients=None, new=True):
		pyraknet.replicamanager.ReplicaManager.construct(self, obj, recipients, new)

	def destruct(self, obj):
		pyraknet.replicamanager.ReplicaManager.destruct(self, obj)

	def new_spawned_id(self):
		self.current_spawned_id += 1
		return self.current_spawned_id

	def new_object_id(self):
		self.current_object_id += 1
		return (self.instance_id << 16)| self.current_object_id | BITS_PERSISTENT

	def new_clone_id(self):
		current = self.db.current_clone_id
		self.db.current_clone_id += 1
		self.commit()
		return current

	def spawn_object(self, lot, set_vars=None, is_world_control=False):
		if set_vars is None:
			set_vars = {}

		if is_world_control:
			object_id = 70368744177662
		else:
			object_id = self.new_spawned_id()
		obj = GameObject(self, lot, object_id, set_vars)
		self.game_objects[obj.object_id] = obj
		self.construct(obj)
		obj.handle("on_startup", silent=True)
		return obj

	def get_object(self, object_id):
		if object_id == 0:
			return
		if object_id in self.game_objects:
			return self.game_objects[object_id]
		elif self.world_id[0] != 0 and object_id in self.world_data.objects:
			return self.world_data.objects[object_id]
		log.warning("Object %i not found", object_id)

	def get_objects_in_group(self, group):
		matches = []
		for obj in self.game_objects.values():
			if group in obj.groups:
				matches.append(obj)
		if self.world_id[0] != 0:
			for obj in self.world_data.objects.values():
				if group in obj.groups:
					matches.append(obj)
		return matches

	def find_player_by_name(self, name):
		for acc in self.db.accounts.values():
			for char in acc.characters.values():
				if char.name == name:
					return char
		raise KeyError
