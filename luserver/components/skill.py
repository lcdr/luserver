import asyncio
import logging
import pprint
import enum

from ..bitstream import BitStream, c_bit, c_float, c_int, c_int64, c_ubyte, c_uint, c_uint64, c_ushort
from ..math.quaternion import Quaternion
from ..math.vector import Vector3
from .component import Component
from .inventory import InventoryType, ItemType
from .mission import MissionState, TaskType

log = logging.getLogger(__name__)

class BehaviorTemplate(enum.IntEnum):
	BasicAttack = 1
	TacArc = 2
	And = 3
	ProjectileAttack = 4
	Heal = 5
	MovementSwitch = 6
	AreaOfEffect = 7
	PlayEffect = 8
	Immunity = 9
	DamageBuff = 10
	DamageAbsorption = 11
	OverTime = 12
	Imagination = 13
	TargetCaster = 14
	Stun = 15
	Duration = 16
	Knockback = 17
	AttackDelay = 18
	CarBoost = 19
	FallSpeed = 20
	Shield = 21
	RepairArmor = 22
	Speed = 23
	DarkInspiration = 24
	LootBuff = 25
	VentureVision = 26
	SpawnObject = 27
	LayBrick = 28
	Switch = 29
	Buff = 30
	Jetpack = 31
	SkillEvent = 32
	ConsumeItem = 33
	SkillCastFailed = 34
	ImitationSkunkStink = 35
	ChangeIdleFlags = 36
	ApplyBuff = 37
	Chain = 38
	ChangeOrientation = 39
	ForceMovement = 40
	Interrupt = 41
	AlterCooldown = 42
	ChargeUp = 43
	SwitchMultiple = 44
	Start = 45
	End = 46
	AlterChainDelay = 47
	Camera = 48
	RemoveBuff = 49
	Grab = 50
	ModularBuild = 51
	NPCCombatSkill = 52
	Block = 53
	Verify = 54
	Taunt = 55
	AirMovement = 56
	SpawnQuickbuild = 57
	PullToPoint = 58
	PropertyRotate = 59
	DamageReduction = 60
	PropertyTeleport = 61
	ClearTarget = 62
	TakePicture = 63
	Mount = 64
	SkillSet = 65

class MovementType:
	Ground = 1
	Jump = 2
	Falling = 3
	DoubleJump = 4
	FallingAfterDoubleJumpAttack = 5
	Jetpack = 6
	Rail = 10

class SkillSlot:
	RightHand = 0
	LeftHand = 1
	Neck = 2
	Hat = 3

class CastType:
	Consumable = 3
	EverlastingConsumable = 4

