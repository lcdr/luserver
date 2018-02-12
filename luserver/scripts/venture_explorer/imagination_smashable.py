import random

import luserver.components.script as script
from luserver.game_object import GameObject
from luserver.components.mission import MissionState

# crate chicken easter egg not implemented

BOB_IMAGINATION_MISSION_ID = 173
IMAGINATION_POWERUP_LOT = 935

class ScriptComponent(script.ScriptComponent):
	def on_death(self, killer: GameObject) -> None:
		if BOB_IMAGINATION_MISSION_ID not in killer.char.mission.missions:
			return
		mission = killer.char.mission.missions[BOB_IMAGINATION_MISSION_ID]
		if mission.state == MissionState.Completed:
			for _ in range(random.randint(1, 2)):
				self.object.physics.drop_loot(IMAGINATION_POWERUP_LOT, killer)
