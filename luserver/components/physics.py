from ..bitstream import c_bit, c_float, c_int64, c_ubyte
from ..math.quaternion import Quaternion
from ..math.vector import Vector3

class Controllable:
	def __init__(self, comp_id):
		self._flags["position"] = "transform_data_flag"
		self._flags["rotation"] = "transform_data_flag"
		self._flags["on_ground"] = "transform_data_flag"
		self._flags["unknown_bool"] = "transform_data_flag"
		self._flags["velocity_flag"] = "transform_data_flag"
		self._flags["velocity"] = "velocity_flag"
		self._flags["angular_velocity_flag"] = "transform_data_flag"
		self._flags["angular_velocity"] = "angular_velocity_flag"
		self._flags["unknown_flag"] = "transform_data_flag"
		self._flags["unknown_object_id"] = "unknown_flag"
		self._flags["unknown_float3"] = "unknown_flag"
		self._flags["deeper_unknown_flag"] = "unknown_flag"
		self._flags["deeper_unknown_float3"] = "deeper_unknown_flag"
		if not hasattr(self, "position"):
			self.position = Vector3()
		else:
			self.attr_changed("position")
		if not hasattr(self, "rotation"):
			self.rotation = Quaternion()
		else:
			self.attr_changed("rotation")
		self.on_ground = True
		self.unknown_bool = False
		self.velocity = Vector3()
		self.angular_velocity = 0, 0, 0
		self.unknown_object_id = 0
		self.unknown_float3 = 0, 0, 0
		self.deeper_unknown_float3 = 0, 0, 0

	def serialize(self, out, is_creation):
		out.write(c_bit(self.transform_data_flag or is_creation))
		if self.transform_data_flag or is_creation:
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
			self.transform_data_flag = False

class ControllablePhysicsComponent(Controllable):
	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))

		out.write(c_bit(False))
		out.write(c_bit(False))
		out.write(c_bit(False))
		super().serialize(out, is_creation)

class SimplePhysicsComponent:
	def __init__(self, comp_id):
		self._flags["position"] = "position_rotation_flag"
		self._flags["rotation"] = "position_rotation_flag"
		if not hasattr(self, "position"):
			self.position = Vector3()
		else:
			self.attr_changed("position")
		if not hasattr(self, "rotation"):
			self.rotation = Quaternion()
		else:
			self.attr_changed("rotation")

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))
			out.write(c_float(0))
		out.write(c_bit(False))
		out.write(c_bit(False))
		out.write(c_bit(self.position_rotation_flag or is_creation))
		if self.position_rotation_flag or is_creation:
			out.write(c_float(self.position.x))
			out.write(c_float(self.position.y))
			out.write(c_float(self.position.z))
			out.write(c_float(self.rotation.x))
			out.write(c_float(self.rotation.y))
			out.write(c_float(self.rotation.z))
			out.write(c_float(self.rotation.w))
			self.position_rotation_flag = False

class RigidBodyPhantomPhysicsComponent:
	def __init__(self, comp_id):
		self._flags["position"] = "position_rotation_flag"
		self._flags["rotation"] = "position_rotation_flag"
		if not hasattr(self, "position"):
			self.position = Vector3()
		else:
			self.attr_changed("position")
		if not hasattr(self, "rotation"):
			self.rotation = Quaternion()
		else:
			self.attr_changed("rotation")

	def serialize(self, out, is_creation):
		out.write(c_bit(self.position_rotation_flag or is_creation))
		if self.position_rotation_flag or is_creation:
			out.write(c_float(self.position.x))
			out.write(c_float(self.position.y))
			out.write(c_float(self.position.z))
			out.write(c_float(self.rotation.x))
			out.write(c_float(self.rotation.y))
			out.write(c_float(self.rotation.z))
			out.write(c_float(self.rotation.w))
			self.position_rotation_flag = False

class VehiclePhysicsComponent(Controllable):
	def serialize(self, out, is_creation):
		super().serialize(out, is_creation)
		if is_creation:
			out.write(c_ubyte(0))
			out.write(c_bit(False))
		out.write(c_bit(False))

class PhantomPhysicsComponent:
	def __init__(self, comp_id):
		self._flags["position"] = "position_rotation_flag"
		self._flags["rotation"] = "position_rotation_flag"
		if not hasattr(self, "position"):
			self.position = Vector3()
		else:
			self.attr_changed("position")
		if not hasattr(self, "rotation"):
			self.rotation = Quaternion()
		else:
			self.attr_changed("rotation")

	def serialize(self, out, is_creation):
		out.write(c_bit(self.position_rotation_flag or is_creation))
		if self.position_rotation_flag or is_creation:
			out.write(c_float(self.position.x))
			out.write(c_float(self.position.y))
			out.write(c_float(self.position.z))
			out.write(c_float(self.rotation.x))
			out.write(c_float(self.rotation.y))
			out.write(c_float(self.rotation.z))
			out.write(c_float(self.rotation.w))
			self.position_rotation_flag = False

		out.write(c_bit(False))
