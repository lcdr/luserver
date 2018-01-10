from pyraknet.bitstream import c_float, c_int, c_int64, c_ubyte, c_uint
from ..game_object import broadcast, GameObject
from .component import Component

class RenderComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.render = self
		self.effects = {}

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_uint(len(self.effects)))
			for name, effect_values in self.effects.items():
				effect_id, effect_type = effect_values
				out.write(c_ubyte(len(name)))
				out.write(name)
				out.write(c_int(effect_id))
				out.write(effect_type, length_type=c_ubyte)
				out.write(c_float(1))
				out.write(c_int64(0))

	def on_destruction(self):
		self.effects.clear()

	@broadcast
	def play_animation(self, animation_id:str=None, expect_anim_to_exist:bool=True, play_immediate:bool=False, trigger_on_complete_msg:bool=False, priority:float=2, scale:float=1):
		pass

	@broadcast
	def play_f_x_effect(self, effect_id:c_int=-1, effect_type:str=None, scale:float=1, name:bytes=None, priority:float=1, secondary:c_int64=0, serialize:bool=True):
		self.effects[name] = effect_id, effect_type

	@broadcast
	def stop_f_x_effect(self, kill_immediate:bool=False, name:bytes=None):
		if name in self.effects:
			del self.effects[name]

	@broadcast
	def play_embedded_effect_on_all_clients_near_object(self, effect_name:str=None, from_object:GameObject=None, radius:float=None):
		pass

	@broadcast
	def play_n_d_audio_emitter(self, callback_message_data:c_int64=0, emitter_id:c_int=0, event_guid:bytes=None, meta_event_name:bytes=None, result:bool=False, target_object_id_for_ndaudio_callback_messages:c_int64=0):
		pass

	@broadcast
	def freeze_animation(self, do_freeze:bool=None, duration:float=-1, startup_delay:float=0):
		pass
