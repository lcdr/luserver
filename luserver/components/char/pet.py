from pyraknet.bitstream import c_int, c_uint, c_uint64
from ...game_object import broadcast, GameObject, Sequence, single
from ...math.vector import Vector3
from ...math.quaternion import Quaternion
from ..pet import PetTamingNotify

class CharPet:
	@single
	def notify_pet_taming_minigame(self, pet:GameObject=None, player_taming:GameObject=None, force_teleport:bool=None, notify_type:c_uint=None, pets_dest_pos:Vector3=None, tele_pos:Vector3=None, tele_rot:Quaternion=Quaternion.identity):
		pass

	def client_exit_taming_minigame(self, voluntary_exit:bool=True):
		self.notify_pet_taming_minigame(pet=None, player_taming=None, force_teleport=False, notify_type=PetTamingNotify.Quit, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation)

	@broadcast
	def pet_taming_try_build_result(self, success:bool=True, num_correct:c_int=0):
		pass

	@broadcast
	def notify_pet_taming_puzzle_selected(self, bricks:Sequence[c_uint, c_uint]=None):
		pass

	def pet_taming_try_build(self, selections:Sequence[c_uint, c_uint64]=None, client_failed:bool=False):
		if not client_failed:
			self.pet_taming_try_build_result()
			self.notify_pet_taming_minigame(pet=None, player_taming=None, force_teleport=False, notify_type=PetTamingNotify.NamingPet, pets_dest_pos=self.object.physics.position, tele_pos=self.object.physics.position, tele_rot=self.object.physics.rotation)
