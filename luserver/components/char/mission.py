from persistent.mapping import PersistentMapping

from ...bitstream import c_int, c_int64, c_ubyte
from ...game_object import GameObject
from ...messages import single
from ...math.vector import Vector3
from ..inventory import InventoryType, LootType, Stack
from ..mission import check_prereqs, MissionProgress, MissionState, TaskType

class CharMission:
	def __init__(self):
		self.autocomplete_missions = False
		self.missions = PersistentMapping()
		# add achievements
		for mission_id, data in self.object._v_server.db.missions.items():
			is_mission = data[3] # if False, it's an achievement (internally works the same as missions, that's why the naming is weird)
			if not is_mission:
				self.missions[mission_id] = MissionProgress(mission_id, data)

	def add_mission(self, mission_id):
		mission_progress = MissionProgress(mission_id, self.object._v_server.db.missions[mission_id])
		self.missions[mission_id] = mission_progress
		self.notify_mission(mission_id, mission_state=mission_progress.state, sending_rewards=False)
		# obtain item task: update according to items already in inventory
		for task in mission_progress.tasks:
			if task.type == TaskType.ObtainItem:
				for item in self.object.inventory.items:
					if item is not None and item.lot in task.target:
						self.update_mission_task(TaskType.ObtainItem, item.lot, increment=item.amount, mission_id=mission_id)
						if task.value == task.target_value:
							break

		self.object._v_server.commit()
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

		if not mission.is_choice_reward:
			for lot, amount in mission.rew_items:
				self.object.inventory.add_item_to_inventory(lot, amount, source_type=source_type)

		if mission.rew_emote is not None:
			self.set_emote_lock_state(lock=False, emote_id=mission.rew_emote)

		self.object.stats.max_life += mission.rew_max_life
		self.object.stats.max_imagination += mission.rew_max_imagination

		if mission.rew_max_items:
			self.object.inventory.set_inventory_size(inventory_type=InventoryType.Items, size=len(self.object.inventory.items)+mission.rew_max_items)

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

		if mission_id in self.object._v_server.db.mission_mail:
			for id, attachment_lot in self.object._v_server.db.mission_mail[mission_id]:
				if attachment_lot is not None:
					object_id = self.object._v_server.new_object_id()
					attachment = Stack(self.object._v_server.db, object_id, attachment_lot)
				else:
					attachment = None
				self.object._v_server.mail.send_mail("%[MissionEmail_{id}_senderName]".format(id=id), "%[MissionEmail_{id}_subjectText]".format(id=id), "%[MissionEmail_{id}_bodyText]".format(id=id), self.object, attachment)

		self.object._v_server.commit()

	@single
	def offer_mission(self, mission_id:c_int=None, offerer:GameObject=None):
		pass

	def respond_to_mission(self, mission_id:c_int=None, player_id:c_int64=None, receiver:GameObject=None, reward_item:c_int=-1):
		assert player_id == self.object.object_id
		if reward_item != -1:
			mission = self.missions[mission_id]
			for lot, amount in mission.rew_items:
				if lot == reward_item:
					self.object.inventory.add_item_to_inventory(lot, amount, source_type=LootType.Mission)
					break
		receiver.handle("respond_to_mission", mission_id, self.object, reward_item, silent=True)

	@single
	def notify_mission(self, mission_id:c_int=None, mission_state:c_int=None, sending_rewards:bool=False):
		pass

	@single
	def notify_mission_task(self, mission_id:c_int=None, task_mask:c_int=None, updates:(c_ubyte, float)=None):
		pass
