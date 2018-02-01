from typing import Optional

import luserver.components.script as script
from luserver.game_object import Player
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		for obj in server.world_data.objects.values():
			if obj.lot == 4945:
				print(obj.groups)
			#if obj.lot == 4945 and self.script_vars["teleport_respawn_point_name"] in obj.groups: # respawn point lot
				player.char.teleport(ignore_y=False, pos=obj.physics.position, set_rotation=True, x=obj.physics.rotation.x, y=obj.physics.rotation.y, z=obj.physics.rotation.z, w=obj.physics.rotation.w)
				break
