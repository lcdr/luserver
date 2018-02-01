import asyncio
import functools
import importlib
import inspect
import logging
import re
from collections import OrderedDict
from functools import wraps
from typing import Callable, cast, Dict, Generic, List, NewType, Tuple, Type, TypeVar, TYPE_CHECKING, Union
from typing import Sequence as Sequence_
from typing import Mapping as Mapping_

from persistent import Persistent

from pyraknet.bitstream import c_bit, c_float, c_ubyte, c_ushort, ReadStream, Serializable, UnsignedIntStruct, WriteStream
from pyraknet.bitstream import c_int as c_int_
from pyraknet.bitstream import c_int64 as c_int64_
from pyraknet.bitstream import c_uint as c_uint_
from pyraknet.bitstream import c_uint64 as c_uint64_
from pyraknet.messages import Address
from pyraknet.replicamanager import Replica
from .bitstream import WriteStream as WriteStream_
from .ldf import LDF
from .messages import GameMessage, WorldClientMsg
from .world import server

log = logging.getLogger(__name__)

ObjectID = NewType("ObjectID", int)
CallbackID = NewType("CallbackID", int)
if TYPE_CHECKING:
	E = inspect.Parameter.empty
	c_int = int
	c_int64 = int
	c_uint = int
	c_uint64 = int
else:
	E = "empty"
	c_int = c_int_
	c_int64 = c_int64_
	c_uint = c_uint_
	c_uint64 = c_uint64_

T = TypeVar("T", bound=UnsignedIntStruct)
U = TypeVar("U")
V = TypeVar("V")

class Sequence(Generic[T, U], Sequence_[U]):
	pass

class Mapping(Generic[T, U, V], Mapping_[U, V]):
	pass

