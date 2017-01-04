import asyncio

import luserver.components.script as script
from luserver.components.mission import TaskType

SMOKE_TIME = 5

# fire going out when sprayed with water not implemented

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object.render.play_f_x_effect(name="candle_light", effect_type="create", effect_id=2108)
		self.script_vars["am_hit"] = False

	def on_hit(self, attacker):
		if not self.script_vars["am_hit"]:
			attacker.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=850)

			self.script_vars["am_hit"] = True
			self.object.render.stop_f_x_effect(name="candle_light", kill_immediate=False)
			self.object.render.play_f_x_effect(name="candle_smoke", effect_type="create", effect_id=2109)
			asyncio.get_event_loop().call_later(SMOKE_TIME, self.relight)

	def relight(self):
		self.script_vars["am_hit"] = False
		self.object.render.stop_f_x_effect(name="candle_smoke", kill_immediate=False)
		self.object.render.play_f_x_effect(name="candle_light", effect_type="create", effect_id=2108)
