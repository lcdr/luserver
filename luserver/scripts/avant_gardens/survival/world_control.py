import asyncio
import time

import luserver.components.script as script
from luserver.ldf import LDF, LDFDataType
from luserver.bitstream import c_int
from luserver.messages import single
from luserver.world import server
from luserver.components.mission import TaskType
from luserver.math.vector import Vector3
from luserver.math.quaternion import Quaternion

# todo: change this to a separate activity manager script

BASE_SPAWNERS = "Base_MobA", "Base_MobB","Base_MobC"
SURVIVAL_MISSIONS = [
	(479, 60),
	(1153, 180),
	(1618, 420),
	(1648, 420),
	(1628, 420),
	(1638, 420),
	(1412, 120),
	(1510, 120),
	(1547, 120),
	(1584, 120),
	(1426, 300),
	(1524, 300),
	(1561, 300),
	(1598, 300),
	(1865, 180)]

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.set_network_var("NumberOfPlayers", LDFDataType.INT32, 1)

	def set_player_spawn_points(self):
		for index, player_id in enumerate(self.object.scripted_activity.activity_values):
			player = server.get_object(player_id)
			spawn = server.get_objects_in_group("P%i_Spawn" % (index+1))[0]
			player.char.teleport(ignore_y=False, pos=spawn.physics.position, set_rotation=True, x=spawn.physics.rotation.x, y=spawn.physics.rotation.y, z=spawn.physics.rotation.z, w=spawn.physics.rotation.w)

	def start(self):
		if len(self.object.scripted_activity.activity_values) == 1:
			self.game_type = "solo"
		else:
			self.game_type = "team"
		server.spawners["Smash_01"].spawner.activate()
		for spawner in BASE_SPAWNERS:
			server.spawners[spawner].spawner.activate()

		self.start_time = time.time()
		self.tick_handle = self.object.call_later(1, self.tick)
		self.object.scripted_activity.activity_start()
		self.set_network_var("wavesStarted", LDFDataType.BOOLEAN, True)
		self.set_network_var("Start_Wave_Message", LDFDataType.STRING, "Start!")
		self.set_network_var("Clear_Scoreboard", LDFDataType.BOOLEAN, True)
		leaderboard = LDF()
		leaderboard.ldf_set("ADO.Result", LDFDataType.BOOLEAN, True)
		leaderboard.ldf_set("Result.Count", LDFDataType.INT32, 1)
		leaderboard.ldf_set("Result[0].RowCount", LDFDataType.INT32, 0)

		for player_id in self.object.scripted_activity.activity_values:
			player = server.get_object(player_id)
			player.stats.refill_stats()
			self.object.scripted_activity.send_activity_summary_leaderboard_data(game_id=5, info_type=1, leaderboard_data=leaderboard, throttled=False, weekly=False, player=player)

	def game_over(self, player):
		if not self.are_all_players_dead():
			return
		self.object.cancel_callback(self.tick_handle)
		self.script_network_vars.clear()

		server.spawners["Smash_01"].spawner.destroy()
		for spawner in BASE_SPAWNERS:
			server.spawners[spawner].spawner.destroy()

		for player_id, values in self.object.scripted_activity.activity_values.items():
			player = server.get_object(player_id)
			player.char.request_resurrect()

			player_time = values[1]
			player_score = values[0]
			self.object.scripted_activity.notify_client_zone_object(name="Update_ScoreBoard", param1=int(player_time), param2=0, param_str=b"%i" % player_score, param_obj=player)
			self.notify_client_object(name="ToggleLeaderBoard", param1=0, param2=0, param_str=b"", param_obj=player)

			for mission_id, time in SURVIVAL_MISSIONS:
				if player_time > time:
					player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=mission_id)
			player.char.update_mission_task(TaskType.MinigameAchievement, self.object.scripted_activity.activity_id, ("survival_time_"+self.game_type, 400))

	def tick(self):
		self.set_network_var("Update_Timer", LDFDataType.DOUBLE, time.time()-self.start_time)
		self.tick_handle = self.object.call_later(1, self.tick)

	def are_all_players_dead(self):
		for player_id in self.object.scripted_activity.activity_values:
			player = server.get_object(player_id)
			if player.stats.life > 0:
				return False
		return True

	def player_died(self, player):
		if self.script_network_vars.get("wavesStarted", False):
			if self.are_all_players_dead():
				all_dead = b"true"
			else:
				all_dead = b"false"
			self.object.scripted_activity.activity_values[player.object_id][1] = time.time()-self.start_time
			self.object.scripted_activity.notify_client_zone_object(name="Player_Died", param1=int(time.time()-self.start_time), param2=0, param_str=all_dead, param_obj=player)
			self.game_over(player)
		else:
			player.char.request_resurrect()
			self.set_player_spawn_points()

	@single
	def player_ready(self, player):
		self.object.scripted_activity.add_player(player)
		self.set_network_var("Define_Player_To_UI", LDFDataType.BYTES, str(player.object_id).encode())
		self.set_network_var("Show_ScoreBoard", LDFDataType.BOOLEAN, True)
		self.set_network_var("Update_ScoreBoard_Players.1", LDFDataType.BYTES, str(player.object_id).encode())

		self.set_player_spawn_points()

	def message_box_respond(self, player, button:c_int=None, identifier:str=None, user_data:str=None):
		if identifier == "RePlay":
			self.start()

		elif identifier == "Exit_Question" and button == 1:
			self.game_over(player)
			self.object.scripted_activity.remove_player(player)
			asyncio.ensure_future(player.char.transfer_to_last_non_instance(Vector3(131.83, 376, -180.31), Quaternion(0, -0.268720, 0, 0.963218)))
