from typing import cast

import luserver.components.script as script
from luserver.game_object import PhysicsObject
from luserver.world import server

class ScriptComponent(script.ScriptComponent):
	def on_enter(self, player):
		teleport_obj = cast(PhysicsObject, server.get_objects_in_group("Teleport")[0])
		player.char.teleport(ignore_y=False, pos=teleport_obj.physics.position, set_rotation=True, x=teleport_obj.physics.rotation.x, y=teleport_obj.physics.rotation.y, z=teleport_obj.physics.rotation.z, w=teleport_obj.physics.rotation.w)
