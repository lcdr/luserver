
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
	CollectPowerup = 21
	TamePet = 22
	# CompleteRace = 23 ? or CompleteActivity or something?
	Flag = 24

class MissionState:
	Unavailable = 0
	Available = 1
	Active = 2
	ReadyToComplete = 4
	Completed = 8
	# daily missions
	CompletedAvailable = 9
	CompletedActive = 10
	CompletedReadyToComplete = 12

class ObtainItemType:
	RemoveOnComplete = 2

from persistent import Persistent
from ..commonserver import MissionData

class MissionTask(Persistent):
	def __init__(self, task_type: int, target: int, target_value: int, parameter):
		self.type = task_type
		self.target = target
		self.value = 0
		self.target_value = target_value
		if task_type == TaskType.Collect:
			parameter = set() # used for collectibles
		self.parameter = parameter

class MissionProgress(Persistent):
	def __repr__(self) -> str:
		return "<MissionProgress state=%i>" % self.state

	def __init__(self, id: int, mission_data: MissionData):
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

import logging
import random
from typing import Dict, Optional

from bitstream import WriteStream
from ..game_object import c_int, Config, EB, EI, EO, EP, GameObject, ObjectID, Player, single
from ..world import server
from .component import Component

log = logging.getLogger(__name__)

def check_prereqs(mission_id: int, player: Player) -> bool:
	prereqs = server.db.missions[mission_id][1]
	for prereq_ors in prereqs:
		for prereq_mission in prereq_ors:
			if isinstance(prereq_mission, tuple): # prereq requires special mission state
				prereq_mission, prereq_mission_state = prereq_mission
			else:
				prereq_mission_state = MissionState.Completed
			if prereq_mission in player.char.mission.missions and player.char.mission.missions[prereq_mission].state == prereq_mission_state:
				break # an element was found, this prereq_ors is satisfied
		else:
			break # no elements found, not satisfied, checking further prereq_ors unnecessary
	else: # all preconditions satisfied
		return True
	return False

class MissionNPCComponent(Component):
	def __init__(self, obj: GameObject, set_vars: Config, comp_id: int):
		super().__init__(obj, set_vars, comp_id)
		self.object.mission = self
		self.missions = server.db.mission_npc_component[comp_id]
		self.random_mission_choices: Dict[ObjectID, int] = {}

	def serialize(self, out: WriteStream, is_creation: bool) -> None:
		pass

	def on_use(self, player: Player, multi_interact_id: Optional[int]) -> bool:
		offer = None
		if multi_interact_id is not None:
			offer = multi_interact_id
		else:
			for mission_id, offers_mission, accepts_mission in self.missions:
				if mission_id in player.char.mission.missions:
					if accepts_mission and player.char.mission.missions[mission_id].state == MissionState.Active:
						log.debug("mission %i in progress, offering", mission_id)
						offer = mission_id
						break
				elif offers_mission:
					log.debug("assessing %i", mission_id)
					is_random = server.db.missions[mission_id][4]
					random_pool = server.db.missions[mission_id][5]
					if is_random:
						if random_pool and check_prereqs(mission_id, player):
							if player.object_id not in self.random_mission_choices:
								eligible_missions = []
								for random_mission_id in random_pool:
									if random_mission_id not in player.char.mission.missions:
										eligible_missions.append(random_mission_id)
								if not eligible_missions:
									continue
								offer = random.choice(eligible_missions)
								log.debug("choosing random mission %i", offer)
								# save the random choice so the player can't cycle through random missions
								self.random_mission_choices[player.object_id] = offer
								# todo: fix this
								# disabling for now because handlers accidentally get saved to DB
								#player.add_handler("destruction", self.clear_random_missions)
							else:
								offer = self.random_mission_choices[player.object_id]
								log.debug("choosing saved random mission %i", offer)
					elif check_prereqs(mission_id, player):
						offer = mission_id

		if offer is not None:
			log.debug("offering %i", offer)
			self.offer_mission(offer, offerer=self.object, player=player)
			player.char.mission.offer_mission(offer, offerer=self.object)

		return offer is not None

	@single
	def offer_mission(self, mission_id:c_int=EI, offerer:GameObject=EO) -> None:
		pass

	def on_mission_dialogue_o_k(self, is_complete:bool=EB, mission_state:c_int=EI, mission_id:c_int=EI, player:Player=EP) -> None:
		if mission_state == MissionState.Available:
			assert not is_complete
			player.char.mission.add_mission(mission_id)
		elif mission_state == MissionState.ReadyToComplete:
			assert is_complete
			player.char.mission.complete_mission(mission_id)
			self.clear_random_missions(player)

	def on_request_linked_mission(self, player:Player=EP, mission_id:c_int=EI, mission_offered:bool=EB) -> None:
		self.on_use(player, None)

	def clear_random_missions(self, player: Player) -> None:
		if player.object_id in self.random_mission_choices:
			del self.random_mission_choices[player.object_id]
