import luserver.components.script as script
from luserver.math.vector import Vector3

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		player.char.knockback(vector=Vector3(-20, 10, -20))
		player.render.play_animation("knockback-recovery")

		self.object.render.play_f_x_effect(name=b"console_sparks", effect_type="create", effect_id=1430)
		self.object.call_later(2, lambda: self.object.render.stop_f_x_effect(name=b"console_sparks"))
