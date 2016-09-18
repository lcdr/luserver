import asyncio

import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		asyncio.ensure_future(player.char.transfer_to_world((self.script_vars["transfer_world_id"], 0, 0), respawn_point_name=""))
