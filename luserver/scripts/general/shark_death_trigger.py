import luserver.components.script as script
from luserver.bitstream import c_int
from luserver.game_object import GameObject
from luserver.components.mission import TaskType

DEATH_ANIMATION = "big-shark-death"
EATEN_BY_SHARK_ACHIEVEMENTS = 447, 446, 445

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		player.destructible.request_die(unknown_bool=False, death_type=DEATH_ANIMATION, direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, killer_id=self.object.object_id, loot_owner_id=0)

	def fire_event_server_side(self, args:str=None, param1:c_int=-1, param2:c_int=-1, param3:c_int=-1, sender:GameObject=None):
		if args == "achieve":
			for achievement_id in EATEN_BY_SHARK_ACHIEVEMENTS:
				sender.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=achievement_id)
