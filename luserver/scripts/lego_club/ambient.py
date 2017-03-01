import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object.render.play_animation(animation_id="interact", play_immediate=False)
