import asyncio
from typing import Optional

import luserver.components.script as script
from luserver.game_object import c_int, EI, ES, Player

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> None:
		assert multi_interact_id is None
		player.char.ui.disp_message_box(self.script_vars.get("transfer_text", "DRAGON_EXIT_QUESTION"), id="instance_exit", callback=self.object)

	def on_message_box_respond(self, player, button:c_int=EI, id:str=ES, user_data:str=ES):
		if id == "instance_exit" and button == 1:
			asyncio.ensure_future(player.char.transfer_to_last_non_instance())
