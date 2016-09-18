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
	BattleAgainstFrakjaw = 2001
	FVSiege = 58001

import inspect
import logging
import re
import time

import pyraknet.replicamanager
from . import amf3
from . import ldf
from . import server
from .bitstream import BitStream, c_bit, c_float, c_int64, c_uint, c_ushort
from .game_object import GameObject
from .messages import GameMessage, WorldClientMsg, WorldServerMsg
from .math.quaternion import Quaternion
from .components.property import PropertyData, PropertySelectQueryProperty
from .math.vector import Vector3
from .modules.char import CharHandling
from .modules.chat import ChatHandling
from .modules.general import GeneralHandling
from .modules.mail import MailHandling
from .modules.physics import PhysicsHandling
from .modules.social import SocialHandling

log = logging.getLogger(__name__)

BITS_PERSISTENT = 1 << 60
BITS_LOCAL = 1 << 46
BITS_SPAWNED = 1 << 58 | BITS_LOCAL

class WorldServer(server.Server, pyraknet.replicamanager.ReplicaManager):
	PEER_TYPE = WorldServerMsg.__int__()

	def __init__(self, address, external_host, world_id, max_connections, db):
		server.Server.__init__(self, address, max_connections, db)
		pyraknet.replicamanager.ReplicaManager.__init__(self)
		self.external_address = external_host, address[1]
		self.not_console_logged_packets.add("GameMessage/DropClientLoot")
		self.modules = []
		self.char = CharHandling(self)
		self.chat = ChatHandling(self)
		self.general = GeneralHandling(self)
		self.mail = MailHandling(self)
		self.physics = PhysicsHandling(self)
		self.social = SocialHandling(self)

		self.current_spawned_id = BITS_SPAWNED
		self.world_data = None
		self.game_objects = {}
		self.models = []
		self.set_world_id(world_id)
		self.accounts = {}
		self.dropped_loot = {}

	async def init_network(self):
		await super().init_network()
		self.external_address = self.external_address[0], self._address[1] # update port (for OS-chosen port)
		self.db.servers[self.external_address] = self.world_id
		self.commit()

	def __del__(self):
		del self.db.servers[self.external_address]
		self.conn.transaction_manager.commit()
		time.sleep(0.5)

	def log_packet(self, data, address, received):
		try:
			packetname = self.packetname(data)
			if packetname in self.file_logged_packets:
				with open("logs/"+packetname+str(time.time())+".bin", "wb") as file:
					file.write(data)
			console_log = packetname not in self.not_console_logged_packets
		except ValueError:
			packetname = self.unknown_packetname(data)
			console_log = True

		if console_log:
			if received:
				log.debug("got %s", packetname)
			else:
				log.debug("snd %s", packetname)

			if packetname.startswith("GameMessage"):
				message = BitStream(data[8:])
				object_id = message.read(c_int64)
				obj = self.get_object(object_id)
				if obj:
					kwargs = self.read_game_message(obj, message, address, call_handler=False, return_kwargs=True)
					if kwargs is not None:
						log.debug(" ".join("%s: %s" % (key, value) for key, value in kwargs.items()))

	def conn_sync(self):
		super().conn_sync()
		self.reset_v_()

	def commit(self):
		self.conn.transaction_manager.commit()
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
			self.world_data = self.db.world_data[self.world_id[0]]
			for obj in self.world_data.objects.values():
				obj._v_server = self
				for comp in obj.components:
					if hasattr(comp, "on_startup"):
						comp.on_startup()
				if obj.lot == 176:
					obj.spawner.spawn()
			if self.world_id[2] != 0:
				self.models = []
				for spawner_id, spawn_data in self.db.properties[self.world_id[0]][self.world_id[2]].items():
					lot, position, rotation = spawn_data
					self.spawn_model(spawner_id, lot, position, rotation)
			self.physics.init()

	def spawn_model(self, spawner_id, lot, position, rotation):
		# todo: this is outdated, needs to be updated
		spawner = GameObject(self, 176, spawner_id)
		spawner.spawner.spawntemplate = lot
		spawner.physics.position.update(position)
		spawner.physics.rotation.update(rotation)
		spawner._v_server = self
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
				log.error("Database session key %s does not match supplied session key %s" % (self.db.accounts[username.lower()].session_key, session_key))
				self.close_connection(address, reason=server.DisconnectReason.InvalidSessionKey)
		except KeyError:
			log.error("User %s not found in database" % username.lower())
			self.close_connection(address)
		else:
			account = self.db.accounts[username.lower()]
			account.address = address
			self.commit()
			self.accounts[address] = account

			for module in self.modules:
				module.on_validated(address)

	def new_spawned_id(self):
		self.current_spawned_id += 1
		return self.current_spawned_id

	def new_object_id(self):
		current = self.db.current_object_id
		self.db.current_object_id += 1
		self.commit()
		return current | BITS_PERSISTENT

	def new_clone_id(self):
		current = self.db.current_clone_id
		self.db.current_clone_id += 1
		self.commit()
		return current

	def spawn_object(self, lot, spawner=None, parent=None, position=None, rotation=None, custom_script=None, set_vars={}):
		if spawner is not None:
			creator = spawner
		if parent is not None:
			creator = parent
		if position:
			if isinstance(position, Vector3):
				position = Vector3(position)
			else:
				position = Vector3(*position)
		else:
			position = Vector3(creator.physics.position)
		if rotation:
			if isinstance(rotation, Quaternion):
				rotation = Quaternion(rotation)
			else:
				rotation = Quaternion(*rotation)
		else:
			rotation = Quaternion(creator.physics.rotation)

		set_vars["position"] = position
		set_vars["rotation"] = rotation
		obj = GameObject(self, lot, self.new_spawned_id(), custom_script, set_vars)

		if spawner is not None:
			obj.spawner_object = spawner
			obj.spawner_waypoint_index = spawner.spawner.last_waypoint_index

		if parent is not None:
			obj.parent = parent.object_id
			parent.children.append(obj.object_id)
			parent.children_flag = True

		obj._serialize = False
		self.game_objects[obj.object_id] = obj
		self.construct(obj)

		if hasattr(obj, "rebuild"):
			self.spawn_object(6604, parent=obj, position=obj.rebuild.rebuild_activator_position)
		return obj

	def get_object(self, object_id):
		if object_id in self.game_objects:
			return self.game_objects[object_id]
		elif self.world_id[0] != 0 and object_id in self.world_data.objects:
			return self.world_data.objects[object_id]
		log.warn("Object %i not found", object_id)

	def find_player_by_name(self, name):
		for acc in self.db.accounts.values():
			for char in acc.characters.values():
				if char.name == name:
					return char
		raise KeyError

	# Game message stuff

	def send_game_message(self, func, *args, address=None, broadcast=False, **kwargs):
		"""
		Serialize a game message call.
		Arguments:
			func: The game message function to serialize
			*args, **kwargs: The arguments to pass to the function.
		The serialization is handled as follows:
			The Game Message ID is taken from the function name.
			The argument serialization order is taken from the function definition.
			Any arguments with defaults (a default of None is ignored)(also according to the function definition) will be wrapped in a flag and only serialized if the argument is not the default.
			The serialization type (c_int, c_float, etc) is taken from the argument annotation.
		"""
		multiple_components = isinstance(func, tuple)
		if multiple_components:
			obj, func_name = func
			for comp in obj.components:
				if hasattr(comp, func_name):
					func = getattr(comp, func_name)

		game_message_id = GameMessage[re.sub("(^|_)(.)", lambda match: match.group(2).upper(), func.__name__)].value
		out = BitStream()
		out.write_header(WorldClientMsg.GameMessage)
		if isinstance(func.__self__, GameObject):
			object_id = func.__self__.object_id
		else:
			object_id = func.__self__.object.object_id
		out.write(c_int64(object_id))
		out.write(c_ushort(game_message_id))

		signature = inspect.signature(func)
		bound_args = signature.bind(None, *args, **kwargs)

		for param in list(signature.parameters.values())[1:]:
			if param.annotation == c_bit:
				if param.name in bound_args.arguments:
					value = bound_args.arguments[param.name]
				else:
					value = param.default
				assert value in (True, False)
				out.write(param.annotation(value))
			else:
				if param.default not in (param.empty, None):
					is_not_default = param.name in bound_args.arguments and bound_args.arguments[param.name] != param.default
					out.write(c_bit(is_not_default))
					if not is_not_default:
						continue

				value = bound_args.arguments[param.name]
				assert value is not None
				self.game_message_serialize(out, param.annotation, value)

		if multiple_components:
			for comp in obj.components:
				if hasattr(comp, func_name):
					getattr(comp, func_name)(address, *args, **kwargs)
		else:
			func(address, *args, **kwargs)

		self.send(out, address, broadcast)

	def read_game_message(self, obj, message, address, call_handler=True, return_kwargs=False):
		"""Does the opposite of send_game_message."""
		message_id = message.read(c_ushort)
		try:
			message_name = GameMessage(message_id).name
		except ValueError:
			return
		message_handler = re.sub("(?!^)([A-Z])", r"_\1", message_name).lower()

		if hasattr(obj, message_handler):
			message_handler = getattr(obj, message_handler)
		else:
			for comp in obj.components:
				if hasattr(comp, message_handler):
					message_handler = getattr(comp, message_handler)
					break
			else:
				log.warn("%s has no handler for %s", obj, message_name)
				return

		signature = inspect.signature(message_handler)
		kwargs = {}
		for param in list(signature.parameters.values())[1:]:
			if param.annotation == c_bit:
				value = message.read(c_bit)
				if param.default not in (param.empty, None) and value == param.default:
					continue
			else:
				if param.default not in (param.empty, None):
					is_not_default = message.read(c_bit)
					if not is_not_default:
						continue

				value = self.game_message_deserialize(message, param.annotation)

			kwargs[param.name] = value
		assert message.all_read()
		if call_handler:
			message_handler(address=address, **kwargs)
		if return_kwargs:
			return kwargs

	def game_message_serialize(self, out, type, value):
		if isinstance(type, tuple):
			out.write(type[0](len(value)))
			if len(type) == 2: # list
				for i in value:
					self.game_message_serialize(out, type[1], i)
			elif len(type) == 3: # dict
				for k, v in value.items():
					self.game_message_serialize(out, type[1], k)
					self.game_message_serialize(out, type[2], v)

		elif type == Vector3:
			out.write(c_float(value.x))
			out.write(c_float(value.y))
			out.write(c_float(value.z))
		elif type == Quaternion:
			out.write(c_float(value.x))
			out.write(c_float(value.y))
			out.write(c_float(value.z))
			out.write(c_float(value.w))
		elif type in (PropertyData, PropertySelectQueryProperty):
			value.serialize(out)
		elif type == BitStream:
			out.write(c_uint(len(value)))
			out.write(bytes(value))
		elif type == "amf":
			amf3.write(value, out)
		elif type == "ldf":
			ldf_text = ldf.to_ldf(value, ldf_type="text")
			out.write(ldf_text, length_type=c_uint)
			if ldf_text:
				out.write(bytes(2)) # for some reason has a null terminator
		elif type == "str":
			out.write(value, char_size=1, length_type=c_uint)
		elif type == "wstr":
			out.write(value, char_size=2, length_type=c_uint)
		else:
			out.write(type(value))

	def game_message_deserialize(self, message, type):
		if isinstance(type, tuple):
			if len(type) == 2: # list
				value = []
				for _ in range(self.game_message_deserialize(message, type[0])):
					value.append(self.game_message_deserialize(message, type[1]))
			elif len(type) == 3: # dict
				value = {}
				for _ in range(self.game_message_deserialize(message, type[0])):
					value[self.game_message_deserialize(message, type[1])] = self.game_message_deserialize(message, type[2])
			return value

		if type == Vector3:
			return Vector3(message.read(c_float), message.read(c_float), message.read(c_float))
		if type == Quaternion:
			return Quaternion(message.read(c_float), message.read(c_float), message.read(c_float), message.read(c_float))
		if type == PropertyData:
			value = PropertyData()
			value.deserialize(message)
			return value
		if type == PropertySelectQueryProperty:
			value = PropertySelectQueryProperty()
			value.deserialize(message)
			return value
		if type == BitStream:
			length = message.read(c_uint)
			return BitStream(message.read(bytes, length=length))
		if type == "amf":
			return amf3.read(message)
		if type == "ldf":
			value = message.read(str, length_type=c_uint)
			if value:
				assert message.read(c_ushort) == 0 # for some reason has a null terminator
			# todo: convert to dict
			return value
		if type == "str":
			return message.read(str, char_size=1, length_type=c_uint)
		if type == "wstr":
			return message.read(str, char_size=2, length_type=c_uint)

		return message.read(type)
