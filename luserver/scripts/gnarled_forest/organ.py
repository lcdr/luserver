import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object.render.play_n_d_audio_emitter(event_guid=b"{15d5f8bd-139a-4c31-8904-970c480cd70f}", meta_event_name=b"")
		player.render.play_animation("jig", play_immediate=True)
