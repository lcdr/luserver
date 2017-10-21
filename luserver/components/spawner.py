from ..world import server
from .component import Component

class SpawnerComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.spawner = self
		self.active = set_vars.get("active_on_load", True)
		self.spawntemplate = set_vars["spawntemplate"]
		self.name = set_vars.get("spawner_name")
		self.respawn_time = set_vars.get("respawn_time", 8)
		if self.respawn_time == 0:
			self.respawn_time = 8 # not sure why it's 0
		self.num_to_maintain = set_vars.get("num_to_maintain", 1)
		self.waypoints = set_vars["spawner_waypoints"]
		self.spawn_net_on_smash = set_vars.get("spawn_net_on_smash")
		self.last_waypoint_index = 0

	def serialize(self, out, is_creation):
		pass

	def on_startup(self):
		if self.name is not None:
			server.spawners[self.name] = self.object
		if self.active:
			if self.spawn_net_on_smash is not None:
				server.spawners[self.spawn_net_on_smash].add_handler("on_spawned_destruction", self.spawn_on_smash)
				return
			for _ in range(min(self.num_to_maintain, len(self.waypoints))):
				self.spawn()

	def spawn(self):
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

	def on_spawned_destruction(self):
		if self.active:
			self.object.call_later(self.respawn_time, self.spawn)
		if self.spawn_net_on_smash:
			self.active = True

	def spawn_on_smash(self, spawner):
		if self.active:
			self.spawn()
			self.active = False
