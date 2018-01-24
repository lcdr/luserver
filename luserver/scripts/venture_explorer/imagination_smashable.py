import random

import luserver.components.script as script
from luserver.game_object import broadcast, c_uint, E, GameObject
from luserver.components.mission import MissionState

# crate chicken easter egg not implemented

BOB_IMAGINATION_MISSION_ID = 173
IMAGINATION_POWERUP_LOT = 935

class ScriptComponent(script.ScriptComponent):
	@broadcast
	def die(self, client_death:bool=False, spawn_loot:bool=True, death_type:str=E, direction_relative_angle_xz:float=E, direction_relative_angle_y:float=E, direction_relative_force:float=E, kill_type:c_uint=0, killer:GameObject=E, loot_owner:GameObject=None):
		player = loot_owner
		if BOB_IMAGINATION_MISSION_ID not in player.char.missions:
			return
		mission = player.char.missions[BOB_IMAGINATION_MISSION_ID]
		if mission.state == MissionState.Completed:
			for _ in range(random.randint(1, 2)):
				self.object.physics.drop_loot(IMAGINATION_POWERUP_LOT, player)
