import random

import luserver.components.script as script
from luserver.bitstream import c_bit, c_float, c_uint, c_int64
from luserver.components.mission import MissionState

# crate chicken easter egg not implemented

BOB_IMAGINATION_MISSION_ID = 173
IMAGINATION_POWERUP_LOT = 935

class ScriptComponent(script.ScriptComponent):
	def die(self, address, client_death:c_bit=False, spawn_loot:c_bit=True, death_type:"wstr"=None, direction_relative_angle_xz:c_float=None, direction_relative_angle_y:c_float=None, direction_relative_force:c_float=None, kill_type:c_uint=0, killer_id:c_int64=None, loot_owner_id:c_int64=0):
		player = self.object._v_server.get_object(loot_owner_id)
		for mission in player.char.missions:
			if mission.id == BOB_IMAGINATION_MISSION_ID:
				if mission.state == MissionState.Completed:
					for _ in range(random.randint(1, 2)):
						self.object.stats.drop_loot(IMAGINATION_POWERUP_LOT, player)
				break
