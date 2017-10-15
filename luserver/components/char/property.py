from ...bitstream import BitStream, c_int, c_int64, c_uint
from ...game_object import GameObject
from ...messages import broadcast, single
from ...world import server
from ...math.vector import Vector3
from ...math.quaternion import Quaternion
from ..inventory import InventoryType

class DeleteReason:
	PickingModelUp = 0
	ReturningModelToInventory = 1
	BreakingModelApart = 2

class CharProperty:
	@single
	def place_model_response(self, position:Vector3=Vector3.zero, property_plaque:GameObject=0, response:c_int=0, rotation:Quaternion=Quaternion.identity):
		pass

	def update_model_from_client(self, model_id:c_int64=None, position:Vector3=None, rotation:Quaternion=Quaternion.identity):
		for model in self.object.inventory.models:
			if model is not None and model.object_id == model_id:
				spawner_id = server.new_object_id()
				if rotation != Quaternion.identity:
					rotation = Quaternion(rotation.y, rotation.z, rotation.w, rotation.x) # don't ask me why this is swapped
				server.db.properties[server.world_id[0]][server.world_id[2]][spawner_id] = model.lot, position, rotation
				server.spawn_model(spawner_id, model.lot, position, rotation)
				self.object.inventory.remove_item_from_inv(InventoryType.Models, model)
				server.world_control_object.script.on_model_placed(self.object)
				for obj in server.game_objects.values():
					if obj.lot == 3315:
						plaque = obj
						break
				else:
					log.error("no plaque found")
					return

				self.place_model_response(position, plaque, 14, rotation)
				self.handle_u_g_c_equip_pre_create_based_on_edit_mode(0, spawner_id)
				break

	def delete_model_from_client(self, model_id:c_int64=0, reason:c_uint=DeleteReason.PickingModelUp):
		assert reason in (DeleteReason.PickingModelUp, DeleteReason.ReturningModelToInventory)
		if reason == DeleteReason.PickingModelUp:
			server.world_control_object.script.on_model_picked_up(self.object)
		elif reason == DeleteReason.ReturningModelToInventory:
			server.world_control_object.script.on_model_put_away(self.object)

		server.replica_manager.destruct(server.game_objects[model_id])
		for spawner, model in server.models:
			if model.object_id == model_id:
				server.models.remove((spawner, model))
				prop_spawners = server.db.properties[server.world_id[0]][server.world_id[2]]
				del prop_spawners[spawner.object_id]
				item = self.object.inventory.add_item_to_inventory(model.lot)
				if reason == DeleteReason.PickingModelUp:
					self.object.inventory.equip_inventory(item_to_equip=item.object_id)
					self.handle_u_g_c_equip_post_delete_based_on_edit_mode(inv_item=item.object_id, items_total=item.amount)
				self.get_models_on_property(models={model: spawner for spawner, model in server.models})
				self.place_model_response(response=16)
				break

	def b_b_b_save_request(self, local_id:c_int64=None, lxfml_data_compressed:BitStream=None, time_taken_in_ms:c_uint=None):
		save_response = BitStream()
		save_response.write_header(WorldClientMsg.BlueprintSaveResponse)
		save_response.write(c_int64(local_id))
		save_response.write(c_uint(0))
		save_response.write(c_uint(1))
		save_response.write(c_int64(server.new_object_id()))
		save_response.write(c_uint(len(lxfml_data_compressed)))
		save_response.write(lxfml_data_compressed)
		server.send(save_response, self.address)

	@single
	def handle_u_g_c_equip_post_delete_based_on_edit_mode(self, inv_item:c_int64=None, items_total:c_int=0):
		pass

	@single
	def handle_u_g_c_equip_pre_create_based_on_edit_mode(self, model_count:c_int=None, model_id:c_int64=None):
		pass

	def property_contents_from_client(self, query_db:bool=False):
		self.get_models_on_property(models={model: spawner for spawner, model in server.models})

	@broadcast
	def get_models_on_property(self, models:(c_uint, GameObject, GameObject)=None):
		pass
