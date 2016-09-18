import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.object._v_server.send_game_message(self.notify_client_object, name="reveal", param1=0, param2=0, param_obj=player.object_id, param_str="", address=player.char.address)
		player.char.set_flag(address=None, flag=True, flag_id=1911)
		player.stats.life = 1
