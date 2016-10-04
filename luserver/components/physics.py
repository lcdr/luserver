import enum

from ..bitstream import c_bit, c_float, c_int64, c_ubyte, c_uint
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .component import Component

class PhysicsComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.physics = self
		self._flags["position"] = "physics_data_flag"
		self._flags["rotation"] = "physics_data_flag"
		self.position = Vector3()
		self.rotation = Quaternion()
		if "position" in set_vars:
			self.position.update(set_vars["position"])
		if "rotation" in set_vars:
			self.rotation.update(set_vars["rotation"])

class Controllable(PhysicsComponent):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._flags["on_ground"] = "physics_data_flag"
		self._flags["unknown_bool"] = "physics_data_flag"
		self._flags["velocity_flag"] = "physics_data_flag"
		self._flags["velocity"] = "velocity_flag"
		self._flags["angular_velocity_flag"] = "physics_data_flag"
		self._flags["angular_velocity"] = "angular_velocity_flag"
		self._flags["unknown_flag"] = "physics_data_flag"
		self._flags["unknown_object_id"] = "unknown_flag"
		self._flags["unknown_float3"] = "unknown_flag"
		self._flags["deeper_unknown_flag"] = "unknown_flag"
		self._flags["deeper_unknown_float3"] = "deeper_unknown_flag"
		self.on_ground = True
		self.unknown_bool = False
		self.velocity = Vector3()
		self.angular_velocity = 0, 0, 0
		self.unknown_object_id = 0
		self.unknown_float3 = 0, 0, 0
		self.deeper_unknown_float3 = 0, 0, 0

	def serialize(self, out, is_creation):
		out.write(c_bit(self.physics_data_flag or is_creation))
		if self.physics_data_flag or is_creation:
			out.write(c_float(self.position.x))
			out.write(c_float(self.position.y))
			out.write(c_float(self.position.z))

			out.write(c_float(self.rotation.x))
			out.write(c_float(self.rotation.y))
			out.write(c_float(self.rotation.z))
			out.write(c_float(self.rotation.w))

			out.write(c_bit(self.on_ground))
			out.write(c_bit(self.unknown_bool))

			out.write(c_bit(self.velocity_flag))
			if self.velocity_flag:
				out.write(c_float(self.velocity.x))
				out.write(c_float(self.velocity.y))
				out.write(c_float(self.velocity.z))
				self.velocity_flag = False

			out.write(c_bit(self.angular_velocity_flag))
			if self.angular_velocity_flag:
				out.write(c_float(self.angular_velocity[0]))
				out.write(c_float(self.angular_velocity[1]))
				out.write(c_float(self.angular_velocity[2]))
				self.angular_velocity_flag = False

			out.write(c_bit(self.unknown_flag))
			if self.unknown_flag:
				out.write(c_int64(self.unknown_object_id))
				out.write(c_float(self.unknown_float3[0]))
				out.write(c_float(self.unknown_float3[1]))
				out.write(c_float(self.unknown_float3[2]))

				out.write(c_bit(self.deeper_unknown_flag))
				if self.deeper_unknown_flag:
					out.write(c_float(self.deeper_unknown_float3[0]))
					out.write(c_float(self.deeper_unknown_float3[1]))
					out.write(c_float(self.deeper_unknown_float3[2]))
					self.deeper_unknown_flag = False

				self.unknown_flag = False
			if not is_creation:
				out.write(c_bit(False))
			self.physics_data_flag = False

class ControllablePhysicsComponent(Controllable):
	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))

		out.write(c_bit(False))
		out.write(c_bit(False))
		out.write(c_bit(False))
		super().serialize(out, is_creation)

class SimplePhysicsComponent(PhysicsComponent):
	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))
			out.write(c_float(0))
		out.write(c_bit(False))
		out.write(c_bit(False))
		out.write(c_bit(self.physics_data_flag or is_creation))
		if self.physics_data_flag or is_creation:
			out.write(c_float(self.position.x))
			out.write(c_float(self.position.y))
			out.write(c_float(self.position.z))
			out.write(c_float(self.rotation.x))
			out.write(c_float(self.rotation.y))
			out.write(c_float(self.rotation.z))
			out.write(c_float(self.rotation.w))
			self.physics_data_flag = False

class RigidBodyPhantomPhysicsComponent(PhysicsComponent):
	def serialize(self, out, is_creation):
		out.write(c_bit(self.physics_data_flag or is_creation))
		if self.physics_data_flag or is_creation:
			out.write(c_float(self.position.x))
			out.write(c_float(self.position.y))
			out.write(c_float(self.position.z))
			out.write(c_float(self.rotation.x))
			out.write(c_float(self.rotation.y))
			out.write(c_float(self.rotation.z))
			out.write(c_float(self.rotation.w))
			self.physics_data_flag = False

class VehiclePhysicsComponent(Controllable):
	def serialize(self, out, is_creation):
		super().serialize(out, is_creation)
		if is_creation:
			out.write(c_ubyte(0))
			out.write(c_bit(False))
		out.write(c_bit(False))

class PhysicsEffect(enum.IntEnum):
	Push = 0
	Attract = 1
	Repulse = 2
	Gravity = 3
	Friction = 4

class PhantomPhysicsComponent(PhysicsComponent):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._flags["physics_effect_type"] = "physics_effect_flag"
		self._flags["physics_effect_amount"] = "physics_effect_flag"
		self._flags["physics_effect_direction"] = "physics_effect_flag"
		self.physics_effect_type = 0
		self.physics_effect_amount = 0
		self.physics_effect_direction = Vector3()

	def serialize(self, out, is_creation):
		out.write(c_bit(self.physics_data_flag or is_creation))
		if self.physics_data_flag or is_creation:
			out.write(c_float(self.position.x))
			out.write(c_float(self.position.y))
			out.write(c_float(self.position.z))
			out.write(c_float(self.rotation.x))
			out.write(c_float(self.rotation.y))
			out.write(c_float(self.rotation.z))
			out.write(c_float(self.rotation.w))
			self.physics_data_flag = False

		out.write(c_bit((is_creation and self.physics_effect_amount != 0) or self.physics_effect_flag))
		if (is_creation and self.physics_effect_amount != 0) or self.physics_effect_flag:
			out.write(c_bit(True))
			out.write(c_uint(self.physics_effect_type))
			out.write(c_float(self.physics_effect_amount))
			out.write(c_bit(False))
			out.write(c_bit(True))
			out.write(c_float(self.physics_effect_direction.x))
			out.write(c_float(self.physics_effect_direction.y))
			out.write(c_float(self.physics_effect_direction.z))
			self.physics_effect_flag = False