class GameObject(Replica):
	def __setattr__(self, name: str, value: object) -> None:
		self.attr_changed(name)
		super().__setattr__(name, value)

	def __init__(self, lot: int, object_id: ObjectID, set_vars: Dict[str, object]=None):
		if set_vars is None:
			set_vars = {}
		self._handlers: Dict[str, List[Callable[..., None]]] = {}
		self._flags: Dict[str, str] = {
			"parent_flag": "related_objects_flag",
			"children_flag": "related_objects_flag",
			"parent": "parent_flag",
			"children": "children_flag"}
		self._serialize_scheduled = True
		self.lot = lot
		self.object_id = object_id
		self.name = set_vars.get("name", "")
		if len(self.name) > 32:
			raise ValueError("Due to a client bug, names can't be longer than 32 chars")
		self.config = set_vars.get("config", LDF())

		if "spawner" in set_vars:
			self.spawner_object = set_vars["spawner"]
			self.spawner_waypoint_index = set_vars["spawner"].spawner.last_waypoint_index
		else:
			self.spawner_object = None
			self.spawner_waypoint_index = 0

		self.scale = set_vars.get("scale", 1)

		if "parent" in set_vars and set_vars["parent"].object_id in server.game_objects:
			self.parent = set_vars["parent"].object_id
			set_vars["parent"].children.append(self.object_id)
			set_vars["parent"].attr_changed("children")
		else:
			self.parent = None

		self.children: List[int] = []
		self.groups = set_vars.get("groups", ())
		if "respawn_name" in set_vars:
			self.respawn_name = set_vars["respawn_name"]
		if "primitive_model_type" in set_vars:
			self.primitive_model_type = set_vars["primitive_model_type"]
		if "primitive_model_scale" in set_vars:
			self.primitive_model_scale = set_vars["primitive_model_scale"]
		self.components: List[Component] = []

		comps: Dict[Type[Component], int] = OrderedDict()

		comp_ids = list(server.db.components_registry[self.lot])
		if "custom_script" in set_vars:
			# add custom script if no script is already there
			for comp in comp_ids:
				if comp[0] == 5:
					break
			else:
				comp_ids.append((5, None))
		if "render_disabled" in set_vars:
			for comp in comp_ids.copy():
				if comp[0] == 2:
					comp_ids.remove(comp)
		if "marked_as_phantom" in set_vars:
			for comp in comp_ids.copy():
				if comp[0] == 3:
					comp_ids.remove(comp)
			comp_ids.append((40, None))

		for component_type, component_id in sorted(comp_ids, key=lambda x: component_order.index(x[0]) if x[0] in component_order else 99999):
			if component_type == 5:
				if "custom_script" in set_vars and set_vars["custom_script"] is not None:
					try:
						script = importlib.import_module("luserver.scripts."+set_vars["custom_script"])
						comp = script.ScriptComponent,
					except ModuleNotFoundError as e:
						log.warning(str(e))
						comp = ScriptComponent,
				elif component_id is not None and component_id in server.db.script_component:
					try:
						script = importlib.import_module("luserver.scripts."+server.db.script_component[component_id])
						comp = script.ScriptComponent,
					except ModuleNotFoundError as e:
						log.warning(str(e))
						comp = ScriptComponent,
				else:
					comp = ScriptComponent,
			elif component_type in component:
				comp = component[component_type]
			else:
				#print("Component type %i has no class!" % component_type)
				continue
			for subcomp in comp:
				if subcomp not in comps:
					comps[subcomp] = component_id

		if "trigger_events" in set_vars:
			comps[TriggerComponent] = None

		for comp, comp_id in comps.items():
			self.components.append(comp(self, set_vars, comp_id))

	def __repr__(self) -> str:
		return "<GameObject \"%s\", %i, %i>" % (self.name, self.object_id, self.lot)

	def attr_changed(self, name: str) -> None:
		"""In case an attribute change is not registered by __setattr__ (like setting an attribute of an attribute), manually register the change by calling this. Without a registered change changes will not be broadcast to clients!"""
		if hasattr(self, "_flags") and name in self._flags:
			setattr(self, self._flags[name], hasattr(self, name))
			self.signal_serialize()

	def signal_serialize(self) -> None:
		if not self._serialize_scheduled:
			self.call_later(0, self._do_serialize)
			self._serialize_scheduled = True

	def _do_serialize(self) -> None:
		server.replica_manager.serialize(self)
		self._serialize_scheduled = False

	def write_construction(self, stream: WriteStream) -> None:
		stream.write(c_int64_(self.object_id))
		stream.write(c_int_(self.lot))
		stream.write(self.name, length_type=c_ubyte)

		stream.write(bytes(4)) # time since created on server?
		stream.write(c_bit(self.config))
		if self.config:
			stream.write(self.config.to_bitstream())
		stream.write(c_bit(hasattr(self, "trigger")))
		stream.write(c_bit(self.spawner_object is not None))
		if self.spawner_object is not None:
			stream.write(c_int64_(self.spawner_object.object_id))
		stream.write(c_bit(self.spawner_object is not None))
		if self.spawner_object is not None:
			stream.write(c_uint_(self.spawner_waypoint_index))
		stream.write(c_bit(self.scale != 1))
		if self.scale != 1:
			stream.write(c_float(self.scale))
		stream.write(c_bit(False))
		stream.write(c_bit(False))

		self.serialize(stream, True)

		self._serialize_scheduled = False

	def serialize(self, stream: WriteStream, is_creation: bool=False) -> None:
		stream.write(c_bit(self.related_objects_flag or (is_creation and (self.parent is not None or self.children))))
		if self.related_objects_flag or (is_creation and (self.parent is not None or self.children)):
			stream.write(c_bit(self.parent_flag or (is_creation and self.parent is not None)))
			if self.parent_flag or (is_creation and self.parent is not None):
				if self.parent is not None:
					stream.write(c_int64_(self.parent))
				else:
					stream.write(c_int64_(0))
				stream.write(c_bit(False))
				self.parent_flag = False

			stream.write(c_bit(self.children_flag or (is_creation and self.children)))
			if self.children_flag or (is_creation and self.children):
				stream.write(c_ushort(len(self.children)))
				for child in self.children:
					stream.write(c_int64_(child))
				self.children_flag = False

			self.related_objects_flag = False

		for comp in self.components:
			comp.serialize(stream, is_creation)

	def on_destruction(self) -> None:
		self._serialize_scheduled = True # prevent any serializations from now on
		if self.parent is not None:
			server.game_objects[self.parent].children.remove(self.object_id)
			server.game_objects[self.parent].attr_changed("children")

		for child in self.children.copy():
			server.replica_manager.destruct(server.game_objects[child])

		if self.object_id in server.callback_handles:
			for handle in server.callback_handles[self.object_id].values():
				handle.cancel()
			del server.callback_handles[self.object_id]

		self.handle("on_destruction", silent=True)

		del server.game_objects[self.object_id]

	def add_handler(self, event_name: str, handler: Callable[..., None]) -> None:
		self._handlers.setdefault(event_name, []).append(functools.partial(handler, self))

	def remove_handler(self, event_name: str, handler: Callable[..., None]) -> None:
		if event_name not in self._handlers:
			return
		if handler in self._handlers[event_name]:
			self._handlers[event_name].remove(handler)

	def handlers(self, event_name: str, silent: bool=False) -> List[Callable]:
		"""
		Return matching handlers for an event.
		Handlers are returned in serialization order, except for ScriptComponent, which is moved to the bottom of the list.
		"""
		handlers: List[Callable] = []
		script_handler = None
		if event_name in self._handlers:
			handlers.extend(self._handlers[event_name])
		for comp in self.components:
			if hasattr(comp, event_name):
				handler = getattr(comp, event_name)
				if isinstance(comp, ScriptComponent):
					script_handler = handler
				else:
					handlers.append(handler)
		if script_handler is not None:
			handlers.append(script_handler)

		if not handlers and not silent:
			log.info("Object %s has no handlers for %s", self, event_name)

		return handlers

	def handle(self, event_name: str, *args, silent=False, **kwargs) -> None:
		"""
		Calls handlers for an event. See handlers() for the order of handlers.
		If a handler returns True, it's assumed that the handler has sufficiently handled the event and no further handlers will be called.
		"""
		for handler in self.handlers(event_name, silent):
			if handler(*args, **kwargs):
				break

	def send_game_message(self, handler_name: str, *args, **kwargs) -> None:
		"""For game messages with multiple handlers: call all the handlers but only send one message over the network."""
		handlers = self.handlers(handler_name)
		if not handlers:
			return

		send_handler = handlers[0]
		send_handler(*args, **kwargs)
		for handler in handlers[1:]:
			handler.__wrapped__(handler.__self__, *args, **kwargs)

	def call_later(self, delay: float, callback: Callable[..., None], *args) -> CallbackID:
		"""
		Call a callback in delay seconds. The callback's handle is recorded so that when the object is destructed all pending callbacks are automatically cancelled.
		Return the callback id to be used for cancel_callback.
		"""
		callback_id = server.last_callback_id
		server.callback_handles.setdefault(self.object_id, {})[callback_id] = asyncio.get_event_loop().call_later(delay, self._callback, callback_id, callback, *args)
		server.last_callback_id += 1
		return callback_id

	def _callback(self, callback_id: CallbackID, callback: Callable[..., None], *args) -> None:
		"""Execute a callback and delete the handle from the list because it won't be cancelled."""
		del server.callback_handles[self.object_id][callback_id]
		callback(*args)

	def cancel_callback(self, callback_id: CallbackID) -> None:
		"""Cancel a callback and delete the handle from the list."""
		if callback_id in server.callback_handles[self.object_id]:
			server.callback_handles[self.object_id][callback_id].cancel()
			del server.callback_handles[self.object_id][callback_id]

	def on_game_message(self, message: ReadStream, address: Address) -> None:
		message_id = message.read(c_ushort)
		try:
			message_name = GameMessage(message_id).name
		except ValueError:
			return
		handler_name = re.sub("(?!^)([A-Z])", r"_\1", message_name).lower()

		handlers = self.handlers(handler_name)
		if not handlers:
			return

		signature = inspect.signature(handlers[0])
		kwargs = {}
		params = list(signature.parameters.values())
		if params and params[0].name == "player" and params[0].default == inspect.Parameter.empty:
			params.pop(0)
		for param in params:
			if param.annotation == bool:
				value = message.read(c_bit)
				if param.default not in (param.empty, E) and value == param.default:
					continue
			else:
				if param.default not in (param.empty, E):
					is_not_default = message.read(c_bit)
					if not is_not_default:
						continue

				value = self._game_message_deserialize(message, param.annotation)

			kwargs[param.name] = value
		assert message.all_read()

		if message_name != "ReadyForUpdates": # todo: don't hardcode this
			if kwargs:
				log.debug(", ".join("%s=%s" % (key, value) for key, value in kwargs.items()))

		player = server.accounts[address].characters.selected()
		for handler in handlers:
			if hasattr(handler, "__wrapped__"):
				handler = functools.partial(handler.__wrapped__, handler.__self__)
			signature = inspect.signature(handler)
			playerarg = "player" in signature.parameters
			if playerarg:
				it = iter(signature.parameters.keys())
				playerarg = next(it) == "player"
				if playerarg:
					arg = signature.parameters["player"]
					playerarg = arg.default == inspect.Parameter.empty
			if playerarg:
				handler(player, **kwargs)
			else:
				handler(**kwargs)

	def _game_message_deserialize(self, message: ReadStream, type_):
		value: Union[str, list, dict]
		if type_ == float:
			return message.read(c_float)
		if type_ == bytes:
			return message.read(bytes, length_type=c_uint_)
		if type_ == str:
			return message.read(str, length_type=c_uint_)
		if type_ in (c_int_, c_int64_, c_ubyte, c_uint_, c_uint64_):
			return message.read(type_)
		if type_ == LDF:
			value = message.read(str, length_type=c_uint_)
			if value:
				assert message.read(c_ushort) == 0  # for some reason has a null terminator
			# todo: convert to LDF
			return value
		if issubclass(type_, GameObject):
			return server.get_object(message.read(c_int64_))
		if issubclass(type_, Serializable):
			return type_.deserialize(message)
		if issubclass(type_, Sequence):
			length_type, value_type = type_.__args__
			value = []
			for _ in range(self._game_message_deserialize(message, length_type)):
				value.append(self._game_message_deserialize(message, value_type))
			return value
		if issubclass(type_, Mapping):
			length_type, key_type, value_type = type_.__args__
			value = {}
			for _ in range(self._game_message_deserialize(message, length_type)):
				key = self._game_message_deserialize(message, key_type)
				val = self._game_message_deserialize(message, value_type)
				value[key] = val
			return value
		raise TypeError(type_)

