import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		player.set_flag(None, True, flag_id=self._v_server.world_id[0]+self.script_vars["flag_id"])
		self._v_server.send_game_message(self.fire_event_client_side, args="achieve", obj=0, sender_id=0, address=player.address)
