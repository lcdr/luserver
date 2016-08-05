import random

class SpawnerComponent:
	def __init__(self, comp_id):
		self.waypoints = ()
		self.last_waypoint_index = 0

	def serialize(self, out, is_creation):
		pass

	def spawn(self):
		self.last_waypoint_index = random.randrange(len(self.waypoints))
		position, rotation, spawn_vars, spawned_vars, script_vars = self.waypoints[self.last_waypoint_index]
		spawned = self._v_server.spawn_object(self.spawntemplate, spawner=self, custom_script=spawn_vars.get("custom_script"), position=position, rotation=rotation, set_vars=spawned_vars)
		spawned.script_vars = script_vars
		return spawned
