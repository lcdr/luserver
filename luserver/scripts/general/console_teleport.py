import asyncio

import luserver.components.script as script

# todo: not completely implemented

class ScriptComponent(script.ScriptComponent):
	def transfer(self, player, world, respawn_point_name):
		player.render.play_animation("lup-teleport")
		asyncio.get_event_loop().call_later(4, asyncio.ensure_future, player.char.transfer_to_world(world, respawn_point_name=respawn_point_name))
