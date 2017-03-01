import luserver.components.script as script
from luserver.components.mission import TaskType
from luserver.ldf import LDFDataType

FLOWER_MISSIONS = 143, 152, 153, 1409, 1507, 1544, 1581, 1845

class ScriptComponent(script.ScriptComponent):
	def on_skill_event(self, caster, event_name):
		if event_name == "waterspray":
			if not "blooming" in self.script_network_vars:
				self.set_network_var("blooming", LDFDataType.BOOLEAN, True)
				for mission_id in FLOWER_MISSIONS:
					caster.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=mission_id)
				self.object.call_later(16, lambda: self.object.destructible.request_die(unknown_bool=False, death_type="", direction_relative_angle_xz=0, direction_relative_angle_y=0, direction_relative_force=0, killer_id=caster.object_id, loot_owner_id=0))
