from ..bitstream import c_bit, c_int64, c_uint
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .component import Component
from .mission import MissionState, TaskType

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
		player.char.notify_pet_taming_minigame(pet_id=self.object.object_id, player_taming_id=0, force_teleport=True, notify_type=PetTamingNotify.Begin, pets_dest_pos=self.object.physics.position, tele_pos=player.physics.position, tele_rot=player.physics.rotation)
		player.char.notify_pet_taming_puzzle_selected(bricks=[30367, 21, 48729, 1, 6141, 1, 6143, 21])
		#self.flags = 80

	def pet_taming_minigame_result(self, player, success:c_bit=None):
		if success:
			# update missions that have taming this pet as requirement
			for mission in player.char.missions:
				if mission.state == MissionState.Active:
					for task in mission.tasks:
						if task.type == TaskType.TamePet and self.object.lot in task.target:
							mission.increment_task(task, player)

