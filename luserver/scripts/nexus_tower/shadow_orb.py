import luserver.components.script as script
from luserver.bitstream import c_int, c_int64

class ScriptComponent(script.ScriptComponent):
	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		self._v_server.send_game_message(self.notify_client_object, name="reveal", param1=0, param2=0, param_obj=player.object_id, param_str="", address=player.address)
		player.set_flag(address=None, flag=True, flag_id=1911)
		player.life = 1

	def notify_client_object(self, address, name:"wstr"=None, param1:c_int=None, param2:c_int=None, param_obj:c_int64=None, param_str:"str"=None):
		pass