class Player(GameObject, Persistent):
	char: "CharacterComponent"

	def __init__(self, object_id: ObjectID):
		GameObject.__init__(self, 1, object_id)
		Persistent.__init__(self)

	def __setattr__(self, name, value):
		if not self._p_setattr(name, value):
			super().__setattr__(name, value)
			self._p_changed = True

# backwards compatibility
PersistentObject = Player

OBJ_NONE = cast(Player, None)

# these are for static typing and shouldn't actually be used
class PhysicsObject(GameObject):
	physics: "PhysicsComponent"

class StatsObject(GameObject):
	stats: "StatsSubcomponent"

W = TypeVar("W")

def _send_game_message(mode: str) -> Callable[[W], W]:
	"""
	Send a game message on calling its function.
	Modes:
		broadcast: The game message will be sent to all connected players. If "player" is specified, that player will be excluded.
		single: The game message will only be sent to the player this game message belongs to. If the object is not a player, specify "player" explicitly.
	The serialization is handled as follows:
		The Game Message ID is taken from the function name.
		The argument serialization order is taken from the function definition.
		Any arguments with defaults (a default of None is ignored)(also according to the function definition) will be wrapped in a flag and only serialized if the argument is not the default.
		The serialization type (c_int, float, etc) is taken from the argument annotation.

	If the function has "player" as the first argument, the player that this message will be sent to will be passed to the function as that argument. Note that this only really makes sense to specify in "single" mode.
	"""
	def decorator(func):
		from .world import server

		@wraps(func)
		def wrapper(self, *args, **kwargs):
			game_message_id = GameMessage[re.sub("(^|_)(.)", lambda match: match.group(2).upper(), func.__name__)].value
			out = WriteStream_()
			out.write_header(WorldClientMsg.GameMessage)
			object_id = self.object.object_id
			out.write(c_int64_(object_id))
			out.write(c_ushort(game_message_id))

			signature = inspect.signature(func)
			params = list(signature.parameters.values())[1:]

			if "player" in kwargs:
				player = kwargs["player"]
			else:
				player = None
			if params and params[0].name == "player":
				params.pop(0)
			else:
				if "player" in kwargs:
					del kwargs["player"]

			bound_args = signature.bind(self, *args, **kwargs)
			for param in params:
				if param.annotation == bool:
					if param.name in bound_args.arguments:
						value = bound_args.arguments[param.name]
					else:
						value = param.default
					assert value in (True, False)
					out.write(c_bit(value))
				else:
					if param.default not in (param.empty, E):
						is_not_default = param.name in bound_args.arguments and bound_args.arguments[param.name] != param.default
						out.write(c_bit(is_not_default))
						if not is_not_default:
							continue

					if param.name not in bound_args.arguments:
						raise TypeError("\"%s\" needs to be specified" % param.name)
					value = bound_args.arguments[param.name]
					_game_message_serialize(out, param.annotation, value)
			if mode == "broadcast":
				exclude_address = None
				if player is not None:
					exclude_address = player.char.address
				server.send(out, address=exclude_address, broadcast=True)
			elif mode == "single":
				if player is None:
					player = self.object
				server.send(out, address=player.char.address)
			if func.__name__ not in ("drop_client_loot", "script_network_var_update"): # todo: don't hardcode this
				if len(bound_args.arguments) > 1:
					log.debug(", ".join("%s=%s" % (key, value) for key, value in list(bound_args.arguments.items())[1:]))
			return func(self, *args, **kwargs)
		return wrapper
	return decorator


