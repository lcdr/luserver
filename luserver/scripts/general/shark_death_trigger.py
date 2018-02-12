import luserver.components.script as script
from luserver.game_object import c_int, EP, ES, Player
from luserver.components.mission import TaskType

DEATH_ANIMATION = "big-shark-death"
EATEN_BY_SHARK_ACHIEVEMENTS = 447, 446, 445

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.destructible.simply_die(death_type=DEATH_ANIMATION, killer=self.object)

	def on_fire_event_server_side(self, args:str=ES, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:Player=EP):
		if args == "achieve":
			for achievement_id in EATEN_BY_SHARK_ACHIEVEMENTS:
				sender.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=achievement_id)
