import logging
import math

from ..ldf import LDF, LDFDataType
from ..math.vector import Vector3
from .module import ServerModule

log = logging.getLogger(__file__)

MODEL_DIMENSIONS = {
	1656: (Vector3(-1, -1, -1), Vector3(1, 2, 1)), # imagination powerup
	4734: (Vector3(-5.2644, 0.0051, -0.5011), Vector3(4.7356, 5.0051, 0.4989)), # wall
	4956: (Vector3(-2, 0, -2), Vector3(2, 4, 2)), # AG monument switch,
	5633: (Vector3(-819.2, 0, -819.2), Vector3(819.2, 13.521, 819.2)), # death plane
	5652: (Vector3(-2.5, -2.5, -2.5), Vector3(2.5, 2.5, 2.5)), # cube
	12384: (Vector3(-0.5, -0.0002, -10.225), Vector3(0.5, 12.9755, 10.225))} # POI wall
MODEL_DIMENSIONS[5650] = MODEL_DIMENSIONS[4956] # AG monument switch rebuild
MODEL_DIMENSIONS[8419] = MODEL_DIMENSIONS[4734] # wall 2

class PrimitiveModelType:
	Cuboid = 1
	Cone = 2
	Cylinder = 3
	Sphere = 4

PRIMITIVE_DIMENSIONS = {
	PrimitiveModelType.Cuboid: (Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5))}

# currently for static objects only, does not handle position/rotation updates
class AABB: # axis aligned bounding box
	def __init__(self, obj):
		if hasattr(obj, "primitive_model_type"):
			if obj.primitive_model_type != PrimitiveModelType.Cuboid:
				raise NotImplementedError("Primitive model type not cuboid %s" % obj)
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

class PhysicsHandling(ServerModule):
	def __init__(self, server):
		super().__init__(server)
		self.last_collisions = {}
		self.tracked_objects = {}
		self.debug_markers = {}
		debug_cmd = self.server.chat.commands.add_parser("physicsdebug")
		debug_cmd.add_argument("--original", action="store_true", default=False)
		debug_cmd.set_defaults(func=self.debug_cmd)

	def on_startup(self):
		for obj in self.server.world_data.objects.values():
			self.check_add_object(obj)

	def on_construction(self, obj):
		self.check_add_object(obj)
		if hasattr(obj, "char"):
			self.last_collisions[obj] = []

	def on_destruction(self, obj):
		if obj in self.tracked_objects:
			del self.tracked_objects[obj]
		if obj in self.debug_markers:
			for marker in self.debug_markers[obj]:
				self.server.destruct(marker)
			del self.debug_markers[obj]
		if hasattr(obj, "char"):
			del self.last_collisions[obj]

	def check_add_object(self, obj):
		if obj.lot in MODEL_DIMENSIONS or (hasattr(obj, "primitive_model_type") and obj.primitive_model_type == PrimitiveModelType.Cuboid):
			for comp in obj.components:
				if hasattr(comp, "on_enter") or hasattr(comp, "on_exit"):
					self.tracked_objects[obj] = AABB(obj)
					if self.debug_markers:
						self.add_marker(obj)
					break

	def add_with_radius(self, obj, radius):
		for comp in obj.components:
			if hasattr(comp, "on_enter") or hasattr(comp, "on_exit"):
				self.tracked_objects[obj] = CollisionSphere(obj, radius)
				if self.debug_markers:
					self.add_marker(obj)
				break

	def check_collisions(self, player):
		collisions = []
		for obj, coll in self.tracked_objects.items():
			if coll.is_point_within(player.physics.position):
				collisions.append(obj)

		for obj in collisions:
			if obj not in self.last_collisions[player]:
				obj.handle("on_enter", player)
		for obj in self.last_collisions[player]:
			if obj not in collisions:
				obj.handle("on_exit", player, silent=True)

		self.last_collisions[player] = collisions

	def debug_cmd(self, args, sender):
		if not self.debug_markers:
			for obj in self.tracked_objects.copy():
				self.add_marker(obj, args.original)
		else:
			for markers in self.debug_markers.copy().values():
				for marker in markers:
					self.server.destruct(marker)
			self.debug_markers.clear()

	def add_marker(self, obj, original=False):
		if obj not in self.tracked_objects:
			return
		coll = self.tracked_objects[obj]
		if original:
			set_vars = {
				"position": obj.physics.position,
				"rotation": obj.physics.rotation,
				"scale": obj.scale}
			self.debug_markers.setdefault(obj, []).append(self.server.spawn_object(obj.lot, set_vars))
		if isinstance(coll, AABB):
			config = LDF()
			config.ldf_set("primitiveModelType", LDFDataType.INT32, PrimitiveModelType.Cuboid)
			config.ldf_set("primitiveModelValueX", LDFDataType.FLOAT, coll.max.x-coll.min.x)
			config.ldf_set("primitiveModelValueY", LDFDataType.FLOAT, coll.max.y-coll.min.y)
			config.ldf_set("primitiveModelValueZ", LDFDataType.FLOAT, coll.max.z-coll.min.z)

			set_vars = {
				"position": Vector3((coll.min.x+coll.max.x)/2, coll.min.y, (coll.min.z+coll.max.z)/2),
				"config": config}
			self.debug_markers.setdefault(obj, []).append(self.server.spawn_object(14510, set_vars))
		elif isinstance(coll, CollisionSphere):
			set_vars = {
				"position": coll.position,
				"scale": math.sqrt(coll.sq_radius)/5}
			self.debug_markers.setdefault(obj, []).append(self.server.spawn_object(6548, set_vars))
