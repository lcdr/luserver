import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		self.object.destructible.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, killer_id=player.object_id, loot_owner_id=player.object_id)
