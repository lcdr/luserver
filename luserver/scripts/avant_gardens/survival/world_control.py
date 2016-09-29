import luserver.components.script as script
from luserver.bitstream import c_bool, c_int

class ScriptComponent(script.ScriptComponent):
	def player_ready(self, address):
		player = self.object._v_server.accounts[address].characters.selected()
		script_vars = {}
		script_vars["NumberOfPlayers"] = c_int, 1
		script_vars["Define_Player_To_UI"] = bytes, player.object_id
		script_vars["Show_ScoreBoard"] = c_bool, int(True)
		script_vars["Update_ScoreBoard_Players.1"] = bytes, player.object_id
		self.object._v_server.send_game_message(self.script_network_var_update, script_vars, broadcast=True)
