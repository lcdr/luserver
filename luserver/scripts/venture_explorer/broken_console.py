import asyncio

import luserver.components.script as script
from luserver.math.vector import Vector3

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self._v_server.send_game_message(player.knockback, vector=Vector3(-20, 10, -20), address=player.address)
		self._v_server.send_game_message(player.play_animation, animation_id="knockback-recovery", play_immediate=False, address=player.address)

		self._v_server.send_game_message(self.play_f_x_effect, name="console_sparks", effect_type="create", effect_id=1430, address=player.address)
		asyncio.get_event_loop().call_later(2, lambda: self._v_server.send_game_message(self.stop_f_x_effect, name="console_sparks", kill_immediate=False, address=player.address))
