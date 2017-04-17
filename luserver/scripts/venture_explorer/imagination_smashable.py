import random

import luserver.components.script as script
from luserver.bitstream import c_uint, c_int64
from luserver.messages import broadcast
from luserver.components.mission import MissionState

# crate chicken easter egg not implemented

BOB_IMAGINATION_MISSION_ID = 173
IMAGINATION_POWERUP_LOT = 935

class ScriptComponent(script.ScriptComponent):
	@broadcast
	def die(self, client_death:bool=False, spawn_loot:bool=True, death_type:str=None, direction_relative_angle_xz:float=None, direction_relative_angle_y:float=None, direction_relative_force:float=None, kill_type:c_uint=0, killer_id:c_int64=None, loot_owner_id:c_int64=0):
		player = self.object._v_server.get_object(loot_owner_id)
		if BOB_IMAGINATION_MISSION_ID not in player.char.missions:
			return
		mission = player.char.missions[BOB_IMAGINATION_MISSION_ID]
		if mission.state == MissionState.Completed:
			for _ in range(random.randint(1, 2)):
				self.object.physics.drop_loot(IMAGINATION_POWERUP_LOT, player)
