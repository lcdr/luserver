import random

from .component import Component

class SpawnerComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.spawner = self
		self.spawntemplate = set_vars["spawntemplate"]
		self.unknown = set_vars.get("spawner_unknown", (0, 0, 1))
		self.waypoints = set_vars["spawner_waypoints"]
		self.last_waypoint_index = 0

	def serialize(self, out, is_creation):
		pass

	def spawn(self, all=False):
		if all:
			spawns = self.unknown[2]
		else:
			spawns = 1
		for _ in range(spawns):
			self.last_waypoint_index = random.randrange(len(self.waypoints))
			spawned_vars = self.waypoints[self.last_waypoint_index]
			spawned = self.object._v_server.spawn_object(self.spawntemplate, spawner=self.object, set_vars=spawned_vars)
		return spawned
