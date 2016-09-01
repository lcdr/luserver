import logging

from ..components.script import ScriptComponent
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .module import ServerModule

MODEL_DIMENSIONS = {}
MODEL_DIMENSIONS[4734] = Vector3(-5.2644, 0.0051, -0.5011), Vector3(4.7356, 5.0051, 0.4989)
MODEL_DIMENSIONS[5633] = Vector3(-819.2, 0, -819.2), Vector3(819.2, 13.521, 819.2)
MODEL_DIMENSIONS[5652] = Vector3(-2.5, -2.5, -2.5), Vector3(2.5, 2.5, 2.5)
MODEL_DIMENSIONS[8419] = Vector3(-5.2644, 0.0051, -0.5011), Vector3(4.7356, 5.0051, 0.4989)

DEBUG_INCLUDE_NO_SCRIPT = False

log = logging.getLogger(__file__)

# currently for static serverside objects only, does not handle position/rotation updates and object destructions

class AABB: # axis aligned bounding box
	def __init__(self, obj):
		rel_min = MODEL_DIMENSIONS[obj.lot][0] * obj.scale
		rel_max = MODEL_DIMENSIONS[obj.lot][1] * obj.scale

		rel_min = rel_min.rotate(obj.rotation)
		rel_max = rel_max.rotate(obj.rotation)

		# after rotation min and max are no longer necessarily the absolute min/max values

		rot_min = Vector3()
		rot_max = Vector3()

		rot_min.x = min(rel_min.x, rel_max.x)
		rot_min.y = min(rel_min.y, rel_max.y)
		rot_min.z = min(rel_min.z, rel_max.z)
		rot_max.x = max(rel_min.x, rel_max.x)
		rot_max.y = max(rel_min.y, rel_max.y)
		rot_max.z = max(rel_min.z, rel_max.z)

		self.min = obj.position + rot_min
		self.max = obj.position + rot_max

	def is_point_within(self, point):
		return self.min.x < point.x < self.max.x and \
		       self.min.y < point.y < self.max.y and \
		       self.min.z < point.z < self.max.z

class PhysicsHandling(ServerModule):
	def init(self):
		self.tracked_objects = {}
		for obj in self.server.world_data.objects.values():
			if obj.lot in MODEL_DIMENSIONS and (DEBUG_INCLUDE_NO_SCRIPT or isinstance(obj, ScriptComponent)):
				aabb = AABB(obj)
				#self.server.spawn_object(2556, position=aabb.min, rotation=Quaternion.identity)
				#self.server.spawn_object(2556, position=aabb.max, rotation=Quaternion.identity)
				self.tracked_objects[aabb] = obj

	def check_collisions(self, player):
		for aabb, obj in self.tracked_objects.items():
			if aabb.is_point_within(player.position):
				#self.server.spawn_object(2556, parent=player)
				if DEBUG_INCLUDE_NO_SCRIPT and not hasattr(obj, "on_collision"):
					log.warn("Object %s doesn't have a collision callback!", obj)
					return
				obj.on_collision(player)
