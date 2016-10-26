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
		self.ship_fx_obj = self.object._v_server.get_objects_in_group("ShipFX")[0]
		self.ship_fx2_obj = self.object._v_server.get_objects_in_group("ShipFX2")[0]
		asyncio.get_event_loop().call_later(BASE_SHAKE_TIME, self.shake)

	def shake(self):
		self.object._v_server.send_game_message(self.object.render.play_embedded_effect_on_all_clients_near_object, effect_name=SHAKE_EFFECT_NAME, from_object_id=self.object.object_id, radius=SHAKE_RADIUS, broadcast=True)

		self.object._v_server.send_game_message(self.object.render.play_f_x_effect, name="Debris", effect_type="DebrisFall", broadcast=True)

		self.object._v_server.send_game_message(self.ship_fx_obj.render.play_f_x_effect, name="FX", effect_type="shipboom%i" % random.randint(1, 3), effect_id=559, broadcast=True)
		self.object._v_server.send_game_message(self.ship_fx2_obj.render.play_animation, animation_id="explosion", play_immediate=False, broadcast=True)

		asyncio.get_event_loop().call_later(EXPLOSION_ANIM_LENGTH, self.explode_idle)
		asyncio.get_event_loop().call_later(BASE_SHAKE_TIME + random.randint(MAX_SHAKE_TIME//2, MAX_SHAKE_TIME), self.shake)

	def explode_idle(self):
		self.object._v_server.send_game_message(self.ship_fx_obj.render.play_animation, animation_id="idle", play_immediate=False, broadcast=True)
		self.object._v_server.send_game_message(self.ship_fx2_obj.render.play_animation, animation_id="idle", play_immediate=False, broadcast=True)
