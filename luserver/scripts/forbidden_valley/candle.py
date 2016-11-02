import asyncio

import luserver.components.script as script
from luserver.components.mission import MissionState, TaskType

SMOKE_TIME = 5

# fire going out when sprayed with water not implemented

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object._v_server.send_game_message(self.object.render.play_f_x_effect, name="candle_light", effect_type="create", effect_id=2108, broadcast=True)
		self.script_vars["am_hit"] = False

	def on_hit(self, attacker):
		if not self.script_vars["am_hit"]:
			for mission in attacker.char.missions:
				if mission.id == 850 and mission.state == MissionState.Active:
					for task in mission.tasks:
						if task.type == TaskType.Script and self.object.lot in task.target:
							mission.increment_task(task, attacker)

			self.script_vars["am_hit"] = True
			self.object._v_server.send_game_message(self.object.render.stop_f_x_effect, name="candle_light", kill_immediate=False, broadcast=True)
			self.object._v_server.send_game_message(self.object.render.play_f_x_effect, name="candle_smoke", effect_type="create", effect_id=2109, broadcast=True)
			asyncio.get_event_loop().call_later(SMOKE_TIME, self.relight)

	def relight(self):
		self.script_vars["am_hit"] = False
		self.object._v_server.send_game_message(self.object.render.stop_f_x_effect, name="candle_smoke", kill_immediate=False, broadcast=True)
		self.object._v_server.send_game_message(self.object.render.play_f_x_effect, name="candle_light", effect_type="create", effect_id=2108, broadcast=True)
