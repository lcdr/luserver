import luserver.components.script as script
from pyraknet.bitstream import c_int
from luserver.game_object import GameObject
from luserver.components.mission import TaskType

DEATH_ANIMATION = "big-shark-death"
EATEN_BY_SHARK_ACHIEVEMENTS = 447, 446, 445

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.destructible.simply_die(death_type=DEATH_ANIMATION, killer=self.object)

	def fire_event_server_side(self, args:str=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:GameObject=None):
		if args == "achieve":
			for achievement_id in EATEN_BY_SHARK_ACHIEVEMENTS:
				sender.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=achievement_id)
