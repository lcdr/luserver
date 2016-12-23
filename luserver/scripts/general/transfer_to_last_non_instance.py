import asyncio

import luserver.components.script as script
from luserver.bitstream import c_int

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object._v_server.send_game_message(player.char.display_message_box, show=True, callback_client=self.object.object_id, identifier="instance_exit", image_id=0, text=self.script_vars.get("transfer_text", "DRAGON_EXIT_QUESTION"), user_data="", address=player.char.address)

	def message_box_respond(self, address, button:c_int=None, identifier:"wstr"=None, user_data:"wstr"=None):
		if identifier == "instance_exit" and button == 1:
			player = self.object._v_server.accounts[address].characters.selected()
			asyncio.ensure_future(player.char.transfer_to_world(((player.char.world[0] // 100)*100, player.char.world[1], player.char.world[2])))