class SkillComponent(Component):
	def __init__(self, obj, set_vars, comp_id):
		super().__init__(obj, set_vars, comp_id)
		self.object.skill = self
		self.delayed_behaviors = {}
		self.projectile_behaviors = {}
		self.last_ui_skill_handle = 0
		self.everlasting = False

	def serialize(self, out, is_creation):
		if is_creation:
			out.write(c_bit(False))

	def on_destruction(self):
		self.delayed_behaviors.clear()
		self.projectile_behaviors.clear()

	def cast_skill(self, skill_id, target=None):
		if target is None:
			target = self.object
		self.start_skill(None, skill_id=skill_id, optional_target_id=target.object_id, ui_skill_handle=self.last_ui_skill_handle, optional_originator_id=0, originator_rot=Quaternion(0, 0, 0, 0), bitstream=BitStream())
		self.last_ui_skill_handle += 1

	def echo_start_skill(self, address, used_mouse:c_bit=False, caster_latency:c_float=0, cast_type:c_int=0, last_clicked_posit:Vector3=(0, 0, 0), optional_originator_id:c_int64=None, optional_target_id:c_int64=0, originator_rot:Quaternion=Quaternion.identity, bitstream:BitStream=None, skill_id:c_uint=None, ui_skill_handle:c_uint=0):
		pass

	def start_skill(self, address, used_mouse:c_bit=False, consumable_item_id:c_int64=0, caster_latency:c_float=0, cast_type:c_int=0, last_clicked_posit:Vector3=Vector3.zero, optional_originator_id:c_int64=None, optional_target_id:c_int64=0, originator_rot:Quaternion=Quaternion.identity, bitstream:BitStream=None, skill_id:c_uint=None, ui_skill_handle:c_uint=0):
		assert not used_mouse
		assert caster_latency == 0
		assert last_clicked_posit == Vector3.zero
		assert optional_originator_id in (0, self.object.object_id)
		assert originator_rot == Quaternion(0, 0, 0, 0)

		self.object._v_server.send_game_message(self.echo_start_skill, used_mouse, caster_latency, cast_type, last_clicked_posit, optional_originator_id, optional_target_id, originator_rot, bitstream, skill_id, ui_skill_handle, address=address, broadcast=True)

		if hasattr(self.object, "char"):
			# update missions that have using this skill as requirement
			for mission in self.object.char.missions:
				if mission.state == MissionState.Active:
					for task in mission.tasks:
						if task.type == TaskType.UseSkill and skill_id in task.parameter:
							mission.increment_task(task, self.object)

		target = self.object
		self.picked_target_id = optional_target_id
		behavior = self.object._v_server.db.skill_behavior[skill_id]
		self.original_target_id = target.object_id
		self.handle_behavior(behavior, bitstream, target)

		if not bitstream.all_read():
			log.warning("not all read, remaining: %s", bitstream[bitstream._read_offset//8:])

		# remove consumable
		if not self.everlasting and consumable_item_id != 0 and cast_type == CastType.Consumable:
			for item in self.object.inventory.items:
				if item is not None and item.object_id == consumable_item_id:
					self.object.inventory.remove_item_from_inv(InventoryType.Items, item)
					break

	def select_skill(self, address, from_skill_set:c_bit=False, skill_id:c_int=None):
		pass

	def add_skill(self, address, ai_combat_weight:c_int=0, from_skill_set:c_bit=False, cast_type:c_int=0, time_secs:c_float=-1, times_can_cast:c_int=-1, skill_id:c_uint=None, slot_id:c_int=-1, temporary:c_bit=True):
		pass

	def remove_skill(self, address, from_skill_set:c_bit=False, skill_id:c_uint=None):
		pass

	def echo_sync_skill(self, address, done:c_bit=False, bitstream:BitStream=None, ui_behavior_handle:c_uint=None, ui_skill_handle:c_uint=None):
		pass

	def sync_skill(self, address, done:c_bit=False, bitstream:BitStream=None, ui_behavior_handle:c_uint=None, ui_skill_handle:c_uint=None):
		self.object._v_server.send_game_message(self.echo_sync_skill, done, bitstream, ui_behavior_handle, ui_skill_handle, address=address, broadcast=True)
		if ui_behavior_handle not in self.delayed_behaviors:
			log.error("Handle %i not handled!", ui_behavior_handle)
			return
		behavior = self.delayed_behaviors[ui_behavior_handle]
		target = self.object
		if behavior is None:
			behavior_id = bitstream.read(c_uint)
			target_id = bitstream.read(c_uint64)
			if behavior_id != 0:
				behavior = self.object._v_server.db.behavior[behavior_id]
			if target_id != 0:
				target = self.object._v_server.game_objects[target_id]

		if behavior is not None: # no, this is not an "else" from above
			self.original_target_id = target.object_id
			self.handle_behavior(behavior, bitstream, target)
		if not bitstream.all_read():
			log.warning("not all read, remaining: %s", bitstream[bitstream._read_offset//8:])
		if done:
			del self.delayed_behaviors[ui_behavior_handle]

	def request_server_projectile_impact(self, address, local_id:c_int64=0, target_id:c_int64=0, bitstream:BitStream=None):
		if target_id == 0:
			target = self.object
		else:
			if target_id not in self.object._v_server.game_objects:
				log.debug("Projectile Target %i not in game objects", target_id)
				return
			target = self.object._v_server.game_objects[target_id]

		for behav in self.projectile_behaviors[local_id]:
			self.original_target_id = target.object_id
			self.handle_behavior(behav, bitstream, target)
		del self.projectile_behaviors[local_id]
		# todo: do client projectile impact

	def handle_behavior(self, behavior, bitstream, target, level=0):
		if behavior is None:
			return
		log.debug("  "*level+BehaviorTemplate(behavior.template).name+" %i", behavior.id)
		if behavior.template not in (BehaviorTemplate.BasicAttack, BehaviorTemplate.TacArc, BehaviorTemplate.And, BehaviorTemplate.Heal, BehaviorTemplate.MovementSwitch, BehaviorTemplate.AreaOfEffect, BehaviorTemplate.PlayEffect, BehaviorTemplate.Imagination, BehaviorTemplate.TargetCaster, BehaviorTemplate.Stun, BehaviorTemplate.Duration, BehaviorTemplate.Knockback, BehaviorTemplate.AttackDelay, BehaviorTemplate.RepairArmor, BehaviorTemplate.Switch, BehaviorTemplate.Chain, BehaviorTemplate.ChangeOrientation, BehaviorTemplate.ForceMovement, BehaviorTemplate.AlterCooldown, BehaviorTemplate.ChargeUp, BehaviorTemplate.SwitchMultiple, BehaviorTemplate.Start, BehaviorTemplate.AlterChainDelay, BehaviorTemplate.AirMovement):
			log.debug(pprint.pformat(vars(behavior), indent=level))

		if behavior.template == BehaviorTemplate.BasicAttack:
			bitstream.align_read()
			bitstream.read(c_ushort) # "padding", unused
			assert not bitstream.read(c_bit)
			assert not bitstream.read(c_bit)
			assert bitstream.read(c_bit)
			log.debug(bitstream.read(c_uint))
			damage = bitstream.read(c_uint)
			log.debug(damage)
			log.debug("AoE? %s", bitstream.read(c_bit))
			enemy_type = bitstream.read(c_ubyte) # ?
			if enemy_type != 1:
				log.debug(enemy_type)
			target.destructible.deal_damage(damage, self.object)
			if hasattr(behavior, "on_success"):
				self.handle_behavior(behavior.on_success, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.TacArc:
			if behavior.use_picked_target and self.picked_target_id != 0 and self.picked_target_id in self.object._v_server.game_objects:
				target = self.object._v_server.game_objects[self.picked_target_id]
				# todo: there seems to be a skill where this doesn't work and where the rest of the code should be executed as if the following lines weren't there?
				log.debug("using picked target, not completely working")
				self.handle_behavior(behavior.action, bitstream, target, level+1)
				return
				# end of lines
			if bitstream.read(c_bit): # is hit
				if behavior.check_env:
					if bitstream.read(c_bit): # is blocked
						log.debug("hit but blocked")
						self.handle_behavior(behavior.blocked_action, bitstream, target, level+1)
						return
				targets = []
				for _ in range(bitstream.read(c_uint)): # number of targets
					target_id = bitstream.read(c_int64)
					targets.append(self.object._v_server.game_objects[target_id])
				for target in targets:
					log.debug("Target %s", target)
					self.handle_behavior(behavior.action, bitstream, target, level+1)

			else:
				if hasattr(behavior, "blocked_action"):
					if bitstream.read(c_bit): # is blocked
						log.debug("blocked")
						self.handle_behavior(behavior.blocked_action, bitstream, target, level+1)
						return
				if hasattr(behavior, "miss_action"):
					log.debug("miss")
					self.handle_behavior(behavior.miss_action, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.And:
			for behav in behavior.behaviors:
				self.handle_behavior(behav, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.ProjectileAttack:
			target_id = bitstream.read(c_int64)
			if target_id != 0:
				target = self.object._v_server.game_objects[target_id]
				log.debug("target %s", target)

			proj_behavs = []
			for skill_id in self.object._v_server.db.object_skills[int(behavior.projectile_lot)]:
				proj_behavs.append(self.object._v_server.db.skill_behavior[skill_id])

			projectile_count = 1
			if hasattr(behavior, "spread_count") and behavior.spread_count > 0:
				projectile_count = behavior.spread_count
			for _ in range(projectile_count):
				local_id = bitstream.read(c_int64)
				self.projectile_behaviors[local_id] = proj_behavs

		elif behavior.template == BehaviorTemplate.Heal:
			target.stats.life += behavior.life

		elif behavior.template == BehaviorTemplate.MovementSwitch:
			movement_type = bitstream.read(c_uint)
			if movement_type in (MovementType.Ground, MovementType.Rail):
				action = behavior.ground_action
			elif movement_type == MovementType.Jump:
				action = behavior.jump_action
			elif movement_type == MovementType.Falling:
				action = behavior.falling_action
			elif movement_type == MovementType.DoubleJump:
				action = behavior.double_jump_action
			elif movement_type == MovementType.Jetpack:
				action = behavior.jetpack_action
			else:
				raise NotImplementedError("Movement type", movement_type)
			if action is not None:
				self.handle_behavior(action, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.AreaOfEffect:
			targets = []
			for _ in range(bitstream.read(c_uint)): # number of targets
				target_id = bitstream.read(c_int64)
				targets.append(self.object._v_server.game_objects[target_id])
			for target in targets:
				self.handle_behavior(behavior.action, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.OverTime:
			for interval in range(behavior.num_intervals):
				asyncio.get_event_loop().call_later(interval * behavior.delay, self.handle_behavior, behavior.action, b"", target)

		elif behavior.template == BehaviorTemplate.Imagination:
			target.stats.imagination += behavior.imagination

		elif behavior.template == BehaviorTemplate.TargetCaster:
			casted_behavior = behavior.action
			self.handle_behavior(casted_behavior, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.Stun:
			if target.object_id != self.original_target_id:
				log.debug("Stun reading bit")
				assert not bitstream.read(c_bit)

		elif behavior.template == BehaviorTemplate.Duration:
			params = self.handle_behavior(behavior.action, bitstream, target, level+1)
			asyncio.get_event_loop().call_later(behavior.duration, self.undo_behavior, behavior.action, params)

		elif behavior.template == BehaviorTemplate.Knockback:
			assert not bitstream.read(c_bit)

		elif behavior.template in (BehaviorTemplate.AttackDelay, BehaviorTemplate.ChargeUp):
			handle = bitstream.read(c_uint)
			log.debug("handle %s", handle)
			self.delayed_behaviors[handle] = behavior.action

		elif behavior.template == BehaviorTemplate.RepairArmor:
			target.stats.armor += behavior.armor

		elif behavior.template in (BehaviorTemplate.SpawnObject, BehaviorTemplate.SpawnQuickbuild):
			return self.object._v_server.spawn_object(behavior.lot, parent=self.object)

		elif behavior.template == BehaviorTemplate.Switch:
			switch = True
			if getattr(behavior, "imagination", 0) > 0 or not getattr(behavior, "is_enemy_faction", False):
				log.debug("Switch reading bit")
				switch = bitstream.read(c_bit)
			if switch:
				self.handle_behavior(behavior.action_true, bitstream, target, level+1)
			else:
				self.handle_behavior(behavior.action_false, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.Buff:
			if hasattr(behavior, "life"):
				self.object.stats.max_life += behavior.life
			if hasattr(behavior, "armor"):
				self.object.stats.max_armor += behavior.armor
			if hasattr(behavior, "imagination"):
				self.object.stats.max_imagination += behavior.imagination

		elif behavior.template == BehaviorTemplate.Chain:
			chain_index = bitstream.read(c_uint)
			self.handle_behavior(behavior.behaviors[chain_index-1], bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.ForceMovement:
			if getattr(behavior, "hit_action", None) is not None or \
			   getattr(behavior, "hit_action_enemy", None) is not None or \
				 getattr(behavior, "hit_action_faction", None) is not None:
				handle = bitstream.read(c_uint)
				log.debug("move handle %s", handle)
				self.delayed_behaviors[handle] = None # not known yet

		elif behavior.template == BehaviorTemplate.Interrupt:
			if target != self.object:
				log.debug("Interrupt: target != self, reading bit")
				assert not bitstream.read(c_bit)
			if not getattr(behavior, "interrupt_block", False):
				log.debug("Interrupt: not block, reading bit")
				assert not bitstream.read(c_bit)
			assert not bitstream.read(c_bit)

		elif behavior.template == BehaviorTemplate.SwitchMultiple:
			charge_time = bitstream.read(c_float)
			for behav, value in behavior.behaviors:
				if charge_time <= value:
					self.handle_behavior(behav, bitstream, target, level+1)
					break

		elif behavior.template == BehaviorTemplate.Start:
			self.handle_behavior(behavior.action, bitstream, target, level+1)

		elif behavior.template == BehaviorTemplate.AirMovement:
			handle = bitstream.read(c_uint)
			log.debug("move handle %s", handle)
			self.delayed_behaviors[handle] = None # not known yet

		elif behavior.template == BehaviorTemplate.ClearTarget:
			self.handle_behavior(behavior.action, bitstream, target, level+1)

	def undo_behavior(self, behavior, params=None):
		if behavior.template == BehaviorTemplate.SpawnObject:
			self.object._v_server.destruct(params)
		elif behavior.template == BehaviorTemplate.Buff:
			if hasattr(behavior, "life"):
				self.object.stats.max_life -= behavior.life
			if hasattr(behavior, "armor"):
				self.object.stats.max_armor -= behavior.armor
			if hasattr(behavior, "imagination"):
				self.object.stats.max_imagination -= behavior.imagination

	def add_skill_for_item(self, item, add_buffs=True):
		if item.lot in self.object._v_server.db.object_skills:
			for skill_id in self.object._v_server.db.object_skills[item.lot]:
				behavior = self.object._v_server.db.skill_behavior[skill_id]
				if behavior.template in (BehaviorTemplate.TargetCaster, BehaviorTemplate.Buff, BehaviorTemplate.ApplyBuff):
					if add_buffs:
						if hasattr(self.object, "char"):
							# update missions that have using this skill as requirement
							for mission in self.object.char.missions:
								if mission.state == MissionState.Active:
									for task in mission.tasks:
										if task.type == TaskType.UseSkill and skill_id in task.parameter:
											mission.increment_task(task, self.object)
						self.handle_behavior(behavior, b"", self.object)
				else:
					slot_id = SkillSlot.RightHand
					if item.item_type == ItemType.Hat:
						slot_id = SkillSlot.Hat
					elif item.item_type == ItemType.LeftHand:
						slot_id = SkillSlot.LeftHand
					elif item.item_type == ItemType.Neck:
						slot_id = SkillSlot.Neck
					self.object._v_server.send_game_message(self.add_skill, skill_id=skill_id, slot_id=slot_id, address=self.object.char.address)

	def add_skill_server(self, skill_id):
		behavior = self.object._v_server.db.skill_behavior[skill_id]
		if behavior.template in (BehaviorTemplate.TargetCaster, BehaviorTemplate.Buff, BehaviorTemplate.ApplyBuff):
			if hasattr(self.object, "char"):
				# update missions that have using this skill as requirement
				for mission in self.object.char.missions:
					if mission.state == MissionState.Active:
						for task in mission.tasks:
							if task.type == TaskType.UseSkill and skill_id in task.parameter:
								mission.increment_task(task, self.object)
			self.handle_behavior(behavior, b"", self.object)

	def remove_skill_for_item(self, item):
		if item.lot in self.object._v_server.db.object_skills:
			for skill_id in self.object._v_server.db.object_skills[item.lot]:
				behavior = self.object._v_server.db.skill_behavior[skill_id]
				if behavior.template in (BehaviorTemplate.TargetCaster, BehaviorTemplate.Buff, BehaviorTemplate.ApplyBuff):
					self.undo_behavior(behavior)
				else:
					self.object._v_server.send_game_message(self.remove_skill, skill_id=skill_id, address=self.object.char.address)

	def remove_skill_server(self, skill_id):
		behavior = self.object._v_server.db.skill_behavior[skill_id]
		if behavior.template in (BehaviorTemplate.TargetCaster, BehaviorTemplate.Buff, BehaviorTemplate.ApplyBuff):
			self.undo_behavior(behavior)
