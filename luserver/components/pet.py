from pyraknet.bitstream import c_bit, c_uint
from ..game_object import E
from .component import Component
from .mission import TaskType

class PetTamingNotify:
	Success = 0
	Quit = 1
	Failed = 2
	Begin = 3
	Ready = 4
	NamingPet = 5

class PetComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.pet = self
		self.flags = 67108866 # possibly the same flags as in the object id?

	def serialize(self, out, is_creation):
		out.write(c_bit(True))
		out.write(c_uint(self.flags))
		out.write(c_uint(0))
		out.write(c_bit(False))
		out.write(c_bit(False))
		out.write(c_bit(False))

	def on_use(self, player, multi_interact_id):
		assert multi_interact_id is None
		player.char.notify_pet_taming_minigame(pet=self.object, player_taming=None, force_teleport=True, notify_type=PetTamingNotify.Begin, pets_dest_pos=self.object.physics.position, tele_pos=player.physics.position, tele_rot=player.physics.rotation)
		player.char.notify_pet_taming_puzzle_selected(bricks=[30367, 21, 48729, 1, 6141, 1, 6143, 21])
		#self.flags = 80

	def pet_taming_minigame_result(self, player, success:bool=E):
		if success:
			player.char.update_mission_task(TaskType.TamePet, self.object.lot)
