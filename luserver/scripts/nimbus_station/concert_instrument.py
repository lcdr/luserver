import luserver.components.script as script
from luserver.game_object import c_int, E, GameObject
from luserver.components.mission import TaskType
from luserver.math.quaternion import Quaternion
from luserver.math.vector import Vector3

# todo: not fully implemented

UPDATE_TIME = 0.1

GUITAR = 4039
BASS = 4040
KEYBOARD = 4041
DRUM = 4042

CONFIG = {
	GUITAR: {
		"cinematic": "Concert_Cam_G",
		"play_anim": "guitar",
		"player_offset": Vector3(5, 0, 0),
		"smash_anim": "guitar-smash"
	},
	BASS: {
		"cinematic": "Concert_Cam_B",
		"play_anim": "bass",
		"player_offset": Vector3(5, 0, 0),
		"smash_anim": "bass-smash"
	},
	KEYBOARD: {
		"cinematic": "Concert_Cam_K",
		"play_anim": "keyboard",
		"player_offset": Vector3(-0.45, 0, 0.75),
		"smash_anim": "keyboard-smash"
	},
	DRUM: {
		"cinematic": "Concert_Cam_D",
		"play_anim": "drums",
		"player_offset": Vector3(0, 0, -0.5),
		"smash_anim": "drums-smash"
	}
}

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.player = None

	def on_destruction(self):
		if self.player is not None:
			self.stop_playing()
			self.player.remove_handler("on_destruction", self.on_player_destruction)

	def complete_rebuild(self, player):
		self.player = player
		# todo: fix this
		# disabling for now because handlers accidentally get saved to DB
		#self.player.add_handler("on_destruction", self.on_player_destruction)
		self.object.call_later(0.1, self.play)

	def play(self):
		config = CONFIG[self.object.lot]
		self.notify_client_object(name="startPlaying", param1=0, param2=0, param_str=b"", param_obj=self.player)
		self.player.char.play_cinematic(path_name=config["cinematic"], start_time_advance=0)
		self.player.render.play_animation(config["play_anim"])

		offset = config["player_offset"]
		new_pos = self.object.physics.position + offset.rotated(self.object.physics.rotation)

		if self.object.lot == KEYBOARD:
			rotation = Quaternion.angle_axis(-0.3, Vector3.up)
		else:
			rotation = self.player.physics.rotation

		self.player.char.teleport(ignore_y=False, set_rotation=True, pos=new_pos, x=rotation.x, y=rotation.y, z=rotation.z, w=rotation.w)

		self.object.call_later(UPDATE_TIME, self.check_on_player)

	def check_on_player(self):
		if self.player is None:
			return
		self.notify_client_object(name="checkMovement", param1=0, param2=0, param_str=b"", param_obj=self.player)
		self.object.call_later(UPDATE_TIME, self.check_on_player)

	def stop_playing(self):
		if self.player is None:
			return

		if self.object.lot == GUITAR:
			self.player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=176)

		self.notify_client_object(name="stopCheckingMovement", param1=0, param2=0, param_str=b"", param_obj=self.player)
		self.player.char.end_cinematic(lead_out=1, path_name="")
		self.player.render.play_animation(CONFIG[self.object.lot]["smash_anim"])

		self.object.call_later(1, self.return_control)

	def return_control(self):
		self.notify_client_object(name="stopPlaying", param1=0, param2=0, param_str=b"", param_obj=self.player)
		self.player = None

	def on_player_destruction(self, player):
		self.object.destructible.simply_die()

	def fire_event_server_side(self, args:str=E, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:GameObject=E):
		if args == "stopPlaying":
			self.stop_playing()
