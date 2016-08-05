import asyncio
import random

import luserver.components.script as script

BASE_SHAKE_TIME = 2
MAX_SHAKE_TIME = 20
EXPLOSION_ANIM_LENGTH = 3.3
SHAKE_EFFECT_NAME = "camshake-bridge"
SHAKE_RADIUS = 500

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		for obj in self._v_server.world_data.objects.values():
			if "ShipFX" in obj.groups:
				self.ship_fx_obj = obj
				break
		for obj in self._v_server.world_data.objects.values():
			if "ShipFX2" in obj.groups:
				self.ship_fx2_obj = obj
				break

		asyncio.get_event_loop().call_later(BASE_SHAKE_TIME, self.shake)

	def shake(self):
		self._v_server.send_game_message(self.play_embedded_effect_on_all_clients_near_object, effect_name=SHAKE_EFFECT_NAME, from_object_id=self.object_id, radius=SHAKE_RADIUS, broadcast=True)

		self._v_server.send_game_message(self.play_f_x_effect, name="Debris", effect_type="DebrisFall", broadcast=True)

		self._v_server.send_game_message(self.ship_fx_obj.play_f_x_effect, name="FX", effect_type="shipboom%i" % random.randint(1, 3), effect_id=559, broadcast=True)
		self._v_server.send_game_message(self.ship_fx2_obj.play_animation, animation_id="explosion", play_immediate=False, broadcast=True)

		asyncio.get_event_loop().call_later(EXPLOSION_ANIM_LENGTH, self.explode_idle)
		asyncio.get_event_loop().call_later(BASE_SHAKE_TIME + random.randint(MAX_SHAKE_TIME//2, MAX_SHAKE_TIME), self.shake)

	def explode_idle(self):
		self._v_server.send_game_message(self.ship_fx_obj.play_animation, animation_id="idle", play_immediate=False, broadcast=True)
		self._v_server.send_game_message(self.ship_fx2_obj.play_animation, animation_id="idle", play_immediate=False, broadcast=True)
