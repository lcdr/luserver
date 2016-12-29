import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object.render.play_n_d_audio_emitter(event_guid="{15d5f8bd-139a-4c31-8904-970c480cd70f}", meta_event_name="")
		player.render.play_animation(animation_id="jig", play_immediate=True)
