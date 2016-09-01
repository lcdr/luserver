import logging

from persistent import Persistent

from ..bitstream import c_bit, c_int, c_int64
from ..math.vector import Vector3
from .inventory import InventoryType

log = logging.getLogger(__name__)

class LootType: # doesn't really belong in this module but currently is only used from this module
	Mission = 2
	Achievement = 5
	# loot drop = 11 ?

class TaskType:
	KillEnemy = 0
	Script = 1
	QuickBuild = 2
	Collect = 3
	GoToNPC = 4
	UseEmote = 5
	# ??? = 9 # use collectible?
	UseSkill = 10
	ObtainItem = 11
	# Discover = 12 # needs physics
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
	player_missions = {mission.id: mission.state for mission in player.missions}
	prereqs = player._v_server.db.missions[mission_id][1]
	for prereq_ors in prereqs:
		for prereq_mission in prereq_ors:
			if isinstance(prereq_mission, tuple): # prereq requires special mission state
				prereq_mission, prereq_mission_state = prereq_mission
			else:
				prereq_mission_state = MissionState.Completed
			if prereq_mission in player_missions and player_missions[prereq_mission] == prereq_mission_state:
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
		self.parameter = parameter

class MissionProgress(Persistent):
	def __repr__(self):
		return "<MissionProgress id=%i state=%i>" % (self.id, self.state)

	def __init__(self, id, mission_data):
		self.id = id
		self.state = MissionState.Active
		rewards = mission_data[0]
		self.rew_currency = rewards[0]
		self.rew_universe_score = rewards[1]
		self.rew_items = rewards[2]
		self.rew_emote = rewards[3]
		self.rew_max_life = rewards[4]
		self.rew_max_imagination = rewards[5]
		self.rew_max_items = rewards[6]
		self.tasks = [MissionTask(task_type, target, target_value, parameter) for task_type, target, target_value, parameter in mission_data[2]]
		self.is_mission = mission_data[3]

	def increment_task(self, task, player, increment=1):
		if task.value == task.target_value:
			return
		if not self.is_mission and not check_prereqs(self.id, player):
			return

		task.value = min(task.value+increment, task.target_value)
		task_index = self.tasks.index(task)
		player._v_server.send_game_message(player.notify_mission_task, self.id, task_mask=1<<(task_index+1), updates=[task.value], address=player.address)
		if not self.is_mission:
			for task in self.tasks:
				if task.value < task.target_value:
					break
			else:
				self.complete(player)

	def complete(self, player):
		self.state = MissionState.Completed

		if self.is_mission:
			source_type = LootType.Mission
		else:
			source_type = LootType.Achievement

		player._v_server.send_game_message(player.notify_mission, self.id, mission_state=MissionState.Unavailable, sending_rewards=True, address=player.address)
		player._v_server.send_game_message(player.set_currency, currency=player.currency + self.rew_currency, position=Vector3.zero, source_type=source_type, address=player.address)
		player._v_server.send_game_message(player.modify_lego_score, self.rew_universe_score, source_type=source_type, address=player.address)

		for lot, amount in self.rew_items:
			player.add_item_to_inventory(lot, amount, source_type=source_type)

		if self.rew_emote is not None:
			player._v_server.send_game_message(player.set_emote_lock_state, lock=False, emote_id=self.rew_emote, address=player.address)

		player.max_life += self.rew_max_life
		player.max_imagination += self.rew_max_imagination

		if self.rew_max_items:
			player._v_server.send_game_message(player.set_inventory_size, inventory_type=InventoryType.Items, size=len(player.items)+self.rew_max_items, address=player.address)

		player._v_server.send_game_message(player.notify_mission, self.id, mission_state=MissionState.Completed, sending_rewards=False, address=player.address)

		# No longer required, delete to free memory in db

		del self.tasks
		del self.rew_currency
		del self.rew_universe_score
		del self.rew_items
		del self.rew_emote
		del self.rew_max_life
		del self.rew_max_imagination
		del self.rew_max_items
		del self.is_mission

		# Update missions that check if this mission was completed

		for mission in player.missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == TaskType.MissionComplete and self.id in task.target:
						mission.increment_task(task, player)

		player._v_server.commit()

class MissionNPCComponent:
	def __init__(self, comp_id):
		self.missions = self._v_server.db.mission_npc_component[comp_id]

	def serialize(self, out, is_creation):
		pass

	def on_use(self, player, multi_interact_id):
		offer = None
		if multi_interact_id is not None:
			offer = multi_interact_id
		else:
			player_missions = {mission.id: mission.state for mission in player.missions}

			for mission_id, offers_mission, accepts_mission in self.missions:
				if mission_id in player_missions:
					if accepts_mission and player_missions[mission_id] == MissionState.Active:
						log.debug("mission %i in progress, offering", mission_id)
						offer = mission_id
						break
				elif offers_mission:
					log.debug("assessing %i", mission_id)
					if check_prereqs(mission_id, player):
						offer = mission_id

		if offer is not None:
			log.debug("offering %i", offer)
			self._v_server.send_game_message(self.offer_mission, offer, offerer=self.object_id, address=player.address)
			self._v_server.send_game_message(player.offer_mission, offer, offerer=self.object_id, address=player.address)

		return offer is not None

	def respond_to_mission(self, address, mission_id, player, reward_item):
		pass

	def offer_mission(self, address, mission_id:c_int=None, offerer:c_int64=None):
		pass

	def mission_dialogue_o_k(self, address, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		player = self._v_server.game_objects[responder]

		if mission_state == MissionState.Available:
			assert not is_complete
			player.add_mission(mission_id)

		elif mission_state == MissionState.ReadyToComplete:
			assert is_complete
			for mission_progress in player.missions:
				if mission_progress.id == mission_id:
					mission_progress.complete(player)
					break

	def request_linked_mission(self, address, player_id:c_int64=None, mission_id:c_int=None, mission_offered:c_bit=None):
		player = self._v_server.game_objects[player_id]
		MissionNPCComponent.on_use(self, player, None)
