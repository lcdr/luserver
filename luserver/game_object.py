import asyncio
import importlib
import logging
from collections import OrderedDict

from persistent import Persistent

from .ldf import LDF
from .bitstream import BitStream, c_bit, c_float, c_int, c_int64, c_ubyte, c_uint, c_ushort

log = logging.getLogger(__name__)

class GameObject:
	def __setattr__(self, name, value):
		self.attr_changed(name)
		super().__setattr__(name, value)

	def __init__(self, server, lot, object_id, set_vars={}):
		self._v_server = server
		self._flags = {}
		self._flags["parent_flag"] = "related_objects_flag"
		self._flags["children_flag"] = "related_objects_flag"
		self._flags["parent"] = "parent_flag"
		self._flags["children"] = "children_flag"
		self._serialize_scheduled = True
		self.lot = lot
		self.object_id = object_id
		self.name = set_vars.get("name", "")
		self.config = set_vars.get("config", LDF())

		if "spawner" in set_vars:
			self.spawner_object = set_vars["spawner"]
			self.spawner_waypoint_index = set_vars["spawner"].spawner.last_waypoint_index
		else:
			self.spawner_object = None
			self.spawner_waypoint_index = 0

		self.scale = set_vars.get("scale", 1)

		if "parent" in set_vars and set_vars["parent"].object_id in self._v_server.game_objects:
			self.parent = set_vars["parent"].object_id
			set_vars["parent"].children.append(self.object_id)
			set_vars["parent"].attr_changed("children")
		else:
			self.parent = None

		self.children = []
		self.groups = set_vars.get("groups", ())
		if "respawn_name" in set_vars:
			self.respawn_name = set_vars["respawn_name"]
		if "primitive_model_type" in set_vars:
			self.primitive_model_type = set_vars["primitive_model_type"]
		if "primitive_model_scale" in set_vars:
			self.primitive_model_scale = set_vars["primitive_model_scale"]
		self.components = []

		comps = OrderedDict()

		comp_ids = list(self._v_server.db.components_registry[self.lot])
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
					script = importlib.import_module("luserver.scripts."+set_vars["custom_script"])
					comp = script.ScriptComponent,
				elif component_id is not None and component_id in self._v_server.db.script_component:
					script = importlib.import_module("luserver.scripts."+self._v_server.db.script_component[component_id])
					comp = script.ScriptComponent,
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

	def __repr__(self):
		return "<GameObject \"%s\", %i, %i>" % (self.name, self.object_id, self.lot)

	def attr_changed(self, name):
		"""In case an attribute change is not registered by __setattr__ (like setting an attribute of an attribute), manually register the change by calling this. Without a registered change changes will not be broadcast to clients!"""
		if hasattr(self, "_flags") and name in self._flags:
			setattr(self, self._flags[name], hasattr(self, name))
			self.signal_serialize()

	def signal_serialize(self):
		if not self._serialize_scheduled:
			self.call_later(0, self.do_serialize)
			self._serialize_scheduled = True

	def do_serialize(self):
		self._v_server.serialize(self)
		self._serialize_scheduled = False

	def send_construction(self):
		out = BitStream()
		out.write(c_int64(self.object_id))
		out.write(c_int(self.lot))
		out.write(self.name, length_type=c_ubyte)

		out.write(bytes(4)) # time since created on server?
		out.write(c_bit(self.config))
		if self.config:
			out.write(self.config.to_bitstream())
		out.write(c_bit(hasattr(self, "trigger")))
		out.write(c_bit(self.spawner_object is not None))
		if self.spawner_object is not None:
			out.write(c_int64(self.spawner_object.object_id))
		out.write(c_bit(self.spawner_object is not None))
		if self.spawner_object is not None:
			out.write(c_uint(self.spawner_waypoint_index))
		out.write(c_bit(self.scale != 1))
		if self.scale != 1:
			out.write(c_float(self.scale))
		out.write(c_bit(False))
		out.write(c_bit(False))

		out.write(self.serialize(True))

		self._serialize_scheduled = False
		return out

	def serialize(self, is_creation=False):
		out = BitStream()
		out.write(c_bit(self.related_objects_flag or (is_creation and (self.parent is not None or self.children))))
		if self.related_objects_flag or (is_creation and (self.parent is not None or self.children)):
			out.write(c_bit(self.parent_flag or (is_creation and self.parent is not None)))
			if self.parent_flag or (is_creation and self.parent is not None):
				if self.parent is not None:
					out.write(c_int64(self.parent))
				else:
					out.write(c_int64(0))
				out.write(c_bit(False))
				self.parent_flag = False

			out.write(c_bit(self.children_flag or (is_creation and self.children)))
			if self.children_flag or (is_creation and self.children):
				out.write(c_ushort(len(self.children)))
				for child in self.children:
					out.write(c_int64(child))
				self.children_flag = False

			self.related_objects_flag = False

		for comp in self.components:
			comp.serialize(out, is_creation)
		return out

	def on_destruction(self):
		self._serialize_scheduled = True
		if self.parent is not None:
			self._v_server.game_objects[self.parent].children.remove(self.object_id)
			self._v_server.game_objects[self.parent].attr_changed("children")

		for child in self.children.copy():
			self._v_server.destruct(self._v_server.game_objects[child])

		if self.object_id in self._v_server.callback_handles:
			for handle in self._v_server.callback_handles[self.object_id].values():
				handle.cancel()
			del self._v_server.callback_handles[self.object_id]

		self.handle("on_destruction", silent=True)

		del self._v_server.game_objects[self.object_id]

	def handlers(self, func_name, silent=False):
		"""
		Return matching component handlers for a function.
		Handlers are returned in serialization order, except for ScriptComponent, which is moved to the bottom of the list.
		"""
		handlers = []
		script_handler = None
		for comp in self.components:
			if hasattr(comp, func_name):
				handler = getattr(comp, func_name)
				if isinstance(comp, ScriptComponent):
					script_handler = handler
				else:
					handlers.append(handler)
		if script_handler is not None:
			handlers.append(script_handler)

		if not handlers and not silent:
			log.info("Object %s has no handlers for %s", self, func_name)

		return handlers

	def handle(self, func_name, *args, silent=False, **kwargs):
		"""
		Calls component handlers for a function. See handlers() for the order of handlers.
		If a handler returns True, it's assumed that the handler has sufficiently handled the event and no further handlers will be called.
		"""
		for handler in self.handlers(func_name, silent):
			if handler(*args, **kwargs):
				break

	def send_game_message(self, handler_name, *args, **kwargs):
		"""For game messages with multiple handlers: call all the handlers but only send one message over the network."""
		handlers = self.handlers(handler_name)
		if not handlers:
			return

		send_handler = handlers[0]
		send_handler(*args, **kwargs)
		for handler in handlers[1:]:
			handler.__wrapped__(handler.__self__, *args, **kwargs)

	def call_later(self, delay, callback, *args):
		"""
		Call a callback in delay seconds. The callback's handle is recorded so that when the object is destructed all pending callbacks are automatically cancelled.
		Return the callback id to be used for cancel_callback.
		"""
		callback_id = self._v_server.last_callback_id
		self._v_server.callback_handles.setdefault(self.object_id, {})[callback_id] = asyncio.get_event_loop().call_later(delay, self._callback, callback_id, callback, *args)
		self._v_server.last_callback_id += 1
		return callback_id

	def _callback(self, callback_id, callback, *args):
		"""Execute a callback and delete the handle from the list because it won't be cancelled."""
		del self._v_server.callback_handles[self.object_id][callback_id]
		callback(*args)

	def cancel_callback(self, callback_id):
		"""Cancel a callback and delete the handle from the list."""
		if callback_id in self._v_server.callback_handles[self.object_id]:
			self._v_server.callback_handles[self.object_id][callback_id].cancel()
			del self._v_server.callback_handles[self.object_id][callback_id]

