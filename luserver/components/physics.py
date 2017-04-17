import enum
import math
import random

from ..bitstream import c_bit, c_float, c_int64, c_ubyte, c_uint
from ..ldf import LDF, LDFDataType
from ..messages import broadcast
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
		elif "parent" in set_vars:
			self.position.update(set_vars["parent"].physics.position)
		if "rotation" in set_vars:
			self.rotation.update(set_vars["rotation"])
		elif "parent" in set_vars:
			self.rotation.update(set_vars["parent"].physics.rotation)

	def on_destruction(self):
		if self.object in self.object._v_server.general.tracked_objects:
			del self.object._v_server.general.tracked_objects[self.object]

	def proximity_radius(self, radius):
		for comp in self.object.components:
			if hasattr(comp, "on_enter") or hasattr(comp, "on_exit"):
				self.object._v_server.general.tracked_objects[self.object] = CollisionSphere(self.object, radius)
				if self.object._v_server.get_objects_in_group("physics_debug_marker"):
					self.spawn_debug_marker()
				break

	def spawn_debug_marker(self):
		if self.object not in self.object._v_server.general.tracked_objects:
			return
		coll = self.object._v_server.general.tracked_objects[self.object]
		set_vars = {"groups": ("physics_debug_marker",), "parent": self.object}
		if isinstance(coll, AABB):
			config = LDF()
			config.ldf_set("primitiveModelType", LDFDataType.INT32, PrimitiveModelType.Cuboid)
			config.ldf_set("primitiveModelValueX", LDFDataType.FLOAT, coll.max.x-coll.min.x)
			config.ldf_set("primitiveModelValueY", LDFDataType.FLOAT, coll.max.y-coll.min.y)
			config.ldf_set("primitiveModelValueZ", LDFDataType.FLOAT, coll.max.z-coll.min.z)

			set_vars["position"] = Vector3((coll.min.x+coll.max.x)/2, coll.min.y, (coll.min.z+coll.max.z)/2)
			set_vars["config"] = config
			self.object._v_server.spawn_object(14510, set_vars)
		elif isinstance(coll, CollisionSphere):
			set_vars["position"] = coll.position
			set_vars["scale"] = math.sqrt(coll.sq_radius)/5
			self.object._v_server.spawn_object(6548, set_vars)


	# not really related to physics, but depends on physics and hasn't been conclusively associated with a component

	def drop_rewards(self, loot_matrix, currency_min, currency_max, owner):
		if currency_min is not None and currency_max is not None:
			currency = random.randint(currency_min, currency_max)
			owner.char.drop_client_loot(currency=currency, item_template=-1, loot_id=0, owner=owner, source_obj=self.object)

		if loot_matrix is not None:
			loot = owner.char.random_loot(loot_matrix)
			for lot in loot:
				self.drop_loot(lot, owner)

	def drop_loot(self, lot, owner):
		loot_position = Vector3(self.position.x+(random.random()-0.5)*20, self.position.y, self.position.z+(random.random()-0.5)*20)
		object_id = self.object._v_server.new_spawned_id()
		owner.char.dropped_loot[object_id] = lot
		owner.char.drop_client_loot(use_position=True, spawn_position=self.position, final_position=loot_position, currency=0, item_template=lot, loot_id=object_id, owner=owner, source_obj=self.object)

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

	# not sure which component this belongs to, putting it here for now
	@broadcast
	def lock_node_rotation(self, node_name:bytes=None):
		pass

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

MODEL_DIMENSIONS = {
	1656: (Vector3(-1, -1, -1), Vector3(1, 2, 1)), # imagination powerup
	4734: (Vector3(-5.2644, 0.0051, -0.5011), Vector3(4.7356, 5.0051, 0.4989)), # wall
	4956: (Vector3(-2, 0, -2), Vector3(2, 4, 2)), # AG monument switch,
	5633: (Vector3(-819.2, 0, -819.2), Vector3(819.2, 13.521, 819.2)), # death plane
	5652: (Vector3(-2.5, -2.5, -2.5), Vector3(2.5, 2.5, 2.5)), # cube
	10285: (Vector3(-7, 0, -6), Vector3(7, 3, 8)), # lego club ring
	12384: (Vector3(-0.5, -0.0002, -10.225), Vector3(0.5, 12.9755, 10.225))} # POI wall
