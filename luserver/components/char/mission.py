from persistent.mapping import PersistentMapping

from pyraknet.bitstream import c_ubyte

from ...game_object import c_int_, c_int64_, GameObject, Sequence, single
from ...world import server
from ...math.vector import Vector3
from ..inventory import InventoryType, LootType, Stack
from ..mission import check_prereqs, MissionProgress, MissionState, ObtainItemType, TaskType

class CharMission:
	def __init__(self):
		self.missions = PersistentMapping()
		# add achievements
		for mission_id, data in server.db.missions.items():
			is_mission = data[3] # if False, it's an achievement (internally works the same as missions, that's why the naming is weird)
			if not is_mission:
				self.missions[mission_id] = MissionProgress(mission_id, data)

	def add_mission(self, mission_id):
		mission_progress = MissionProgress(mission_id, server.db.missions[mission_id])
		self.missions[mission_id] = mission_progress
		self.notify_mission(mission_id, mission_state=mission_progress.state, sending_rewards=False)
		# obtain item task: update according to items already in inventory
		for task in mission_progress.tasks:
			if task.type == TaskType.ObtainItem:
				for item in self.object.inventory.items:
					if item is not None and item.lot in task.target:
						self.update_mission_task(TaskType.ObtainItem, item.lot, increment=item.count, mission_id=mission_id)
						if task.value == task.target_value:
							break

		return mission_progress

	def update_mission_task(self, task_type, target, parameter=None, increment=1, mission_id=None):
		if mission_id is not None:
			if mission_id not in self.missions:
				return
			missions = (mission_id, self.missions[mission_id]),
		else:
			missions = self.missions.items()
		for mission_id, mission in missions:
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if task.type == task_type:
						if task.value == task.target_value:
							continue
						if task_type in (TaskType.UseEmote, TaskType.UseSkill):
							if parameter not in task.parameter:
								continue
						if task_type == TaskType.MinigameAchievement:
							if parameter[0] != task.parameter or parameter[1] < task.target_value:
								continue
						if isinstance(task.target, tuple):
							if target not in task.target:
								continue
						else:
							if task.target != target:
								continue

						# don't update achievements whose previous tiers haven't been completed
						if not mission.is_mission and not check_prereqs(mission_id, self.object):
							continue

						task_index = mission.tasks.index(task)

						if task.type == TaskType.Collect:
							task.parameter.add(increment)
							task.value = len(task.parameter)
							update = increment
						elif task.type == TaskType.MinigameAchievement:
							task.value = task.target_value
							update = task.value
						else:
							task.value = min(task.value+increment, task.target_value)
							update = task.value
						self.notify_mission_task(mission_id, task_mask=1<<(task_index+1), updates=[update])

						# complete achievements that have all tasks complete
						if not mission.is_mission:
							for task in mission.tasks:
								if task.value < task.target_value:
									break
							else:
								self.complete_mission(mission_id)

	def complete_mission(self, mission_id):
		mission = self.missions[mission_id]
		if mission.state == MissionState.Completed:
			return
		mission.state = MissionState.Completed

		if mission.is_mission:
			source_type = LootType.Mission
		else:
			source_type = LootType.Achievement

		self.notify_mission(mission_id, mission_state=MissionState.Unavailable, sending_rewards=True)
		self.set_currency(currency=self.currency + mission.rew_currency, position=Vector3.zero, source_type=source_type)
		self.modify_lego_score(mission.rew_universe_score, source_type=source_type)

		for task in mission.tasks:
			if task.type == TaskType.ObtainItem and task.parameter == ObtainItemType.RemoveOnComplete:
				self.object.inventory.remove_item(InventoryType.Max, lot=task.target[0], count=task.target_value)

		if mission.rew_max_items:
			self.object.inventory.set_inventory_size(inventory_type=InventoryType.Items, size=len(self.object.inventory.items)+mission.rew_max_items)

		if not mission.is_choice_reward:
			for lot, count in mission.rew_items:
				self.object.inventory.add_item(lot, count, source_type=source_type)

		if mission.rew_emote is not None:
			self.set_emote_lock_state(lock=False, emote_id=mission.rew_emote)

		self.object.stats.max_life += mission.rew_max_life
		self.object.stats.max_imagination += mission.rew_max_imagination

		self.notify_mission(mission_id, mission_state=MissionState.Completed, sending_rewards=False)

		# No longer required, delete to free memory in db

		del mission.tasks
		del mission.rew_currency
		del mission.rew_universe_score
		del mission.is_choice_reward
		del mission.rew_items
		del mission.rew_emote
		del mission.rew_max_life
		del mission.rew_max_imagination
		del mission.rew_max_items
		del mission.is_mission

		self.update_mission_task(TaskType.MissionComplete, mission_id)

		if mission_id in server.db.mission_mail:
			for id, attachment_lot in server.db.mission_mail[mission_id]:
				if attachment_lot is not None:
					object_id = server.new_object_id()
					attachment = Stack(server.db, object_id, attachment_lot)
				else:
					attachment = None
				server.mail.send_mail("%[MissionEmail_{id}_senderName]".format(id=id), "%[MissionEmail_{id}_subjectText]".format(id=id), "%[MissionEmail_{id}_bodyText]".format(id=id), self.object, attachment)

	@single
	def offer_mission(self, mission_id:c_int_=None, offerer:GameObject=None):
		pass

	def respond_to_mission(self, mission_id:c_int_=None, player_id:c_int64_=None, receiver:GameObject=None, reward_item:c_int_=-1):
		assert player_id == self.object.object_id
		if reward_item != -1:
			mission = self.missions[mission_id]
			for lot, count in mission.rew_items:
				if lot == reward_item:
					self.object.inventory.add_item(lot, count, source_type=LootType.Mission)
					break
		receiver.handle("respond_to_mission", mission_id, self.object, reward_item, silent=True)

	@single
	def notify_mission(self, mission_id:c_int_=None, mission_state:c_int_=None, sending_rewards:bool=False):
		pass

	@single
	def notify_mission_task(self, mission_id:c_int_=None, task_mask:c_int_=None, updates:Sequence[c_ubyte, float]=None):
		pass
