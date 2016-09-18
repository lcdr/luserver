import asyncio

import luserver.components.script as script
from luserver.math.vector import Vector3

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object._v_server.send_game_message(player.char.knockback, vector=Vector3(-20, 10, -20), address=player.char.address)
		self.object._v_server.send_game_message(player.play_animation, animation_id="knockback-recovery", play_immediate=False, address=player.char.address)

		self.object._v_server.send_game_message(self.object.render.play_f_x_effect, name="console_sparks", effect_type="create", effect_id=1430, address=player.char.address)
		asyncio.get_event_loop().call_later(2, lambda: self.object._v_server.send_game_message(self.object.render.stop_f_x_effect, name="console_sparks", kill_immediate=False, address=player.char.address))
