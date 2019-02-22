import enum
import random
from abc import ABC, abstractmethod
from typing import Optional

from bitstream import c_bit, c_float, c_int64, c_ubyte, c_uint, WriteStream
from ..game_object import Config, broadcast, EBY, GameObject, PhysicsObject, Player
from ..world import Event, server
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .component import Component

class PhysicsComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.physics = self
		self._flags["position"] = "physics_data_flag"
		self._flags["rotation"] = "physics_data_flag"
		self.position = Vector3()
		self.rotation = Quaternion()

		if "position" in set_vars:
			self.position.update(set_vars["position"])
		elif "parent" in set_vars and isinstance(set_vars["parent"], PhysicsObject):
			self.position.update(set_vars["parent"].physics.position)
		if "rotation" in set_vars:
			self.rotation.update(set_vars["rotation"])
		elif "parent" in set_vars and isinstance(set_vars["parent"], PhysicsObject):
			self.rotation.update(set_vars["parent"].physics.rotation)

	def on_destruction(self) -> None:
		if self.object in server.general.tracked_objects:
			del server.general.tracked_objects[self.object]

	def proximity_radius(self, radius: int) -> None:
		for comp in self.object.components:
			if hasattr(comp, "on_enter") or hasattr(comp, "on_exit"):
				server.general.tracked_objects[self.object] = CollisionSphere(self.object, radius)
				server.handle(Event.ProximityRadius, self)
				break

	# not really related to physics, but depends on physics and hasn't been conclusively associated with a component

	def drop_rewards(self, loot_matrix, currency_min: Optional[int], currency_max: Optional[int], owner: Player) -> None:
		if currency_min is not None and currency_max is not None:
			currency = random.randint(currency_min, currency_max)
			owner.char.drop_client_loot(currency=currency, item_template=-1, loot_id=0, owner=owner, source_obj=self.object)

		if loot_matrix is not None:
			loot = owner.char.random_loot(loot_matrix)
			for lot in loot.elements():
				self.drop_loot(lot, owner)

	def drop_loot(self, lot: int, owner: Player) -> None:
		loot_position = Vector3(self.position.x+(random.random()-0.5)*20, self.position.y, self.position.z+(random.random()-0.5)*20)
		object_id = server.new_spawned_id()
		owner.char.dropped_loot[object_id] = lot
		owner.char.drop_client_loot(spawn_position=self.position, final_position=loot_position, currency=0, item_template=lot, loot_id=object_id, owner=owner, source_obj=self.object)

class Controllable(PhysicsComponent):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
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

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if self.flag("physics_data_flag", out, is_creation):
			out.write(self.position)
			out.write(self.rotation)

			out.write(c_bit(self.on_ground))
			out.write(c_bit(self.unknown_bool))

			if self.flag("velocity_flag", out):
				out.write(self.velocity)

			if self.flag("angular_velocity_flag", out):
				out.write(c_float(self.angular_velocity[0]))
				out.write(c_float(self.angular_velocity[1]))
				out.write(c_float(self.angular_velocity[2]))

			if self.flag("unknown_flag", out):
				out.write(c_int64(self.unknown_object_id))
				out.write(c_float(self.unknown_float3[0]))
				out.write(c_float(self.unknown_float3[1]))
				out.write(c_float(self.unknown_float3[2]))

				if self.flag("deeper_unknown_flag", out):
					out.write(c_float(self.deeper_unknown_float3[0]))
					out.write(c_float(self.deeper_unknown_float3[1]))
					out.write(c_float(self.deeper_unknown_float3[2]))

			self.write_vehicle_stuff(out, is_creation)
			if not is_creation:
				out.write(c_bit(False))

	def write_vehicle_stuff(self, out: WriteStream, is_creation: bool) -> None:
		pass # hook for vehiclephysics

class ControllablePhysicsComponent(Controllable):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if is_creation:
			out.write(c_bit(False))
			out.write(c_bit(False))

		out.write(c_bit(False))
		out.write(c_bit(False))
		out.write(c_bit(False))
		super().serialize(out, is_creation)

	# not sure which component this belongs to, putting it here for now
	@broadcast
	def lock_node_rotation(self, node_name:bytes=EBY) -> None:
		pass

class SimplePhysicsComponent(PhysicsComponent):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if is_creation:
			out.write(c_bit(False))
			out.write(c_float(0))
		out.write(c_bit(False))
		out.write(c_bit(False))
		if self.flag("physics_data_flag", out, is_creation):
			out.write(self.position)
			out.write(self.rotation)

class RigidBodyPhantomPhysicsComponent(PhysicsComponent):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if self.flag("physics_data_flag", out, is_creation):
			out.write(self.position)
			out.write(self.rotation)

class VehiclePhysicsComponent(Controllable):
	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		super().serialize(out, is_creation)
		if is_creation:
			out.write(c_ubyte(0))
			out.write(c_bit(False))
		out.write(c_bit(False))

	def write_vehicle_stuff(self, out: WriteStream, is_creation: bool) -> None:
		out.write(c_bit(False))
		out.write(c_float(0))

