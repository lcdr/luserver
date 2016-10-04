import logging

from ..math.vector import Vector3
from .module import ServerModule

MODEL_DIMENSIONS = {}
MODEL_DIMENSIONS[4734] = Vector3(-5.2644, 0.0051, -0.5011), Vector3(4.7356, 5.0051, 0.4989) # wall
MODEL_DIMENSIONS[5633] = Vector3(-819.2, 0, -819.2), Vector3(819.2, 13.521, 819.2)
MODEL_DIMENSIONS[5652] = Vector3(-2.5, -2.5, -2.5), Vector3(2.5, 2.5, 2.5) # cube
MODEL_DIMENSIONS[8419] = MODEL_DIMENSIONS[4734] # wall 2

log = logging.getLogger(__file__)

# currently for static serverside objects only, does not handle position/rotation updates and object destructions

class AABB: # axis aligned bounding box
	def __init__(self, obj):
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
				if hasattr(comp, "on_enter"):
					self.tracked_objects[obj] = AABB(obj)
					break

	def check_collisions(self, player):
		collisions = []
		for obj, aabb in self.tracked_objects.items():
			if aabb.is_point_within(player.physics.position):
				if obj not in self.last_collisions[player]:
					for comp in obj.components:
						if hasattr(comp, "on_enter"):
							comp.on_enter(player)
				collisions.append(obj)
		self.last_collisions[player] = collisions

	def debug_cmd(self, args, sender):
		if not self.debug_markers:
			for obj, aabb in self.tracked_objects.items():
				set_vars = {}
				set_vars["position"] = obj.physics.position
				set_vars["rotation"] = obj.physics.rotation
				set_vars["scale"] = obj.scale
				self.debug_markers.append(self.server.spawn_object(obj.lot, set_vars=set_vars))
		else:
			for marker in self.debug_markers:
				self.server.destruct(marker)
			self.debug_markers.clear()
