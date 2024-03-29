import luserver.components.script as script
from luserver.components.physics import PhysicsEffect

class ScriptComponent(script.ScriptComponent):
	def on_startup(self) -> None:
		self.object.physics.physics_effect_active = True
		self.object.physics.physics_effect_type = PhysicsEffect.Friction
		self.object.physics.physics_effect_amount = self.script_vars["friction_amount"]