_MODEL_DIMENSIONS = {
	1656: (Vector3(-1, -1, -1), Vector3(1, 2, 1)), # imagination powerup
	4734: (Vector3(-5.2644, 0.0051, -0.5011), Vector3(4.7356, 5.0051, 0.4989)), # wall
	4956: (Vector3(-2, 0, -2), Vector3(2, 4, 2)), # AG monument switch,
	5633: (Vector3(-819.2, 0, -819.2), Vector3(819.2, 13.521, 819.2)), # death plane
	5652: (Vector3(-2.5, -2.5, -2.5), Vector3(2.5, 2.5, 2.5)), # cube
	10285: (Vector3(-7, 0, -6), Vector3(7, 3, 8)), # lego club ring
	12384: (Vector3(-0.5, -0.0002, -10.225), Vector3(0.5, 12.9755, 10.225))} # POI wall
_MODEL_DIMENSIONS[5650] = _MODEL_DIMENSIONS[4956] # AG monument switch rebuild
_MODEL_DIMENSIONS[8419] = _MODEL_DIMENSIONS[4734] # wall 2

class PrimitiveModelType:
	Cuboid = 1
	Cone = 2
	Cylinder = 3
	Sphere = 4

_PRIMITIVE_DIMENSIONS = {
	PrimitiveModelType.Cuboid: (Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5)),
	PrimitiveModelType.Cylinder: (Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5))}

class Collider(ABC):
	@abstractmethod
	def is_point_within(self, point: Vector3) -> bool:
		pass

# currently for static objects only, does not handle position/rotation updates
class AABB(Collider): # axis aligned bounding box
	def __init__(self, obj: PhysicsObject):
		if hasattr(obj, "primitive_model_type"):
			rel_min = _PRIMITIVE_DIMENSIONS[obj.primitive_model_type][0].hadamard(obj.primitive_model_scale)
			rel_max = _PRIMITIVE_DIMENSIONS[obj.primitive_model_type][1].hadamard(obj.primitive_model_scale)
		else:
			rel_min = _MODEL_DIMENSIONS[obj.lot][0] * obj.scale
			rel_max = _MODEL_DIMENSIONS[obj.lot][1] * obj.scale

		vertices = [
			Vector3(rel_min.x, rel_min.y, rel_min.z),
			Vector3(rel_min.x, rel_min.y, rel_max.z),
			Vector3(rel_min.x, rel_max.y, rel_min.z),
			Vector3(rel_min.x, rel_max.y, rel_max.z),
			Vector3(rel_max.x, rel_min.y, rel_min.z),
			Vector3(rel_max.x, rel_min.y, rel_max.z),
			Vector3(rel_max.x, rel_max.y, rel_min.z),
			Vector3(rel_max.x, rel_max.y, rel_max.z)]

		rotated_vertices = []
		for vertex in vertices:
			rotated_vertices.append(obj.physics.rotation.rotate(vertex))

		rot_min = Vector3()
		rot_max = Vector3()

		for vertex in rotated_vertices:
			rot_min.x = min(rot_min.x, vertex.x)
			rot_min.y = min(rot_min.y, vertex.y)
			rot_min.z = min(rot_min.z, vertex.z)
			rot_max.x = max(rot_max.x, vertex.x)
			rot_max.y = max(rot_max.y, vertex.y)
			rot_max.z = max(rot_max.z, vertex.z)

		self.min = obj.physics.position + rot_min
		self.max = obj.physics.position + rot_max

	def is_point_within(self, point: Vector3) -> bool:
		return self.min.x < point.x < self.max.x and \
		       self.min.y < point.y < self.max.y and \
		       self.min.z < point.z < self.max.z

# for dynamic objects
class CollisionSphere(Collider):
	def __init__(self, obj: PhysicsObject, radius: int):
		self.position = obj.physics.position
		self.sq_radius = radius**2

	def is_point_within(self, point: Vector3) -> bool:
		return self.position.sq_distance(point) < self.sq_radius

class PhysicsEffect(enum.IntEnum):
	Push = 0
	Attract = 1
	Repulse = 2
	Gravity = 3
	Friction = 4

class PhantomPhysicsComponent(PhysicsComponent):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
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

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		if self.flag("physics_data_flag", out, is_creation):
			out.write(self.position)
			out.write(self.rotation)

		if self.flag("physics_effect_flag", out, is_creation):
			out.write(c_bit(self.physics_effect_active))
			if self.physics_effect_active:
				out.write(c_uint(self.physics_effect_type))
				out.write(c_float(self.physics_effect_amount))
				out.write(c_bit(False))
				out.write(c_bit(True))
				out.write(self.physics_effect_direction)

	def on_startup(self) -> None:
		if self.object.lot in _MODEL_DIMENSIONS or (hasattr(self.object, "primitive_model_type") and self.object.primitive_model_type in (PrimitiveModelType.Cuboid, PrimitiveModelType.Cylinder)):
			for comp in self.object.components:
				if comp is self:
					if not hasattr(self, "respawn_data"):
						continue
				if hasattr(comp, "on_enter") or hasattr(comp, "on_exit"):
					server.general.tracked_objects[self.object] = AABB(self.object)
					break

	def on_enter(self, player: Player) -> None:
		if hasattr(self, "respawn_data"):
			player.char.player_reached_respawn_checkpoint(self.respawn_data[0], self.respawn_data[1])
