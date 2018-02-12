import luserver.components.script as script
from luserver.components.mission import TaskType
from luserver.ldf import LDFDataType

FLOWER_MISSIONS = 143, 152, 153, 1409, 1507, 1544, 1581, 1845

class ScriptComponent(script.ScriptComponent):
	def on_skill_event(self, caster, event_name):
		if event_name == "waterspray":
			if "blooming" not in self.script_network_vars:
				self.set_network_var("blooming", LDFDataType.BOOLEAN, True)
				for mission_id in FLOWER_MISSIONS:
					caster.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=mission_id)
				self.object.call_later(16, lambda: self.object.destructible.simply_die(killer=caster))
