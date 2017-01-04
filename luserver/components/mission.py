import logging

from persistent import Persistent

from ..bitstream import c_bit, c_int, c_int64
from ..messages import single
from .component import Component

log = logging.getLogger(__name__)

class TaskType:
	KillEnemy = 0
	Script = 1
	QuickBuild = 2
	Collect = 3
	GoToNPC = 4
	UseEmote = 5
	UseConsumable = 9
	UseSkill = 10
	ObtainItem = 11
	Discover = 12
	MinigameAchievement = 14
	Interact = 15
	MissionComplete = 16
	TamePet = 22
	# CompleteRace = 23 ? or CompleteActivity or something?
	Flag = 24

class MissionState:
	Unavailable = 0
	Available = 1
	Active = 2
	ReadyToComplete = 4
	Completed = 8

def check_prereqs(mission_id, player):
	prereqs = player._v_server.db.missions[mission_id][1]
	for prereq_ors in prereqs:
		for prereq_mission in prereq_ors:
			if isinstance(prereq_mission, tuple): # prereq requires special mission state
				prereq_mission, prereq_mission_state = prereq_mission
			else:
				prereq_mission_state = MissionState.Completed
			if prereq_mission in player.char.missions and player.char.missions[prereq_mission].state == prereq_mission_state:
				break # an element was found, this prereq_ors is satisfied
		else:
			break # no elements found, not satisfied, checking further prereq_ors unnecessary
	else: # all preconditions satisfied
		return True
	return False

class MissionTask(Persistent):
	def __init__(self, task_type, target, target_value, parameter):
		self.type = task_type
		self.target = target
		self.value = 0
		self.target_value = target_value
		if task_type == TaskType.Collect:
			parameter = set() # used for collectibles
		self.parameter = parameter

class MissionProgress(Persistent):
	def __repr__(self):
		return "<MissionProgress state=%i>" % self.state

	def __init__(self, id, mission_data):
		self.state = MissionState.Active
		rewards = mission_data[0]
		self.rew_currency = rewards[0]
		self.rew_universe_score = rewards[1]
		self.is_choice_reward = rewards[2]
		self.rew_items = rewards[3]
		self.rew_emote = rewards[4]
		self.rew_max_life = rewards[5]
		self.rew_max_imagination = rewards[6]
		self.rew_max_items = rewards[7]
		self.tasks = [MissionTask(task_type, target, target_value, parameter) for task_type, target, target_value, parameter in mission_data[2]]
		self.is_mission = mission_data[3]

class MissionNPCComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.mission = self
		self.missions = self.object._v_server.db.mission_npc_component[comp_id]

	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		offer = None
		if multi_interact_id is not None:
			offer = multi_interact_id
		else:
			for mission_id, offers_mission, accepts_mission in self.missions:
				if mission_id in player.char.missions:
					if accepts_mission and player.char.missions[mission_id].state == MissionState.Active:
						log.debug("mission %i in progress, offering", mission_id)
						offer = mission_id
						break
				elif offers_mission:
					log.debug("assessing %i", mission_id)
					if check_prereqs(mission_id, player):
						offer = mission_id

		if offer is not None:
			log.debug("offering %i", offer)
			self.offer_mission(offer, offerer=self.object.object_id, player=player)
			player.char.offer_mission(offer, offerer=self.object.object_id)

		return offer is not None

	@single
	def offer_mission(self, mission_id:c_int=None, offerer:c_int64=None):
		pass

	def mission_dialogue_o_k(self, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		player = self.object._v_server.game_objects[responder]

		if mission_state == MissionState.Available:
			assert not is_complete
			player.char.add_mission(mission_id)

		elif mission_state == MissionState.ReadyToComplete:
			assert is_complete
			player.char.complete_mission(mission_id)

	def request_linked_mission(self, player_id:c_int64=None, mission_id:c_int=None, mission_offered:c_bit=None):
		player = self.object._v_server.game_objects[player_id]
		self.on_use(player, None)
