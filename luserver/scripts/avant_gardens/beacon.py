from typing import cast

import luserver.components.script as script
from luserver.game_object import RenderObject
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_complete_rebuild(self, player):
		jet_fx = cast(RenderObject, server.get_objects_in_group("Jet_FX")[0])
		jet_fx.render.play_animation("jetFX")

		# actual jet attack not implemented
