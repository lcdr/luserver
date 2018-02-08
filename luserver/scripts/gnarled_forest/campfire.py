import luserver.components.script as script
from luserver.components.mission import TaskType

# fire going out when sprayed with water not implemented

PROX_RADIUS = 3
SKILL_ID = 43

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		if hasattr(self.object, "render"): # some objects have render disabled for some reason
			self.light_fire()
			self.object.physics.proximity_radius(PROX_RADIUS)

	def light_fire(self):
		self.is_burning = True
		self.object.render.stop_f_x_effect(name=b"Off")
		self.object.render.play_f_x_effect(name=b"Burn", effect_type="running", effect_id=295)

	def on_enter(self, player):
		if self.is_burning:
			player.char.update_mission_task(TaskType.Script, self.object.lot, mission_id=440)
			self.object.skill.cast_skill(SKILL_ID)

	def on_skill_event(self, caster, event_name):
		if event_name == "waterspray":
			self.is_burning = False
			self.object.render.stop_f_x_effect(name=b"Burn")
			self.object.render.play_f_x_effect(name=b"Off", effect_type="idle", effect_id=295)
			self.object.call_later(37, self.light_fire)
