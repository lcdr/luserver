import random

from .component import Component

class SpawnerComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.spawner = self
		self.spawntemplate = set_vars["spawntemplate"]
		self.unknown = set_vars.get("spawner_unknown", (0, 0, 1))
		self.waypoints = set_vars["spawner_waypoints"]
		self.spawned_on_smash = set_vars.get("spawned_on_smash", False)
		self.last_waypoint_index = 0

	def serialize(self, out, is_creation):
		pass

	def on_startup(self):
		if not self.spawned_on_smash:
			for _ in range(self.unknown[2]):
				self.spawn()

	def spawn(self):
		self.last_waypoint_index = random.randrange(len(self.waypoints))
		spawned_vars = self.waypoints[self.last_waypoint_index].copy()
		spawned_vars["spawner"] = self.object
		spawned = self.object._v_server.spawn_object(self.spawntemplate, spawned_vars)
		return spawned