MODEL_DIMENSIONS[5650] = MODEL_DIMENSIONS[4956] # AG monument switch rebuild
MODEL_DIMENSIONS[8419] = MODEL_DIMENSIONS[4734] # wall 2

class PrimitiveModelType:
	Cuboid = 1
	Cone = 2
	Cylinder = 3
	Sphere = 4

PRIMITIVE_DIMENSIONS = {
	PrimitiveModelType.Cuboid: (Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5)),
	PrimitiveModelType.Cylinder: (Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5))}

# currently for static objects only, does not handle position/rotation updates
class AABB: # axis aligned bounding box
	def __init__(self, obj):
		if hasattr(obj, "primitive_model_type"):
			rel_min = PRIMITIVE_DIMENSIONS[obj.primitive_model_type][0] * obj.primitive_model_scale
			rel_max = PRIMITIVE_DIMENSIONS[obj.primitive_model_type][1] * obj.primitive_model_scale
		else:
			rel_min = MODEL_DIMENSIONS[obj.lot][0] * obj.scale
			rel_max = MODEL_DIMENSIONS[obj.lot][1] * obj.scale

		rel_min = rel_min.rotate(obj.physics.rotation)
		rel_max = rel_max.rotate(obj.physics.rotation)

		# after rotation min and max are no longer necessarily the absolute min/max values

		rot_min = Vector3()
		rot_max = Vector3()

		rot_min.x = min(rel_min.x, rel_max.x)
		rot_min.y = min(rel_min.y, rel_max.y)
		rot_min.z = min(rel_min.z, rel_max.z)
		rot_max.x = max(rel_min.x, rel_max.x)
		rot_max.y = max(rel_min.y, rel_max.y)
		rot_max.z = max(rel_min.z, rel_max.z)

		self.min = obj.physics.position + rot_min
		self.max = obj.physics.position + rot_max

	def is_point_within(self, point):
		return self.min.x < point.x < self.max.x and \
		       self.min.y < point.y < self.max.y and \
		       self.min.z < point.z < self.max.z

# for dynamic objects
class CollisionSphere:
	def __init__(self, obj, radius):
		self.position = obj.physics.position
		self.sq_radius = radius**2

	def is_point_within(self, point):
		return self.position.sq_distance(point) < self.sq_radius

class PhysicsEffect(enum.IntEnum):
	Push = 0
	Attract = 1
	Repulse = 2
	Gravity = 3
	Friction = 4

class PhantomPhysicsComponent(PhysicsComponent):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self._flags["physics_effect_active"] = "physics_effect_flag"
		self._flags["physics_effect_type"] = "physics_effect_flag"
		self._flags["physics_effect_amount"] = "physics_effect_flag"
		self._flags["physics_effect_direction"] = "physics_effect_flag"
		self.physics_effect_active = False
		self.physics_effect_type = 0
		self.physics_effect_amount = 0
		self.physics_effect_direction = Vector3()
		if "respawn_data" in set_vars:
			self.respawn_data = set_vars["respawn_data"]

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

		out.write(c_bit(self.physics_effect_flag or is_creation))
		if self.physics_effect_flag or is_creation:
			out.write(c_bit(self.physics_effect_active))
			if self.physics_effect_active:
				out.write(c_uint(self.physics_effect_type))
				out.write(c_float(self.physics_effect_amount))
				out.write(c_bit(False))
				out.write(c_bit(True))
				out.write(c_float(self.physics_effect_direction.x))
				out.write(c_float(self.physics_effect_direction.y))
				out.write(c_float(self.physics_effect_direction.z))
			self.physics_effect_flag = False

	def on_startup(self):
		if self.object.lot in MODEL_DIMENSIONS or (hasattr(self.object, "primitive_model_type") and self.object.primitive_model_type in (PrimitiveModelType.Cuboid, PrimitiveModelType.Cylinder)):
			for comp in self.object.components:
				if comp is self:
					if not hasattr(self, "respawn_data"):
						continue
				if hasattr(comp, "on_enter") or hasattr(comp, "on_exit"):
					self.object._v_server.general.tracked_objects[self.object] = AABB(self.object)
					if self.object._v_server.get_objects_in_group("physics_debug_marker"):
						self.spawn_debug_marker()
					break

	def on_enter(self, player):
		if hasattr(self, "respawn_data"):
			player.char.player_reached_respawn_checkpoint(self.respawn_data[0], self.respawn_data[1])
