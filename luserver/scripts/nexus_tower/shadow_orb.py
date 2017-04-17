import luserver.components.script as script

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self.notify_client_object(name="reveal", param1=0, param2=0, param_obj=player, param_str=b"")
		player.char.set_flag(flag=True, flag_id=1911)
		player.stats.life = 1
