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
		self.object.call_later(BASE_SHAKE_TIME, self.shake)

	def shake(self):
		self.object.render.play_embedded_effect_on_all_clients_near_object(effect_name=SHAKE_EFFECT_NAME, from_object=self.object, radius=SHAKE_RADIUS)

		self.object.render.play_f_x_effect(name=b"Debris", effect_type="DebrisFall")

		self.ship_fx_obj.render.play_f_x_effect(name=b"FX", effect_type="shipboom%i" % random.randint(1, 3), effect_id=559)
		self.ship_fx2_obj.render.play_animation("explosion")

		self.object.call_later(EXPLOSION_ANIM_LENGTH, self.explode_idle)
		self.object.call_later(BASE_SHAKE_TIME + random.randint(MAX_SHAKE_TIME//2, MAX_SHAKE_TIME), self.shake)

	def explode_idle(self):
		self.ship_fx_obj.render.play_animation("idle")
		self.ship_fx2_obj.render.play_animation("idle")
