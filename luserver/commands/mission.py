import asyncio

from ..components.mission import MissionProgress, MissionState
from .command import ChatCommand

class AddMissionCommand(ChatCommand):
	def __init__(self, chat):
		super().__init__(chat, "addmission")
		self.command.add_argument("mission")

	def run(self, args, sender):
		if args.mission in MISSIONS:
			for mission_id in MISSIONS[args.mission]:
				sender.char.add_mission(mission_id)
		else:
			sender.char.add_mission(int(args.mission))

class CompleteMissionCommand(ChatCommand):
	def __init__(self, chat):
		super().__init__(chat, "completemission")
		self.command.add_argument("mission")
		self.command.add_argument("--fully", action="store_true")

	def run(self, args, sender):
		if args.mission in MISSIONS:
			missions = MISSIONS[args.mission]
		else:
			missions = [int(args.mission)]
		for mission_id in missions:
			asyncio.get_event_loop().call_soon(self.async_complete_mission, mission_id, args.fully, sender)

	def async_complete_mission(self, mission_id, fully, sender):
		if mission_id not in sender.char.missions:
			sender.char.add_mission(mission_id)

		if fully:
			sender.char.complete_mission(mission_id)
		else:
			mission = sender.char.missions[mission_id]
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if isinstance(task.target, tuple):
						target = task.target[0]
					else:
						target = task.target
					sender.char.update_mission_task(task.type, target, increment=task.target_value, mission_id=mission_id)

class RemoveMissionCommand(ChatCommand):
	def __init__(self, chat):
		super().__init__(chat, "removemission")
		self.command.add_argument("id", type=int)

	def run(self, args, sender):
		if args.id in sender.char.missions:
			del sender.char.missions[args.id]
			self.chat.sys_msg_sender("Mission removed")
		else:
			self.chat.sys_msg_sender("Mission not found")

class RemoveMissionCommand(ChatCommand):
	def __init__(self, chat):
		super().__init__(chat, "removemission")

	def run(self, args, sender):
		sender.char.missions.clear()
		# add achievements
		for mission_id, data in self.server.db.missions.items():
			is_mission = data[3] # if False, it's an achievement (internally works the same as missions, that's why the naming is weird)
			if not is_mission:
				sender.char.missions[mission_id] = MissionProgress(mission_id, data)

MISSIONS = {
	"VE": [1727, 173, 660, 1896, 308, 1732],
	"AG": [311, 755, 312, 314, 315, 733, 316, 939, 940, 479, 1847, 1848, 477, 1151, 1849, 1850, 1851, 1852, 1935, 313, 1853, 1936, 317, 1854, 1855, 1856, 318, 633, 377, 1950, 768, 870, 871, 891, 320],
	"NS-pre-faction": [483, 476, 809, 475, 478, 482],
	"GF": [220, 301, 380, 541, 382, 383, 384, 329, 228, 229, 230],
	"FV": [493, 490, 496, 498, 509, 594, 689, 513, 763]}