def _game_message_serialize(out, type_, value):
	if type_ == float:
		out.write(c_float(value))
	elif type_ == bytes:
		out.write(value, length_type=c_uint_)
	elif type_ == str:
		out.write(value, length_type=c_uint_)
	elif type_ in (c_int_, c_int64_, c_ubyte, c_uint_, c_uint64_):
		out.write(type_(value))
	elif type_ == LDF:
		ldf_text = value.to_str()
		out.write(ldf_text, length_type=c_uint_)
		if ldf_text:
			out.write(bytes(2)) # for some reason has a null terminator
	elif issubclass(type_, GameObject):
		if value is OBJ_NONE:
			out.write(c_int64_(0))
		else:
			out.write(c_int64_(value.object_id))
	elif inspect.isclass(type_) and issubclass(type_, Serializable):
		type_.serialize(value, out)
	elif issubclass(type_, Sequence):
		length_type, value_type = type_.__args__
		out.write(length_type(len(value)))
		for i in value:
			_game_message_serialize(out, value_type, i)
	elif issubclass(type_, Mapping):
		length_type, key_type, value_type = type_.__args__
		out.write(length_type(len(value)))
		for k, v in value.items():
			_game_message_serialize(out, key_type, k)
			_game_message_serialize(out, value_type, v)
	else:
		raise TypeError(type_)

