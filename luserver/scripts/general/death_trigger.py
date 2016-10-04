import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_collision(self, player):
		self.object._v_server.send_game_message(player.destructible.request_die, unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, kill_type=1, killer_id=self.object.object_id, loot_owner_id=0, address=player.char.address)