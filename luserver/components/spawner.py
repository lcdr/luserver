import random

from ..world import server
from .component import Component

class SpawnerComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.spawner = self
		self.active = True
		self.spawntemplate = set_vars["spawntemplate"]
		self.name = set_vars.get("spawner_name")
		self.unknown = set_vars.get("spawner_unknown", (0, 0, 1))
		self.waypoints = set_vars["spawner_waypoints"]
		self.spawned_on_smash = set_vars.get("spawned_on_smash", False)
		self.last_waypoint_index = 0

	def serialize(self, out, is_creation):
		pass

	def on_startup(self):
		if self.name is not None:
			server.spawners[self.name] = self.object
		if self.active and not self.spawned_on_smash:
			for _ in range(min(self.unknown[2], len(self.waypoints))):
				self.spawn()

	def spawn(self):
		if not self.active:
			return
		spawned_vars = self.waypoints[self.last_waypoint_index].copy()
		spawned_vars["spawner"] = self.object
		spawned = server.spawn_object(self.spawntemplate, spawned_vars)
		if self.last_waypoint_index == len(self.waypoints)-1:
			self.last_waypoint_index = 0
		else:
			self.last_waypoint_index += 1
		return spawned

	def deactivate(self):
		self.active = False

	def destroy(self):
		self.deactivate()
		for obj in server.game_objects.copy().values():
			if obj.spawner_object == self.object:
				server.replica_manager.destruct(obj)
