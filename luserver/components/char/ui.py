from ...game_object import c_int_, GameObject, single
from ...ldf import LDF

class CharUI:
	@single
	def display_message_box(self, show:bool=None, callback_client:GameObject=None, id:str=None, image_id:c_int_=None, text:str=None, user_data:str=None):
		pass

	def disp_message_box(self, text, id="", callback=None):
		"""display_message_box with default parameters."""
		self.display_message_box(show=True, callback_client=callback, id=id, image_id=0, text=text, user_data="")

	@single
	def display_tooltip(self, do_or_die:bool=False, no_repeat:bool=False, no_revive:bool=False, is_property_tooltip:bool=False, show:bool=None, translate:bool=False, time:c_int_=None, id:str=None, localize_params:LDF=None, image_name:str=None, text:str=None):
		pass

	def disp_tooltip(self, text):
		"""display_tooltip with default parameters"""
		self.display_tooltip(show=True, time=1000, id="", localize_params=LDF(), image_name="", text=text)
