from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.components.mission import TaskType

IMAGINATION_POWERUP_LOT = 935
WATER_MISSION = 472

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.light_torch()

	def light_torch(self):
		self.is_burning = True
		self.object.render.play_f_x_effect(name=b"tikitorch", effect_type="fire", effect_id=611)

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		self.object.render.play_animation("interact")
		for _ in range(3):
			self.object.physics.drop_loot(IMAGINATION_POWERUP_LOT, player)

	def on_skill_event(self, caster, event_name):
		if event_name == "waterspray":
			if self.is_burning:
				self.is_burning = False
				self.object.render.play_animation("water")
				self.object.render.stop_f_x_effect(name=b"tikitorch")
				self.object.render.play_f_x_effect(name=b"", effect_type="water", effect_id=611)
				self.object.render.play_f_x_effect(name=b"", effect_type="steam", effect_id=611)
				caster.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=WATER_MISSION)

				self.object.call_later(8, self.light_torch)
