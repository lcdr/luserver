import luserver.components.script as script
from luserver.bitstream import c_bit, c_int, c_int64
from luserver.components.mission import MissionNPCComponent, MissionState
from luserver.components.inventory import InventoryType

package = {}
package[1946] = 14552
package[1947] = 16496
package[1948] = 16497
package[1949] = 16498

flag = {}
flag[1796] = 2030
flag[1952] = 2031
flag[1959] = 2032
flag[1962] = 2033

class ScriptComponent(script.ScriptComponent):
	def mission_dialogue_o_k(self, address, is_complete:c_bit=None, mission_state:c_int=None, mission_id:c_int=None, responder:c_int64=None):
		MissionNPCComponent.mission_dialogue_o_k(self, address, is_complete, mission_state, mission_id, responder)

		if mission_state == MissionState.ReadyToComplete:
			player = self._v_server.game_objects[responder]

			if mission_id in package:
				player.remove_item_from_inv(InventoryType.Items, lot=package[mission_id])
			elif mission_id in flag:
				player.set_flag(None, True, flag[mission_id])
