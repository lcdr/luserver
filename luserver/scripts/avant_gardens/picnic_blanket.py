import luserver.components.script as script

IMAGINATION_POWERUP_LOT = 935

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self._v_server.send_game_message(self.play_animation, animation_id="interact", play_immediate=False, address=player.address)
		for _ in range(3):
			self.drop_loot(IMAGINATION_POWERUP_LOT, player)
