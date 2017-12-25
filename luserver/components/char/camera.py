from ...amf3 import AMF3
from ...bitstream import c_int, c_uint
from ...game_object import GameObject
from ...ldf import LDF
from ...messages import broadcast, single
from ...math.vector import Vector3

class EndBehavior:
	Return = 0
	Wait = 1

class CinematicEvent:
	Started = 0
	Waypoint = 1
	Ended = 2

class CyclingMode:
	AllowCycleTeammates = 0
	DisallowCycling = 1

class CharCamera:
	@single
	def play_cinematic(self, allow_ghost_updates:bool=True, close_multi_interact:bool=False, send_server_notify:bool=False, use_controlled_object_for_audio_listener:bool=False, end_behavior:c_uint=EndBehavior.Return, hide_player_during_cine:bool=False, lead_in:float=-1.0, leave_player_locked_when_finished:bool=False, lock_player:bool=True, path_name:str=None, result:bool=False, skip_if_same_path:bool=False, start_time_advance:float=None):
		pass

	@single
	def end_cinematic(self, lead_out:float=-1, leave_player_locked:bool=False, path_name:str=None):
		pass

	def cinematic_update(self, event:c_uint=CinematicEvent.Started, overall_time:float=-1, path_name:str=None, path_time:float=-1, waypoint:c_int=-1):
		if event == CinematicEvent.Ended:
			# currently only used by the "play cinematic" command, which needs to reset the HUD here
			self.u_i_message_server_to_single_client(message_name=b"popGameState", args=AMF3({"state": "front_end"}))

	def toggle_ghost_reference_override(self, override:bool=False):
		pass

	def set_ghost_reference_position(self, position:Vector3=None):
		pass

	@single
	def add_camera_effect(self, config:LDF=None, duration:float=-1, effect_id:str=None, effect_type:str=None):
		pass

	@single
	def remove_all_camera_effects(self):
		pass

	@broadcast
	def force_camera_target_cycle(self, force_cycling:bool=False, cycling_mode:c_uint=CyclingMode.AllowCycleTeammates, optional_target:GameObject=None):
		pass
