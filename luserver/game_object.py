import asyncio
import importlib
import inspect
import logging
import re
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, cast, Dict, Generic, List, NewType, Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union
from typing import Mapping as Mapping_
from typing import Sequence as Sequence_

from mypy_extensions import TypedDict
from persistent import Persistent

from bitstream import c_bit, c_float, c_ubyte, c_ushort, ReadStream, Serializable, UnsignedIntStruct, WriteStream
from bitstream import c_int as c_int_
from bitstream import c_int64 as c_int64_
from bitstream import c_uint as c_uint_
from bitstream import c_uint64 as c_uint64_
from pyraknet.transports.abc import Connection
from pyraknet.replicamanager import Replica
from .amf3 import AMF3
from .bitstream import WriteStream as WriteStream_
from .ldf import LDF
from .messages import GameMessage, WorldClientMsg
from .world import server
from .math.quaternion import Quaternion
from .math.vector import Vector3

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

EA = cast(AMF3, E)
EB = cast(bool, E)
EBY = cast(bytes, E)
EF = cast(float, E)
EI = cast(int, E)
EL = cast(LDF, E)
ES = cast(str, E)
EV = cast(Vector3, E)

T = TypeVar("T", bound=UnsignedIntStruct)
U = TypeVar("U")
V = TypeVar("V")
W = TypeVar("W", bound=Union[float, bytes, str, c_int_, c_int64_, c_ubyte, c_uint_, c_uint64_, LDF])

class Sequence(Generic[T, U], Sequence_[U]):
	pass

class Mapping(Generic[T, U, V], Mapping_[U, V]):
	pass

class Config(TypedDict, total=False):
	active_on_load: bool
	activity_id: int
	attached_path: str
	collectible_id: int
	config: LDF
	custom_script: str
	groups: Sequence_[str]
	name: str
	num_to_maintain: int
	parent: "GameObject"
	position: Vector3
	primitive_model_type: int
	primitive_model_scale: Vector3
	rail_path: str
	rail_path_start: int
	rebuild_activator_position: Vector3
	rebuild_complete_time: float
	rebuild_smash_time: float
	respawn_data: Tuple[Vector3, Quaternion]
	respawn_name: str
	respawn_point_name: str
	respawn_time: int
	rotation: Quaternion
	scale: float
	script_vars: Dict[str, object]
	spawner: "SpawnerObject"
	spawner_name: str
	spawner_waypoints: Sequence_["Config"]
	spawntemplate: int
	spawn_net_on_smash: str
	transfer_world_id: int

class FlagObject:
	def __init__(self) -> None:
		self._flags: Dict[str, str] = {}

	def __setattr__(self, name: str, value: object) -> None:
		self.attr_changed(name)
		super().__setattr__(name, value)

	def attr_changed(self, name: str) -> None:
		"""In case an attribute change is not registered by __setattr__ (like setting an attribute of an attribute), manually register the change by calling this. Without a registered change changes will not be broadcast to clients!"""

	def flag(self, name: str, stream: WriteStream, additional_condition: bool=False) -> bool:
		"""
		This function can be used to simplify common conditional bitstream writes.
		Evaluate the expression of the attribute with the name "name" or the optional additional condition.
		Write this value as a bit to the bitstream stream.
		If the flag was True, set it to False.
		Return the expression.
		"""
		flag = getattr(self, name)
		condition = flag or additional_condition
		stream.write(c_bit(condition))
		if flag:
			setattr(self, name, False)
		return condition

