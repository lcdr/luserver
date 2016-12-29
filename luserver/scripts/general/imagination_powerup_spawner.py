import luserver.components.script as script

IMAGINATION_SKILL = 13

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		self.object.skill.cast_skill(13, target=player)
		self.object.destructible.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=10, killer_id=self.object.object_id, loot_owner_id=self.object.object_id)