broadcast = _send_game_message("broadcast")
single = _send_game_message("single")

from .components.ai import BaseCombatAIComponent
from .components.bouncer import BouncerComponent
from .components.char import CharacterComponent
from .components.collectible import CollectibleComponent
from .components.comp107 import Comp107Component
from .components.comp108 import Comp108Component
from .components.component import Component
from .components.destructible import DestructibleComponent
from .components.exhibit import ExhibitComponent
from .components.inventory import InventoryComponent, ItemComponent
from .components.launchpad import LaunchpadComponent
from .components.minigame import MinigameComponent
from .components.mission import MissionNPCComponent
from .components.model import ModelComponent
from .components.modular_build import ModularBuildComponent
from .components.moving_platform import MovingPlatformComponent
from .components.pet import PetComponent
from .components.physics import ControllablePhysicsComponent, PhantomPhysicsComponent, PhysicsComponent, RigidBodyPhantomPhysicsComponent, SimplePhysicsComponent, VehiclePhysicsComponent
from .components.property import PropertyEntranceComponent, PropertyManagementComponent, PropertyVendorComponent
from .components.racing_control import RacingControlComponent
from .components.rail import RailActivatorComponent
from .components.rebuild import RebuildComponent
from .components.render import RenderComponent
from .components.script import ScriptComponent
from .components.scripted_activity import ScriptedActivityComponent
from .components.skill import SkillComponent
from .components.spawner import SpawnerComponent
from .components.stats import StatsSubcomponent
from .components.switch import SwitchComponent
from .components.trigger import TriggerComponent
from .components.vendor import VendorComponent

component: Dict[int, Tuple[Type[Component], ...]] = OrderedDict()
component[108] = Comp108Component,
component[1] = ControllablePhysicsComponent,
component[3] = SimplePhysicsComponent,
component[20] = RigidBodyPhantomPhysicsComponent,
component[30] = VehiclePhysicsComponent,
component[40] = PhantomPhysicsComponent,
component[7] = DestructibleComponent, StatsSubcomponent
component[23] = StatsSubcomponent, CollectibleComponent
component[4] = CharacterComponent,
component[12] = ModularBuildComponent,
component[17] = InventoryComponent,
component[26] = PetComponent,
component[5] = ScriptComponent,
component[71] = RacingControlComponent,
component[9] = SkillComponent,
component[11] = ItemComponent,
component[60] = BaseCombatAIComponent,
component[48] = StatsSubcomponent, RebuildComponent
component[25] = MovingPlatformComponent,

component[73] = MissionNPCComponent, # belongs to the other nonserialized components below but is moved up to have higher priority than VendorComponent

component[49] = SwitchComponent,
component[16] = VendorComponent,
component[6] = BouncerComponent,
component[39] = ScriptedActivityComponent,
component[75] = ExhibitComponent,
component[42] = ModelComponent,
component[2] = RenderComponent,
component[107] = Comp107Component,

component[10] = SpawnerComponent,
component[43] = PropertyEntranceComponent,
component[45] = PropertyManagementComponent,
component[50] = MinigameComponent,
component[65] = PropertyVendorComponent,
component[67] = LaunchpadComponent,
component[104] = RailActivatorComponent,

component_order = list(component.keys())
