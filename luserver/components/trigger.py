import functools

from ..bitstream import c_bit
from ..math.vector import Vector3
from .component import Component
from .physics import PhysicsEffect

class TriggerComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		if "trigger_events" in set_vars:
			for event_name, commands in set_vars["trigger_events"].items():
				setattr(self, event_name, functools.partial(self.on_event_process_commands, commands))

	def serialize(self, out, is_creation):
		out.write(c_bit(False))

	def on_event_process_commands(self, commands):
		for command_name, target, args in commands:
			assert target == "self", target
			if command_name == "SetPhysicsVolumeEffect":
				self.object.physics.physics_effect_type = PhysicsEffect[args[0]]
				self.object.physics.physics_effect_amount = float(args[1])
				if self.object.physics.physics_effect_type == PhysicsEffect.Push:
					self.object.physics.physics_effect_direction = Vector3(float(args[2]), float(args[3]), float(args[4]))*self.object.physics.physics_effect_amount
