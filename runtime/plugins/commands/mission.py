import asyncio

from luserver.world import server
from luserver.components.mission import MissionProgress, MissionState
from luserver.interfaces.plugin import ChatCommand

class AddMission(ChatCommand):
	def __init__(self):
		super().__init__("addmission")
		self.command.add_argument("mission")

	def run(self, args, sender):
		if args.mission in MISSIONS:
			for mission_id in MISSIONS[args.mission]:
				sender.char.mission.add_mission(mission_id)
		else:
			sender.char.mission.add_mission(int(args.mission))

class CompleteMission(ChatCommand):
	def __init__(self):
		super().__init__("completemission")
		self.command.add_argument("mission")
		self.command.add_argument("--upto", action="store_true")
		self.command.add_argument("--fully", action="store_true")

	def run(self, args, sender):
		if args.upto:
			args.fully = True
			mission_id = int(args.mission)
			missions = self.find_prereqs(mission_id)
		elif args.mission in MISSIONS:
			missions = MISSIONS[args.mission]
		else:
			missions = [int(args.mission)]
		for mission_id in missions:
			asyncio.get_event_loop().call_soon(self.async_complete_mission, mission_id, args.fully, sender)

	def find_prereqs(self, mission_id):
		missions = set()
		prereqs = server.db.missions[mission_id][1]
		for prereq_ors in prereqs:
			for prereq_mission in prereq_ors:
				if isinstance(prereq_mission, tuple): # prereq requires special mission state
					prereq_mission, prereq_mission_state = prereq_mission
				else:
					prereq_mission_state = MissionState.Completed
				missions.add(prereq_mission)
				missions.update(self.find_prereqs(prereq_mission))
		return missions

	def async_complete_mission(self, mission_id, fully, sender):
		if mission_id not in sender.char.mission.missions:
			sender.char.mission.add_mission(mission_id)

		if fully:
			sender.char.mission.complete_mission(mission_id)
		else:
			mission = sender.char.mission.missions[mission_id]
			if mission.state == MissionState.Active:
				for task in mission.tasks:
					if isinstance(task.target, tuple):
						target = task.target[0]
					else:
						target = task.target
					if isinstance(task.parameter, tuple) and task.parameter:
						parameter = task.parameter[0]
					else:
						parameter = None
					sender.char.mission.update_mission_task(task.type, target, parameter, increment=task.target_value, mission_id=mission_id)

class RemoveMission(ChatCommand):
	def __init__(self):
		super().__init__("removemission")
		self.command.add_argument("id", type=int)

	def run(self, args, sender):
		if args.id in sender.char.mission.missions:
			del sender.char.mission.missions[args.id]
			server.chat.sys_msg_sender("Mission removed")
		else:
			server.chat.sys_msg_sender("Mission not found")

class ResetMissions(ChatCommand):
	def __init__(self):
		super().__init__("resetmissions")

	def run(self, args, sender):
		sender.char.mission.missions.clear()
		# add achievements
		for mission_id, data in server.db.missions.items():
			is_mission = data[3] # if False, it's an achievement (internally works the same as missions, that's why the naming is weird)
			if not is_mission:
				sender.char.mission.missions[mission_id] = MissionProgress(mission_id, data)

MISSIONS = {
	"VE": [1727, 173, 660, 1896, 308, 1732],
	"AG": [311, 755, 312, 314, 315, 733, 316, 939, 940, 479, 1847, 1848, 477, 1151, 1849, 1850, 1851, 1852, 1935, 313, 1853, 1936, 317, 1854, 1855, 1856, 318, 633, 377, 1950, 768, 870, 871, 891, 320],
	"NS-pre-faction": [483, 476, 809, 475, 478, 482],
	"GF": [220, 301, 380, 541, 382, 383, 384, 329, 228, 229, 230],
	"FV": [493, 490, 496, 498, 509, 594, 689, 513, 763]}
