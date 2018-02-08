import luserver.components.script as script
from luserver.components.mission import TaskType

SMOKE_TIME = 5

# fire going out when sprayed with water not implemented

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.object.render.play_f_x_effect(name=b"candle_light", effect_type="create", effect_id=2108)
		self.script_vars["am_hit"] = False

	def on_hit(self, damage, attacker):
		if not self.script_vars["am_hit"]:
			attacker.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=850)

			self.script_vars["am_hit"] = True
			self.object.render.stop_f_x_effect(name=b"candle_light")
			self.object.render.play_f_x_effect(name=b"candle_smoke", effect_type="create", effect_id=2109)
			self.object.call_later(SMOKE_TIME, self.relight)

	def relight(self):
		self.script_vars["am_hit"] = False
		self.object.render.stop_f_x_effect(name=b"candle_smoke")
		self.object.render.play_f_x_effect(name=b"candle_light", effect_type="create", effect_id=2108)
