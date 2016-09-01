from ..bitstream import c_bit, c_int64, c_uint
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .mission import MissionState, TaskType

class PetTamingNotify:
	Success = 0
	Quit = 1
	Failed = 2
	Begin = 3
	Ready = 4
	NamingPet = 5

class PetComponent:
	def __init__(self, comp_id):
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
		self._v_server.send_game_message(player.notify_pet_taming_minigame, pet_id=self.object_id, player_taming_id=0, force_teleport=True, notify_type=PetTamingNotify.Begin, pets_dest_pos=self.position, tele_pos=player.position, tele_rot=player.rotation, address=player.address)
		self._v_server.send_game_message(player.notify_pet_taming_puzzle_selected, bricks=[30367, 21, 48729, 1, 6141, 1, 6143, 21], address=player.address)
		#self.flags = 80

	def notify_pet_taming_minigame(self, address, pet_id:c_int64=None, player_taming_id:c_int64=None, force_teleport:c_bit=None, notify_type:c_uint=None, pets_dest_pos:Vector3=None, tele_pos:Vector3=None, tele_rot:Quaternion=Quaternion.identity):
		pass

	def pet_taming_minigame_result(self, address, success:c_bit=None):
		if success:
			player = self._v_server.accounts[address].characters.selected()
			# update missions that have taming this pet as requirement
			for mission in player.missions:
				if mission.state == MissionState.Active:
					for task in mission.tasks:
						if task.type == TaskType.TamePet and self.lot in task.target:
							mission.increment_task(task, player)

