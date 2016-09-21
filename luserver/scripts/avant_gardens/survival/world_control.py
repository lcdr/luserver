import luserver.components.script as script
from luserver.bitstream import c_bool

class ScriptComponent(script.ScriptComponent):
	def player_ready(self, address):
		script_vars = {}
		script_vars["Show_ScoreBoard"] = c_bool, True
		self.object._v_server.send_game_message(self.script_network_var_update, script_vars, broadcast=True)
