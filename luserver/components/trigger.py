import functools
import logging
from typing import Sequence, Tuple

from pyraknet.bitstream import c_bit, WriteStream
from ..game_object import Config, GameObject
from ..world import server
from ..math.vector import Vector3
from .component import Component
from .mission import TaskType
from .physics import PhysicsEffect

log = logging.getLogger(__name__)

class TriggerComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.trigger = self
		if "trigger_events" in set_vars:
			for event_name, commands in set_vars["trigger_events"].items():
				setattr(self, event_name, functools.partial(self.on_event_process_commands, commands))

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(False))

	def on_event_process_commands(self, commands: Sequence[Tuple[str, str, Sequence[str]]], *eventargs) -> None:
		for command_name, target, args in commands:
			if command_name == "CastSkill":
				assert target == "target"
				player = eventargs[0]
				player.skill.cast_skill(int(args[0]))
			elif command_name == "fireEvent":
				assert target[0] == "objGroup"
				objs = server.get_objects_in_group(target[1])
				for obj in objs:
					if hasattr(obj, "script"):
						obj.script.fire_event(args[0])

			elif command_name == "SetPhysicsVolumeEffect":
				assert target == "self", target
				self.object.physics.physics_effect_active = True
				self.object.physics.physics_effect_type = PhysicsEffect[args[0]]
				self.object.physics.physics_effect_amount = float(args[1])
				if self.object.physics.physics_effect_type == PhysicsEffect.Push:
					self.object.physics.physics_effect_direction = Vector3(float(args[2]), float(args[3]), float(args[4]))*self.object.physics.physics_effect_amount

			elif command_name == "updateMission":
				assert target == "target", target
				assert args[0:4] == ["exploretask","1","1","1"], args[0:4]
				player = eventargs[0]
				player.char.update_mission_task(TaskType.Discover, args[4])

			else:
				log.error("command %s not implemented", command_name)
