import luserver.components.script as script
from luserver.components.mission import TaskType

# fire going out when sprayed with water not implemented

PROX_RADIUS = 3
SKILL_ID = 43

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		if hasattr(self.object, "render"): # some objects have render disabled for some reason
			self.object.render.play_f_x_effect(name="Burn", effect_type="running", effect_id=295)
			self.object._v_server.physics.add_with_radius(self.object, PROX_RADIUS)

	def on_enter(self, player):
		player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=440)
		self.object.skill.cast_skill(SKILL_ID)
