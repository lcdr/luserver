import luserver.components.script as script

IMAGINATION_POWERUP_LOT = 935

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object.render.play_animation("interact")
		for _ in range(3):
			self.object.physics.drop_loot(IMAGINATION_POWERUP_LOT, player)