class GameObject(Replica, FlagObject):
	def __init__(self, lot: int, object_id: ObjectID, set_vars: Config=None):
		FlagObject.__init__(self)
		if set_vars is None:
			set_vars = {}
		self._handlers: Dict[str, List[Callable[..., None]]] = {}
		self._flags = {
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

		comp_ids: List[Tuple[int, Optional[int]]] = list(server.db.components_registry[self.lot])
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

		for component_type, component_id in sorted(comp_ids, key=lambda x: _component_order.index(x[0]) if x[0] in _component_order else 99999):
			if component_type == 5:
				if "custom_script" in set_vars and set_vars["custom_script"] is not None:
					try:
						script = importlib.import_module("luserver.scripts."+set_vars["custom_script"])
						if not hasattr(script, "ScriptComponent"):
							raise RuntimeError("Scripts need to define a ScriptComponent")
						comp = script.ScriptComponent,
					except ModuleNotFoundError as e:
						log.warning(str(e))
						comp = ScriptComponent,
				elif component_id is not None and component_id in server.db.script_component:
					try:
						script = importlib.import_module("luserver.scripts."+server.db.script_component[component_id])
						if not hasattr(script, "ScriptComponent"):
							raise RuntimeError("Scripts need to define a ScriptComponent")
						comp = script.ScriptComponent,
					except ModuleNotFoundError as e:
						log.warning(str(e))
						comp = ScriptComponent,
				else:
					comp = ScriptComponent,
			elif component_type in _component:
				comp = _component[component_type]
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
		stream.write(c_bit(bool(self.config)))
		if self.config:
			stream.write(self.config.to_bytes())
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
		if self.flag("related_objects_flag", stream, is_creation and (self.parent is not None or self.children)):
			if self.flag("parent_flag", stream, is_creation and self.parent is not None):
				if self.parent is not None:
					stream.write(c_int64_(self.parent))
				else:
					stream.write(c_int64_(0))
				stream.write(c_bit(False))

			if self.flag("children_flag", stream, is_creation and self.children):
				stream.write(c_ushort(len(self.children)))
				for child in self.children:
					stream.write(c_int64_(child))

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

		self.handle("destruction", silent=True)

		del server.game_objects[self.object_id]

	def add_handler(self, event_name: str, handler: Callable[..., None]) -> None:
		self._handlers.setdefault(event_name, []).append(handler)

	def remove_handler(self, event_name: str, handler: Callable[..., None]) -> None:
		if event_name not in self._handlers:
			return
		if handler in self._handlers[event_name]:
			self._handlers[event_name].remove(handler)

	def handlers(self, event_name: str, silent: bool=False) -> Sequence_[Callable]:
		"""Return matching handlers for an event."""
		if event_name not in self._handlers:
			if not silent:
				log.info("Object %s has no handlers for %s", self, event_name)
			return []
		else:
			return self._handlers[event_name]

	def handle(self, event_name: str, *args: Any, silent=False, **kwargs: Any) -> None:
		"""
		Calls handlers for an event.
		If a handler returns True, it's assumed that the handler has sufficiently handled the event and no further handlers will be called.
		"""
		for handler in self.handlers(event_name, silent):
			if handler(*args, **kwargs):
				break

	def call_later(self, delay: float, callback: Callable[..., None], *args: Any) -> CallbackID:
		"""
		Call a callback in delay seconds. The callback's handle is recorded so that when the object is destructed all pending callbacks are automatically cancelled.
		Return the callback id to be used for cancel_callback.
		"""
		callback_id = server.last_callback_id
		server.callback_handles.setdefault(self.object_id, {})[callback_id] = asyncio.get_event_loop().call_later(delay, self._callback, callback_id, callback, *args)
		server.last_callback_id += 1
		return callback_id

	def _callback(self, callback_id: CallbackID, callback: Callable[..., None], *args: Any) -> None:
		"""Execute a callback and delete the handle from the list because it won't be cancelled."""
		del server.callback_handles[self.object_id][callback_id]
		callback(*args)

	def cancel_callback(self, callback_id: CallbackID) -> None:
		"""Cancel a callback and delete the handle from the list."""
		if callback_id in server.callback_handles[self.object_id]:
			server.callback_handles[self.object_id][callback_id].cancel()
			del server.callback_handles[self.object_id][callback_id]

	def on_game_message(self, message: ReadStream, conn: Connection) -> None:
		message_id = message.read(c_ushort)
		try:
			message_name = GameMessage(message_id).name
		except ValueError:
			return
		event_name = re.sub("(?!^)([A-Z])", r"_\1", message_name).lower()

		handlers = self.handlers(event_name)
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

		player = server.accounts[conn].selected_char()
		for handler in handlers:
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

	def _game_message_deserialize(self, message: ReadStream, type_: Type[W]) -> W:
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
		if issubclass(type_, GameObject) or issubclass(type_, Player):
			obj_id = message.read(c_int64_)
			if obj_id == 0:
				return None
			return server.get_object(obj_id)
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

EO = cast(GameObject, E)

# these are for static typing and shouldn't actually be used

class _SpecialObjectMeta(type):
	def __instancecheck__(self, instance: object) -> bool:
		if not isinstance(instance, GameObject):
			return False
		for attr in self.__annotations__:
				if not hasattr(instance, attr):
					return False
		return True

class _SpecialObject(GameObject, metaclass=_SpecialObjectMeta):
	pass

class PhysicsObject(_SpecialObject):
	physics: "PhysicsComponent"

class ControllableObject(PhysicsObject):
	physics: "Controllable"

class RenderObject(_SpecialObject):
	render: "RenderComponent"

class ScriptObject(_SpecialObject):
	script: "ScriptComponent"

class StatsObject(PhysicsObject, RenderObject): # safe to assume that a stats object is also a physics object - only 2 entries (6622, 6908) in the database didn't match, and those were test objects
	stats: "StatsSubcomponent"

class DestructibleObject(StatsObject):
	destructible: "DestructibleComponent"

class SpawnerObject(_SpecialObject):
	spawner: "SpawnerComponent"

class VendorObject(_SpecialObject):
	vendor: "VendorComponent"

class Player(ControllableObject, DestructibleObject, Persistent):
	char: "CharacterComponent"
	inventory: "InventoryComponent"
	skill: "SkillComponent"

	def __init__(self, object_id: ObjectID):
		GameObject.__init__(self, 1, object_id)
		Persistent.__init__(self)

	def __setattr__(self, name: str, value: object) -> None:
		if not self._p_setattr(name, value):
			super().__setattr__(name, value)
			self._p_changed = True

EP = cast(Player, E)
OBJ_NONE = cast(Player, None)

X = TypeVar("X", bound=Callable)

def _send_game_message(mode: str) -> Callable[[X], X]:
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
	def decorator(func: X) -> X:
		from .world import server

		@wraps(func)
		def wrapper(self, *args: Any, **kwargs: Any) -> Any:
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
				exclude = []
				if player is not None:
					exclude.append(player.char.data()["conn"])
				server.broadcast(out, exclude=exclude)
			elif mode == "single":
				if player is None:
					player = self.object
				player.char.data()["conn"].send(out)
			if func.__name__ not in ("drop_client_loot", "script_network_var_update"): # todo: don't hardcode this
				if len(bound_args.arguments) > 1:
					log.debug(", ".join("%s=%s" % (key, value) for key, value in list(bound_args.arguments.items())[1:]))
			return func(self, *args, **kwargs)
		return wrapper
	return decorator


def _game_message_serialize(out: WriteStream, type_: Type[W], value: W) -> None:
	if type_ == float:
		out.write(c_float(value))
	elif type_ == bytes:
		out.write(value, length_type=c_uint_)
	elif type_ == str:
		out.write(value, length_type=c_uint_)
	elif hasattr(type_, "__origin__") and type_.__origin__ is not None:
		if type_.__origin__ == Sequence:
			length_type, value_type = type_.__args__
			out.write(length_type(len(value)))
			for i in value:
				_game_message_serialize(out, value_type, i)
		elif type_.__origin__ == Mapping:
			length_type, key_type, value_type = type_.__args__
			out.write(length_type(len(value)))
			for k, v in value.items():
				_game_message_serialize(out, key_type, k)
				_game_message_serialize(out, value_type, v)
		else:
			raise TypeError(type_)
	elif issubclass(type_, (c_int_, c_int64_, c_ubyte, c_uint_, c_uint64_)):
		out.write(type_(value))
	elif type_ == LDF:
		ldf_text = value.to_str()
		out.write(ldf_text, length_type=c_uint_)
		if ldf_text:
			out.write(bytes(2)) # for some reason has a null terminator
	elif issubclass(type_, GameObject) or issubclass(type_, Player):
		if value is OBJ_NONE:
			out.write(c_int64_(0))
		else:
			out.write(c_int64_(value.object_id))
	elif inspect.isclass(type_) and issubclass(type_, Serializable):
		type_.serialize(value, out)
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
from .components.physics import Controllable, ControllablePhysicsComponent, PhantomPhysicsComponent, PhysicsComponent, RigidBodyPhantomPhysicsComponent, SimplePhysicsComponent, VehiclePhysicsComponent
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

_component: Dict[int, Tuple[Type[Component], ...]] = OrderedDict()
_component[108] = Comp108Component,
_component[1] = ControllablePhysicsComponent,
_component[3] = SimplePhysicsComponent,
_component[20] = RigidBodyPhantomPhysicsComponent,
_component[30] = VehiclePhysicsComponent,
_component[40] = PhantomPhysicsComponent,
_component[7] = DestructibleComponent, StatsSubcomponent
_component[23] = StatsSubcomponent, CollectibleComponent
_component[4] = CharacterComponent,
_component[12] = ModularBuildComponent,
_component[17] = InventoryComponent,
_component[26] = PetComponent,
_component[5] = ScriptComponent,
_component[71] = RacingControlComponent,
_component[9] = SkillComponent,
_component[11] = ItemComponent,
_component[60] = BaseCombatAIComponent,
_component[48] = StatsSubcomponent, RebuildComponent
_component[25] = MovingPlatformComponent,

_component[73] = MissionNPCComponent, # belongs to the other nonserialized components below but is moved up to have higher priority than VendorComponent

_component[49] = SwitchComponent,
_component[16] = VendorComponent,
_component[6] = BouncerComponent,
_component[39] = ScriptedActivityComponent,
_component[75] = ExhibitComponent,
_component[42] = ModelComponent,
_component[2] = RenderComponent,
_component[107] = Comp107Component,

_component[10] = SpawnerComponent,
_component[43] = PropertyEntranceComponent,
_component[45] = PropertyManagementComponent,
_component[50] = MinigameComponent,
_component[65] = PropertyVendorComponent,
_component[67] = LaunchpadComponent,
_component[104] = RailActivatorComponent,

_component_order = list(_component.keys())
