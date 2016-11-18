import luserver.components.script as script

# "set on fire" effect not implemented, requires proximity system
# fire going out when sprayed with water not implemented

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		if hasattr(self.object, "render"): # some objects have render disabled for some reason
			self.object._v_server.send_game_message(self.object.render.play_f_x_effect, name="Burn", effect_type="running", effect_id=295, broadcast=True)
