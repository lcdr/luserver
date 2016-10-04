import luserver.components.script as script

DEATH_ANIMATION = "electro-shock-death"

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		self.object._v_server.send_game_message(player.destructible.request_die, unknown_bool=False, death_type=DEATH_ANIMATION, direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, killer_id=self.object.object_id, loot_owner_id=0, address=player.char.address)
