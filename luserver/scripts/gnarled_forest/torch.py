import luserver.components.script as script

IMAGINATION_POWERUP_LOT = 935

# fire going out when sprayed with water not implemented

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object.render.play_f_x_effect(name="tikitorch", effect_type="fire", effect_id=611)

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object.render.play_animation(animation_id="interact", play_immediate=False)
		for _ in range(3):
			self.object.physics.drop_loot(IMAGINATION_POWERUP_LOT, player)
