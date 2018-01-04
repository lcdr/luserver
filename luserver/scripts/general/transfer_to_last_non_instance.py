import asyncio

import luserver.components.script as script
from pyraknet.bitstream import c_int

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		player.char.display_message_box(show=True, callback_client=self.object, id="instance_exit", image_id=0, text=self.script_vars.get("transfer_text", "DRAGON_EXIT_QUESTION"), user_data="")

	def message_box_respond(self, player, button:c_int=None, id:str=None, user_data:str=None):
		if id == "instance_exit" and button == 1:
			asyncio.ensure_future(player.char.transfer_to_last_non_instance())
