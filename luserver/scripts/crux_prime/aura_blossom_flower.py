import luserver.scripts.general.flower as script
from luserver.components.mission import TaskType

class ScriptComponent(script.ScriptComponent):
	def on_skill_event(self, caster, event_name):
		if event_name == "waterspray":
			if "blooming" not in self.script_network_vars:
				self.object.physics.drop_loot(12317, caster)
				caster.char.mission.update_mission_task(TaskType.Script, self.object.lot, mission_id=1136)

		super().on_skill_event(caster, event_name)
