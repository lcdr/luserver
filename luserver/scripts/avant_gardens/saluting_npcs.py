import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_emote_received(self, player, emote_id):
		if emote_id == 356:
			self.object.render.play_animation("salutePlayer")
