from ...game_object import c_int, EB, EI, EL, EO, ES, GameObject, OBJ_NONE, single
from ...ldf import LDF
from .subcomponent import CharSubcomponent

class CharUI(CharSubcomponent):
	@single
	def display_message_box(self, show:bool=EB, callback_client:GameObject=EO, id:str=ES, image_id:c_int=EI, text:str=ES, user_data:str=ES) -> None:
		pass

	def disp_message_box(self, text: str, id: str="", callback: GameObject=OBJ_NONE) -> None:
		"""display_message_box with default parameters."""
		self.display_message_box(show=True, callback_client=callback, id=id, image_id=0, text=text, user_data="")

	@single
	def display_tooltip(self, do_or_die:bool=False, no_repeat:bool=False, no_revive:bool=False, is_property_tooltip:bool=False, show:bool=EB, translate:bool=False, time:c_int=EI, id:str=ES, localize_params:LDF=EL, image_name:str=ES, text:str=ES) -> None:
		pass

	def disp_tooltip(self, text: str) -> None:
		"""display_tooltip with default parameters"""
		self.display_tooltip(show=True, time=1000, id="", localize_params=LDF(), image_name="", text=text)
