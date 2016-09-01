import importlib
from collections import OrderedDict

from persistent import Persistent

from .bitstream import BitStream, c_bit, c_float, c_int, c_int64, c_ubyte, c_uint, c_ushort
from .components.ai import BaseCombatAIComponent
from .components.bouncer import BouncerComponent
from .components.char import CharacterComponent
from .components.collectible import CollectibleComponent
from .components.comp108 import Comp108Component
from .components.destructible import DestructibleComponent
from .components.inventory import InventoryComponent
from .components.launchpad import LaunchpadComponent
from .components.mission import MissionNPCComponent, MissionState, TaskType
from .components.modular_build import ModularBuildComponent
from .components.moving_platform import MovingPlatformComponent
from .components.pet import PetComponent
from .components.physics import ControllablePhysicsComponent, PhantomPhysicsComponent, RigidBodyPhantomPhysicsComponent, SimplePhysicsComponent, VehiclePhysicsComponent
from .components.property import PropertyEntranceComponent, PropertyManagementComponent, PropertyVendorComponent
from .components.rail import RailActivatorComponent
from .components.rebuild import RebuildComponent
from .components.render import RenderComponent
from .components.script import ScriptComponent
from .components.skill import SkillComponent
from .components.spawner import SpawnerComponent
from .components.stats import StatsSubcomponent
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
component[60] = BaseCombatAIComponent,
component[48] = StatsSubcomponent, RebuildComponent
component[25] = MovingPlatformComponent,

component[73] = MissionNPCComponent, # belongs to the other nonserialized components below but is moved up to have higher priority than VendorComponent

component[16] = VendorComponent,
component[6] = BouncerComponent,
component[2] = RenderComponent,

component[10] = SpawnerComponent,
component[43] = PropertyEntranceComponent,
component[45] = PropertyManagementComponent,
component[65] = PropertyVendorComponent,
component[67] = LaunchpadComponent,
component[104] = RailActivatorComponent,

component_order = list(component.keys())

def restore_template(*args):
	cls = Template(*args)
	return cls.__new__(cls)

def Template(lot_, conn=None, comps=None, custom_script=None):
	"""Function acting as metaclass to generate the right type of Template based on the LOT."""
	if comps is None:
		comps = OrderedDict()

		comp_ids = list(conn.root.components_registry[lot_])
		if custom_script is not None:
			# remove any previous script and add the new script
			for comp in comp_ids:
				if comp[0] == 5:
					comp_ids.remove(comp)
					break
			comp_ids.append((5, None))

		for component_type, component_id in sorted(comp_ids, key=lambda x: component_order.index(x[0]) if x[0] in component_order else 99999):
			if component_type == 5:
				if component_id is None:
					if custom_script != "":
						script = importlib.import_module("luserver.scripts."+custom_script)
						comp = script.ScriptComponent,
					else:
						comp = ScriptComponent,
				elif component_id in conn.root.script_component:
					script = importlib.import_module("luserver.scripts."+conn.root.script_component[component_id])
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

		comps = [(k, v) for k, v in comps.items()]

	class GameObjectTemplate(*(i[0] for i in comps)):
		lot = lot_

		def __reduce__(self):
			return restore_template, (lot_, None, comps), self.__dict__

		def __setattr__(self, name, value):
			self.attr_changed(name)
			super().__setattr__(name, value)

		def __init__(self, object_id, server, set_vars={}):
			self._flags = {}
			self._flags["parent_flag"] = "related_objects_flag"
			self._flags["children_flag"] = "related_objects_flag"
			self._flags["parent"] = "parent_flag"
			self._flags["children"] = "children_flag"
			self._serialize = False
			self._v_server = server
			self.object_id = object_id
			self.name = ""
			self.spawner = None
			self.spawner_waypoint_index = 0
			self.groups = ()
			self.parent = None
			self.children = []

			vars(self).update(set_vars)

			for comp, comp_id in comps:
				comp.__init__(self, comp_id)

		def __repr__(self):
			return "<GameObject '%s', %i, %i>" % (self.name, self.object_id, self.lot)

		def attr_changed(self, name):
			"""In case an attribute change is not registered by __setattr__ (like setting an attribute of an attribute), manually register the change by calling this. Without a registered change changes will not be broadcast to clients!"""
			if hasattr(self, "_flags") and name in self._flags:
				setattr(self, self._flags[name], hasattr(self, name))
				self._serialize = True

		def send_construction(self):
			out = BitStream()
			out.write(c_int64(self.object_id))
			out.write(c_int(self.lot))
			out.write(self.name, char_size=2, length_type=c_ubyte)

			out.write(bytes(4)) # time since created on server?
			out.write(c_bit(False))
			out.write(c_bit(False))
			out.write(c_bit(self.spawner is not None))
			if self.spawner is not None:
				out.write(c_int64(self.spawner.object_id))
			out.write(c_bit(self.spawner is not None))
			if self.spawner is not None:
				out.write(c_uint(self.spawner_waypoint_index))

			out.write(c_bit(False))
			out.write(c_bit(False))
			out.write(c_bit(False))

			out.write(self.serialize(True))
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

			for comp, _ in comps:
				comp.serialize(self, out, is_creation)
			return out

		def on_destruction(self):
			if self.parent is not None:
				self._v_server.game_objects[self.parent].children.remove(self.object_id)
				self._v_server.game_objects[self.parent].children_flag = True

			for child in self.children:
				self._v_server.destruct(self._v_server.game_objects[child])

			for comp, _ in comps:
				if hasattr(comp, "on_destruction"):
					comp.on_destruction(self)

			del self._v_server.game_objects[self.object_id]

		def play_emote(self, address, emote_id:c_int, target_id:c_int64):
			# are we sure this message is not-char-component-specific?
			self._v_server.send_game_message(self.emote_played, emote_id, target_id, broadcast=True)
			# update missions that have the use of this emote as requirement
			if target_id:
				for mission in self.missions:
					if mission.state == MissionState.Active:
						for task in mission.tasks:
							if task.type == TaskType.UseEmote and emote_id in task.parameter and task.target == self._v_server.game_objects[target_id].lot:
								mission.increment_task(task, self)


		def play_animation(self, address, animation_id:"wstr"=None, expect_anim_to_exist:c_bit=True, play_immediate:c_bit=None, trigger_on_complete_msg:c_bit=False, priority:c_float=2, f_scale:c_float=1):
			pass

		def emote_played(self, address, emote_id:c_int, target_id:c_int64):
			pass

		def fire_event_client_side(self, address, args:"wstr"=None, obj:c_int64=None, param1:c_int64=0, param2:c_int=-1, sender_id:c_int64=None):
			pass

	return GameObjectTemplate

class PlayerObject(Template(1, comps=((ControllablePhysicsComponent, 1), (DestructibleComponent, 4), (StatsSubcomponent, 4), (CharacterComponent, 0), (InventoryComponent, 0), (SkillComponent, 0))), Persistent): # doesn't seem to work else
	def __init__(self, object_id, server):
		type(self).__bases__[0].__init__(self, object_id, server)
		Persistent.__init__(self)

	def __setattr__(self, name, value):
		if not self._p_setattr(name, value):
			super().__setattr__(name, value)
			self._p_changed = True
