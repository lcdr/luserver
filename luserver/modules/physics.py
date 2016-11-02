import logging

from ..bitstream import c_bool, c_float, c_int
from ..math.vector import Vector3
from .module import ServerModule

MODEL_DIMENSIONS = {}
MODEL_DIMENSIONS[1656] = Vector3(-1, -1, -1), Vector3(1, 2, 1) # imagination powerup
MODEL_DIMENSIONS[4734] = Vector3(-5.2644, 0.0051, -0.5011), Vector3(4.7356, 5.0051, 0.4989) # wall
MODEL_DIMENSIONS[4956] = Vector3(-2, 0, -2), Vector3(2, 4, 2) # AG monument switch
MODEL_DIMENSIONS[5633] = Vector3(-819.2, 0, -819.2), Vector3(819.2, 13.521, 819.2) # death plane
MODEL_DIMENSIONS[5650] = MODEL_DIMENSIONS[4956] # AG monument switch rebuild
MODEL_DIMENSIONS[5652] = Vector3(-2.5, -2.5, -2.5), Vector3(2.5, 2.5, 2.5) # cube
MODEL_DIMENSIONS[8419] = MODEL_DIMENSIONS[4734] # wall 2
MODEL_DIMENSIONS[12384] = Vector3(-0.5, -0.0002, -10.225), Vector3(0.5, 12.9755, 10.225) # POI wall
MODEL_DIMENSIONS[10042] = Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5) # primitive model
MODEL_DIMENSIONS[14510] = Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5) # primitive model phantom (humans only)
MODEL_DIMENSIONS[16506] = Vector3(-0.5, 0, -0.5), Vector3(0.5, 1, 0.5) # primitive model phantom with skill component

log = logging.getLogger(__file__)

# currently for static serverside objects only, does not handle position/rotation updates and object destructions

class AABB: # axis aligned bounding box
	def __init__(self, obj):
		if obj.lot in (10042, 14510, 16506):
			if obj.primitive_model_type != 1:
				log.warn("Primitive model type not 1 %s", obj)
			rel_min = MODEL_DIMENSIONS[obj.lot][0] * obj.primitive_model_scale
			rel_max = MODEL_DIMENSIONS[obj.lot][1] * obj.primitive_model_scale
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

class PhysicsHandling(ServerModule):
	def __init__(self, server):
		super().__init__(server)
		self.last_collisions = {}
		self.tracked_objects = {}
		self.debug_markers = []
		debug_cmd = self.server.chat.commands.add_parser("physicsdebug")
		debug_cmd.add_argument("--original", action="store_true", default=False)
		debug_cmd.set_defaults(func=self.debug_cmd)

	def on_startup(self):
		for obj in self.server.world_data.objects.values():
			self.check_add_object(obj)

	def on_validated(self, address):
		if self.server.world_id[0] != 0: # char
			player = self.server.accounts[address].characters.selected()
			self.last_collisions[player] = []

	def on_disconnect_or_connection_lost(self, address):
		if self.server.world_id[0] != 0: # char
			player = self.server.accounts[address].characters.selected()
			del self.last_collisions[player]

	def on_construction(self, obj):
		self.check_add_object(obj)

	def on_destruction(self, obj):
		if obj in self.tracked_objects:
			del self.tracked_objects[obj]

	def check_add_object(self, obj):
		if obj.lot in MODEL_DIMENSIONS:
			for comp in obj.components:
				if hasattr(comp, "on_enter") or hasattr(comp, "on_exit"):
					self.tracked_objects[obj] = AABB(obj)
					break

	def check_collisions(self, player):
		collisions = []
		for obj, aabb in self.tracked_objects.items():
			if aabb.is_point_within(player.physics.position):
				collisions.append(obj)

		for obj in collisions:
			if obj not in self.last_collisions[player]:
				for comp in obj.components:
					if hasattr(comp, "on_enter"):
						comp.on_enter(player)
		for obj in self.last_collisions[player]:
			if obj not in collisions:
				for comp in obj.components:
					if hasattr(comp, "on_exit"):
						comp.on_exit(player)

		self.last_collisions[player] = collisions

	def debug_cmd(self, args, sender):
		if not self.debug_markers:
			for obj, aabb in self.tracked_objects.copy().items():
				if args.original:
					set_vars = {}
					set_vars["position"] = obj.physics.position
					set_vars["rotation"] = obj.physics.rotation
					set_vars["scale"] = obj.scale
					self.debug_markers.append(self.server.spawn_object(obj.lot, set_vars=set_vars))
				set_vars = {}
				set_vars["position"] = Vector3((aabb.min.x+aabb.max.x)/2, aabb.min.y, (aabb.min.z+aabb.max.z)/2)
				config = {}
				config["primitiveModelType"] = c_int, 1
				config["primitiveModelValueX"] = c_float, aabb.max.x-aabb.min.x
				config["primitiveModelValueY"] = c_float, aabb.max.y-aabb.min.y
				config["primitiveModelValueZ"] = c_float, aabb.max.z-aabb.min.z
				set_vars["config"] = config
				self.debug_markers.append(self.server.spawn_object(14510, set_vars=set_vars))

		else:
			for marker in self.debug_markers:
				self.server.destruct(marker)
			self.debug_markers.clear()
