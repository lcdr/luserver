import luserver.components.script as script
from luserver.ldf import LDFDataType
from luserver.bitstream import c_int
from luserver.game_object import GameObject
from luserver.messages import broadcast, single
from luserver.math.vector import Vector3
from luserver.components.racing_control import RacingNotificationType

class ScriptComponent(script.ScriptComponent):
	@single
	def player_ready(self, player):
		player.char.teleport(ignore_y=False, pos=Vector3(817.812255859375, 247.02963256835938, -3.9437739849090576), x=0, y=0, z=0)
		self.object.scripted_activity.add_player(player)
		# wrong car lot for now
		car = self.object._v_server.spawn_object(7707, set_vars={"parent": self.object, "position": player.physics.position, "rotation": player.physics.rotation})
		self.object.racing_control.player_data[player] = [car]
		self.object.racing_control.player_data_flag = True
		player.char.mount(car)
		self.racing_player_loaded(player, car)
		self.object.racing_control.notify_racing_client(event_type=RacingNotificationType.ActivityStart, param1=0, param_obj=0, param_str="", single_client=0)
		self.object.scripted_activity.activity_start()

	@broadcast
	def racing_player_loaded(self, player:GameObject=None, vehicle:GameObject=None):
		pass
