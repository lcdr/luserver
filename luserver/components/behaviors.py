import asyncio
import logging

from ..bitstream import c_bit, c_float, c_int64, c_ubyte, c_uint, c_ushort

log = logging.getLogger(__name__)

class Behavior:
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		raise NotImplementedError

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		raise NotImplementedError

class BasicAttack(Behavior):
	def serialize(self, behavior, bitstream, target, level):
		bitstream.align_write()
		bitstream.write(c_ushort(0))
		bitstream.write(c_bit(False))
		bitstream.write(c_bit(False))
		bitstream.write(c_bit(True))
		bitstream.write(c_uint(0))
		damage = 1
		bitstream.write(c_uint(damage))
		aoe = False
		bitstream.write(c_bit(aoe))
		enemy_type = 1
		bitstream.write(c_ubyte(enemy_type))
		if hasattr(behavior, "on_success"):
			self.serialize_behavior(behavior.on_success, bitstream, target, level+1)

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
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
		print(target)
		target.destructible.deal_damage(damage, self.object)
		if hasattr(behavior, "on_success"):
			self.unserialize_behavior(behavior.on_success, bitstream, target, level+1)

class TacArc(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		is_hit = True
		bitstream.write(c_bit(is_hit))
		if behavior.check_env:
			is_blocked = False
			bitstream.write(c_bit(is_blocked))
		targets = [target]
		bitstream.write(c_uint(len(targets)))
		for target in targets:
			bitstream.write(c_int64(target.object_id))
		for target in targets:
			log.debug("Target %s", target)
			self.serialize_behavior(behavior.action, bitstream, target, level+1)

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		if behavior.use_picked_target and self.picked_target_id != 0 and self.picked_target_id in self.object._v_server.game_objects:
			target = self.object._v_server.game_objects[self.picked_target_id]
			# todo: there seems to be a skill where this doesn't work and where the rest of the code should be executed as if the following lines weren't there?
			log.debug("using picked target, not completely working")
			self.unserialize_behavior(behavior.action, bitstream, target, level+1)
			return
			# end of lines
		if bitstream.read(c_bit): # is hit
			if behavior.check_env:
				if bitstream.read(c_bit): # is blocked
					log.debug("hit but blocked")
					self.unserialize_behavior(behavior.blocked_action, bitstream, target, level+1)
					return
			targets = []
			for _ in range(bitstream.read(c_uint)): # number of targets
				target_id = bitstream.read(c_int64)
				targets.append(self.object._v_server.game_objects.get(target_id))
			for target in targets:
				log.debug("Target %s", target)
				self.unserialize_behavior(behavior.action, bitstream, target, level+1)

		else:
			if hasattr(behavior, "blocked_action"):
				if bitstream.read(c_bit): # is blocked
					log.debug("blocked")
					self.unserialize_behavior(behavior.blocked_action, bitstream, target, level+1)
					return
			if hasattr(behavior, "miss_action"):
				log.debug("miss")
				self.unserialize_behavior(behavior.miss_action, bitstream, target, level+1)

class And(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		for behav in behavior.behaviors:
			self.serialize_behavior(behav, bitstream, target, level+1)

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		for behav in behavior.behaviors:
			self.unserialize_behavior(behav, bitstream, target, level+1)

class ProjectileAttack(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		bitstream.write(c_int64(target.object_id))

		proj_behavs = []
		for skill_id in self.object._v_server.db.object_skills[int(behavior.projectile_lot)]:
			proj_behavs.append(self.object._v_server.db.skill_behavior[skill_id])

		projectile_count = 1
		if hasattr(behavior, "spread_count") and behavior.spread_count > 0:
			projectile_count = behavior.spread_count
		for _ in range(projectile_count):
			bitstream.write(c_int64(self.cast_projectile(proj_behavs, target)))

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		target_id = bitstream.read(c_int64)
		if target_id != 0 and target_id in self.object._v_server.game_objects:
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

class Heal(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		pass

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		target.stats.life += behavior.life

class MovementType:
	Ground = 1
	Jump = 2
	Falling = 3
	DoubleJump = 4
	FallingAfterDoubleJumpAttack = 5
	Jetpack = 6
	Rail = 10

class MovementSwitch(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
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
			self.unserialize_behavior(action, bitstream, target, level+1)

class AreaOfEffect(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		targets = []
		for _ in range(bitstream.read(c_uint)): # number of targets
			target_id = bitstream.read(c_int64)
			targets.append(self.object._v_server.game_objects[target_id])
		for target in targets:
			self.unserialize_behavior(behavior.action, bitstream, target, level+1)

class OverTime(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		for interval in range(behavior.num_intervals):
			asyncio.get_event_loop().call_later(interval * behavior.delay, self.unserialize_behavior, behavior.action, b"", target)

class Imagination(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		target.stats.imagination += behavior.imagination

class TargetCaster(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		casted_behavior = behavior.action
		self.unserialize_behavior(casted_behavior, bitstream, target, level+1)

class Stun(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		if target.object_id != self.original_target_id:
			log.debug("Stun writing bit")
			bitstream.write(c_bit(False))

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		if target and target.object_id != self.original_target_id:
			log.debug("Stun reading bit")
			assert not bitstream.read(c_bit)

class Duration(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		self.serialize_behavior(behavior.action, bitstream, target, level+1)

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		params = self.unserialize_behavior(behavior.action, bitstream, target, level+1)
		asyncio.get_event_loop().call_later(behavior.duration, self.undo_behavior, behavior.action, params)

class Knockback(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		bitstream.write(c_bit(False))

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		assert not bitstream.read(c_bit)

class AttackDelay(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		bitstream.write(c_uint(self.cast_sync_skill(behavior.delay, behavior.action, target)))

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		handle = bitstream.read(c_uint)
		log.debug("handle %s", handle)
		self.delayed_behaviors[handle] = behavior.action

ChargeUp = AttackDelay # works the same

class RepairArmor(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		target.stats.armor += behavior.armor

class SpawnObject(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		return self.object._v_server.spawn_object(behavior.lot, parent=self.object)

SpawnQuickbuild = SpawnObject # works the same

class Switch(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		switch = True
		if getattr(behavior, "imagination", 0) > 0 or not getattr(behavior, "is_enemy_faction", False):
			log.debug("Switch writing bit")
			bitstream.write(c_bit(True))
		if switch:
			self.serialize_behavior(behavior.action_true, bitstream, target, level+1)
		else:
			self.serialize_behavior(behavior.action_false, bitstream, target, level+1)

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		switch = True
		if getattr(behavior, "imagination", 0) > 0 or not getattr(behavior, "is_enemy_faction", False):
			log.debug("Switch reading bit")
			switch = bitstream.read(c_bit)
		if switch:
			self.unserialize_behavior(behavior.action_true, bitstream, target, level+1)
		else:
			self.unserialize_behavior(behavior.action_false, bitstream, target, level+1)

class Buff(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		if hasattr(behavior, "life"):
			self.object.stats.max_life += behavior.life
		if hasattr(behavior, "armor"):
			self.object.stats.max_armor += behavior.armor
		if hasattr(behavior, "imagination"):
			self.object.stats.max_imagination += behavior.imagination

class Chain(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		chain_index = bitstream.read(c_uint)
		self.unserialize_behavior(behavior.behaviors[chain_index-1], bitstream, target, level+1)

class ForceMovement(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		if getattr(behavior, "hit_action", None) is not None or \
			 getattr(behavior, "hit_action_enemy", None) is not None or \
			 getattr(behavior, "hit_action_faction", None) is not None:
			handle = bitstream.read(c_uint)
			log.debug("move handle %s", handle)
			self.delayed_behaviors[handle] = None # not known yet

class Interrupt(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		if target != self.object:
			log.debug("Interrupt: target != self, reading bit")
			assert not bitstream.read(c_bit)
		if not getattr(behavior, "interrupt_block", False):
			log.debug("Interrupt: not block, reading bit")
			assert not bitstream.read(c_bit)
		assert not bitstream.read(c_bit)

class SwitchMultiple(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		charge_time = bitstream.read(c_float)
		for behav, value in behavior.behaviors:
			if charge_time <= value:
				self.unserialize_behavior(behav, bitstream, target, level+1)
				break

class Start(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		self.unserialize_behavior(behavior.action, bitstream, target, level+1)

class NPCCombatSkill(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		self.serialize_behavior(behavior.behavior, bitstream, target, level+1)

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		self.unserialize_behavior(behavior.behavior, bitstream, target, level+1)

class Verify(Behavior):
	@staticmethod
	def serialize(self, behavior, bitstream, target, level):
		bitstream.write(c_bit(False))
		self.serialize_behavior(behavior.action, bitstream, target, level+1)

	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		assert not bitstream.read(c_bit)
		self.unserialize_behavior(behavior.action, bitstream, target, level+1)

class AirMovement(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		handle = bitstream.read(c_uint)
		log.debug("move handle %s", handle)
		self.delayed_behaviors[handle] = None # not known yet

class ClearTarget(Behavior):
	@staticmethod
	def unserialize(self, behavior, bitstream, target, level):
		self.unserialize_behavior(behavior.action, bitstream, target, level+1)
