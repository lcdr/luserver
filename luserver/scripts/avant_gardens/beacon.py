import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def complete_rebuild(self, player):
		jet_fx = self.object._v_server.get_objects_in_group("Jet_FX")[0]
		jet_fx.render.play_animation("jetFX")

		# actual jet attack not implemented