class PersistentObject(GameObject, Persistent): # possibly just make all game objects persistent?
	def __init__(self, server, lot, object_id, set_vars={}):
		GameObject.__init__(self, server, lot, object_id, set_vars)
		Persistent.__init__(self)

	def __setattr__(self, name, value):
		if not self._p_setattr(name, value):
			super().__setattr__(name, value)
			self._p_changed = True

from .components.ai import BaseCombatAIComponent
from .components.bouncer import BouncerComponent
from .components.char import CharacterComponent
from .components.collectible import CollectibleComponent
from .components.comp108 import Comp108Component
from .components.destructible import DestructibleComponent
from .components.exhibit import ExhibitComponent
from .components.inventory import InventoryComponent, ItemComponent
from .components.launchpad import LaunchpadComponent
from .components.mission import MissionNPCComponent
from .components.modular_build import ModularBuildComponent
from .components.moving_platform import MovingPlatformComponent
from .components.pet import PetComponent
from .components.physics import ControllablePhysicsComponent, PhantomPhysicsComponent, RigidBodyPhantomPhysicsComponent, SimplePhysicsComponent, VehiclePhysicsComponent
from .components.property import PropertyEntranceComponent, PropertyManagementComponent, PropertyVendorComponent
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

component = OrderedDict()
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
component[2] = RenderComponent,

component[10] = SpawnerComponent,
component[43] = PropertyEntranceComponent,
component[45] = PropertyManagementComponent,
component[65] = PropertyVendorComponent,
component[67] = LaunchpadComponent,
component[104] = RailActivatorComponent,

component_order = list(component.keys())
