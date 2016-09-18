import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		if "alt_flag_id" in self.script_vars:
			flag_id = self.script_vars["alt_flag_id"]
		else:
			flag_id = 10000 + self.object._v_server.world_id[0] + self.script_vars["flag_id"]
		player.char.set_flag(None, True, flag_id=flag_id)
		self.object._v_server.send_game_message(self.object.fire_event_client_side, args="achieve", obj=0, sender_id=0, address=player.char.address)
