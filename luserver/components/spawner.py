import random

from .component import Component

class SpawnerComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.spawner = self
		self.spawntemplate = set_vars["spawntemplate"]
		self.waypoints = set_vars["spawner_waypoints"]
		self.last_waypoint_index = 0

	def serialize(self, out, is_creation):
		pass

	def spawn(self):
		self.last_waypoint_index = random.randrange(len(self.waypoints))
		spawned_vars = self.waypoints[self.last_waypoint_index]
		spawned = self.object._v_server.spawn_object(self.spawntemplate, spawner=self.object, set_vars=spawned_vars)
		for comp in spawned.components:
			if hasattr(comp, "on_startup"):
				comp.on_startup()
		return spawned
