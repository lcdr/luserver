from bitstream import c_uint
from ...game_object import broadcast, c_int, c_uint64, E, EB, EI, EO, EV, GameObject, OBJ_NONE, Sequence, single
from ...game_object import c_uint as c_uint_
from ...math.vector import Vector3
from ...math.quaternion import Quaternion
from ..pet import PetTamingNotify
from .subcomponent import CharSubcomponent

class CharPet(CharSubcomponent):
	@single
	def notify_pet_taming_minigame(self, pet:GameObject=EO, player_taming:GameObject=EO, force_teleport:bool=EB, notify_type:c_uint_=EI, pets_dest_pos:Vector3=EV, tele_pos:Vector3=EV, tele_rot:Quaternion=Quaternion.identity) -> None:
		pass

	def on_client_exit_taming_minigame(self, voluntary_exit:bool=True) -> None:
		self.notify_pet_taming_minigame(pet=OBJ_NONE, player_taming=OBJ_NONE, force_teleport=False, notify_type=PetTamingNotify.Quit, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation)

	@broadcast
	def pet_taming_try_build_result(self, success:bool=True, num_correct:c_int=0) -> None:
		pass

	@broadcast
	def notify_pet_taming_puzzle_selected(self, bricks:Sequence[c_uint, c_uint]=E) -> None:
		pass

	def on_pet_taming_try_build(self, selections:Sequence[c_uint, c_uint64]=E, client_failed:bool=False) -> None:
		if not client_failed:
			self.pet_taming_try_build_result()
			self.notify_pet_taming_minigame(pet=OBJ_NONE, player_taming=OBJ_NONE, force_teleport=False, notify_type=PetTamingNotify.NamingPet, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation)
