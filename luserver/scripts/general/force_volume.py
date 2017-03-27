import luserver.components.script as script
from luserver.components.physics import PhysicsEffect
from luserver.math.vector import Vector3

class ScriptComponent(script.ScriptComponent):
	def on_startup(self):
		self.object.physics.physics_effect_active = True
		self.object.physics.physics_effect_type = PhysicsEffect.Push
		self.object.physics.physics_effect_amount = self.script_vars["force_amount"]
		self.object.physics.physics_effect_direction = self.script_vars["force"]*self.object.physics.physics_effect_amount
