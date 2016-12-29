import asyncio

import luserver.components.script as script
from luserver.ldf import LDFDataType
from luserver.bitstream import c_bool, c_int
from luserver.math.vector import Vector3
from luserver.math.quaternion import Quaternion

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.script_network_vars.ldf_set("NumberOfPlayers", LDFDataType.INT32, 1)

	def set_player_spawn_points(self):
		for index, player_id in enumerate(self.object.scripted_activity.players):
			player = self.object._v_server.get_object(player_id)
			spawn = self.object._v_server.get_objects_in_group("P%i_Spawn" % (index+1))[0]
			self.object._v_server.send_game_message(player.char.teleport, ignore_y=False, pos=spawn.physics.position, set_rotation=True, x=spawn.physics.rotation.x, y=spawn.physics.rotation.y, z=spawn.physics.rotation.z, w=spawn.physics.rotation.w, address=player.char.address)

	def start(self):
		self.object._v_server.send_game_message(self.object.scripted_activity.activity_start, broadcast=True)
		self.script_network_vars.clear()
		self.script_network_vars.ldf_set("Clear_Scoreboard", LDFDataType.BOOLEAN, True)
		self.script_network_vars.ldf_set("Start_Wave_Message", LDFDataType.STRING, "Start!")
		self.script_network_vars.ldf_set("wavesStarted", LDFDataType.BOOLEAN, True)
		self.object._v_server.send_game_message(self.script_network_var_update, self.script_network_vars, broadcast=True)


	def player_ready(self, address):
		player = self.object._v_server.accounts[address].characters.selected()
		self.object.scripted_activity.players.append(player.object_id)
		self.script_network_vars.ldf_set("Define_Player_To_UI", LDFDataType.BYTES, str(player.object_id).encode())
		self.script_network_vars.ldf_set("Show_ScoreBoard", LDFDataType.BOOLEAN, True)
		self.script_network_vars.ldf_set("Update_ScoreBoard_Players.1", LDFDataType.BYTES, str(player.object_id).encode())
		self.object._v_server.send_game_message(self.script_network_var_update, self.script_network_vars, broadcast=True)

		self.set_player_spawn_points()

	def message_box_respond(self, address, button:c_int=None, identifier:"wstr"=None, user_data:"wstr"=None):
		if identifier == "RePlay":
			self.start()

		elif identifier == "Exit_Question" and button == 1:
			player = self.object._v_server.accounts[address].characters.selected()
			asyncio.ensure_future(player.char.transfer_to_last_non_instance(Vector3(131.83, 376, -180.31), Quaternion(0, -0.268720, 0, 0.963218)))
