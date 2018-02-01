from pyraknet.bitstream import c_uint
from ...game_object import broadcast, c_int, c_uint64, E, GameObject, OBJ_NONE, Player, Sequence, single
from ...game_object import c_uint as c_uint_
from ...math.vector import Vector3
from ...math.quaternion import Quaternion
from ..pet import PetTamingNotify

class CharPet:
	object: Player

	@single
	def notify_pet_taming_minigame(self, pet:GameObject=E, player_taming:GameObject=E, force_teleport:bool=E, notify_type:c_uint_=E, pets_dest_pos:Vector3=E, tele_pos:Vector3=E, tele_rot:Quaternion=Quaternion.identity) -> None:
		pass

	def client_exit_taming_minigame(self, voluntary_exit:bool=True) -> None:
		self.notify_pet_taming_minigame(pet=OBJ_NONE, player_taming=OBJ_NONE, force_teleport=False, notify_type=PetTamingNotify.Quit, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation)

	@broadcast
	def pet_taming_try_build_result(self, success:bool=True, num_correct:c_int=0) -> None:
		pass

	@broadcast
	def notify_pet_taming_puzzle_selected(self, bricks:Sequence[c_uint, c_uint]=E) -> None:
		pass

	def pet_taming_try_build(self, selections:Sequence[c_uint, c_uint64]=E, client_failed:bool=False) -> None:
		if not client_failed:
			self.pet_taming_try_build_result()
			self.notify_pet_taming_minigame(pet=OBJ_NONE, player_taming=OBJ_NONE, force_teleport=False, notify_type=PetTamingNotify.NamingPet, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation)
