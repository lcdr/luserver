import logging
from typing import Any

from pyraknet.bitstream import c_bit, c_float, c_int64, c_ubyte, c_uint, c_ushort, ReadStream, WriteStream
from ..game_object import GameObject
from ..world import server
from ..math.vector import Vector3

log = logging.getLogger("luserver.components.skill")

class _Behavior:
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		raise NotImplementedError

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		raise NotImplementedError

class BasicAttack(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
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
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		bitstream.align_read()
		bitstream.read(c_ushort) # "padding", unused
		if target == self.object:
			return
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
		log.debug(target)
		if target is not None:
			target.destructible.deal_damage(damage, self.object)
		if hasattr(behavior, "on_success"):
			self.deserialize_behavior(behavior.on_success, bitstream, target, level+1)

class TacArc(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
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
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		if hasattr(behavior, "use_picked_target") and behavior.use_picked_target and self.picked_target_id != 0 and self.picked_target_id in server.game_objects:
			target = server.game_objects[self.picked_target_id]
			# todo: there seems to be a skill where this doesn't work and where the rest of the code should be executed as if the following lines weren't there?
			log.debug("using picked target, not completely working")
			self.deserialize_behavior(behavior.action, bitstream, target, level+1)
			return
			# end of lines
		if bitstream.read(c_bit): # is hit
			if behavior.check_env:
				if bitstream.read(c_bit): # is blocked
					log.debug("hit but blocked")
					self.deserialize_behavior(behavior.blocked_action, bitstream, target, level+1)
					return
			targets = []
			for _ in range(bitstream.read(c_uint)): # number of targets
				target_id = bitstream.read(c_int64)
				targets.append(server.game_objects.get(target_id))
			for target in targets:
				log.debug("Target %s", target)
				self.deserialize_behavior(behavior.action, bitstream, target, level+1)

		else:
			if getattr(behavior, "check_env", False):
				is_blocked = bitstream.read(c_bit)
				log.debug("blocked bit %s", is_blocked)
				if is_blocked:
					if not hasattr(behavior, "blocked_action"):
						log.error("TacArc would be blocked but has no blocked action!")
						return
					log.debug("blocked")
					self.deserialize_behavior(behavior.blocked_action, bitstream, target, level+1)
					return
			if hasattr(behavior, "miss_action"):
				log.debug("miss")
				self.deserialize_behavior(behavior.miss_action, bitstream, target, level+1)

class And(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		for behav in behavior.behaviors:
			self.serialize_behavior(behav, bitstream, target, level+1)

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		for behav in behavior.behaviors:
			self.deserialize_behavior(behav, bitstream, target, level+1)

class ProjectileAttack(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		bitstream.write(c_int64(target.object_id))

		proj_behavs = []
		for skill_id, _ in server.db.object_skills[int(behavior.projectile_lot)]:
			proj_behavs.append(server.db.skill_behavior[skill_id][0])

		projectile_count = 1
		if hasattr(behavior, "spread_count") and behavior.spread_count > 0:
			projectile_count = behavior.spread_count
		for _ in range(projectile_count):
			bitstream.write(c_int64(self.cast_projectile(proj_behavs, target)))

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		target_id = bitstream.read(c_int64)
		if target_id != 0 and target_id in server.game_objects:
			target = server.game_objects[target_id]
			log.debug("target %s", target)

		proj_behavs = []
		for skill_id, _ in server.db.object_skills[int(behavior.projectile_lot)]:
			proj_behavs.append(server.db.skill_behavior[skill_id][0])

		projectile_count = 1
		if hasattr(behavior, "spread_count") and behavior.spread_count > 0:
			projectile_count = behavior.spread_count
		for _ in range(projectile_count):
			local_id = bitstream.read(c_int64)
			self.projectile_behaviors[local_id] = proj_behavs

class Heal(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		pass

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		target.stats.life += behavior.life

class MovementType:
	Ground = 1
	Jump = 2
	Falling = 3
	DoubleJump = 4
	FallingAfterDoubleJumpAttack = 5
	Jetpack = 6
	Seven = 7  # FallingAfterHit / Knockback ?
	Nine = 9  # occurred with item 7311 - cutlass
	Rail = 10

class MovementSwitch(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		bitstream.write(c_uint(1))
		return

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		movement_type = bitstream.read(c_uint)
		log.debug("Movement type %i", movement_type)
		if movement_type in (MovementType.Ground, MovementType.Seven, MovementType.Nine, MovementType.Rail):
			action = behavior.ground_action
		elif movement_type == MovementType.Jump:
			action = behavior.jump_action
		elif movement_type in (MovementType.Falling, MovementType.FallingAfterDoubleJumpAttack):
			action = getattr(behavior, "falling_action", behavior.ground_action)
		elif movement_type == MovementType.DoubleJump:
			action = behavior.double_jump_action
		elif movement_type == MovementType.Jetpack:
			action = getattr(behavior, "jetpack_action", behavior.ground_action)
		else:
			raise NotImplementedError("Behavior", behavior.id, ": Movement type", movement_type)
		if action is not None:
			self.deserialize_behavior(action, bitstream, target, level+1)

class AreaOfEffect(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		bitstream.write(c_uint(0)) # number of targets

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		targets = []
		for _ in range(bitstream.read(c_uint)): # number of targets
			target_id = bitstream.read(c_int64)
			targets.append(server.game_objects[target_id])
		log.debug("targets: %s", targets)
		for target in targets:
			self.deserialize_behavior(behavior.action, bitstream, target, level+1)

class OverTime(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		for interval in range(behavior.num_intervals):
			self.object.call_later(interval * behavior.delay, self.deserialize_behavior, behavior.action, b"", target)

class Imagination(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		pass

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		target.stats.imagination += behavior.imagination

class TargetCaster(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		casted_behavior = behavior.action
		self.serialize_behavior(casted_behavior, bitstream, target, level+1)

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		casted_behavior = behavior.action
		self.deserialize_behavior(casted_behavior, bitstream, target, level+1)

class Stun(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		# needs to be researched more
		if False:#target.object_id != self.original_target_id:
			log.debug("Stun writing bit")
			bitstream.write(c_bit(False))

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		if False:#target and target.object_id != self.original_target_id:
			log.debug("Stun reading bit")
			assert not bitstream.read(c_bit)

class Duration(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		self.serialize_behavior(behavior.action, bitstream, target, level+1)

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		params = self.deserialize_behavior(behavior.action, bitstream, target, level+1)
		self.object.call_later(behavior.duration, self.undo_behavior, behavior.action, params)

class Knockback(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		bitstream.write(c_bit(False))

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		assert not bitstream.read(c_bit)

class AttackDelay(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		handle = self.cast_sync_skill(behavior.delay, behavior.action, target)
		log.debug("write handle %s", handle)
		bitstream.write(c_uint(handle))

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		handle = bitstream.read(c_uint)
		log.debug("read handle %s", handle)
		self.delayed_behaviors[handle] = behavior.action

ChargeUp = AttackDelay # works the same

class RepairArmor(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		pass

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		target.stats.armor += behavior.armor

class SpawnObject(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		position = self.object.physics.position + self.object.physics.rotation.rotate(Vector3.forward)*behavior.distance
		return server.spawn_object(behavior.lot, {"parent": self.object, "position": position})

SpawnQuickbuild = SpawnObject # works the same

class Switch(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		switch = True
		if getattr(behavior, "imagination", 0) > 0 or not getattr(behavior, "is_enemy_faction", False):
			log.debug("Switch writing bit")
			bitstream.write(c_bit(True))
		if switch:
			self.serialize_behavior(behavior.action_true, bitstream, target, level+1)
		else:
			self.serialize_behavior(behavior.action_false, bitstream, target, level+1)

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		switch = True
		if getattr(behavior, "imagination", 0) > 0 or not getattr(behavior, "is_enemy_faction", False):
			log.debug("Switch reading bit")
			switch = bitstream.read(c_bit)
		if switch:
			self.deserialize_behavior(behavior.action_true, bitstream, target, level+1)
		else:
			self.deserialize_behavior(behavior.action_false, bitstream, target, level+1)

class Buff(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		pass

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		if hasattr(behavior, "life"):
			self.object.stats.max_life += behavior.life
		if hasattr(behavior, "armor"):
			self.object.stats.max_armor += behavior.armor
		if hasattr(behavior, "imagination"):
			self.object.stats.max_imagination += behavior.imagination

class Jetpack(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		pass

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		kwargs = {}
		if hasattr(behavior, "bypass_checks"):
			kwargs["bypass_checks"] = bool(behavior.bypass_checks)
		if hasattr(behavior, "enable_hover"):
			kwargs["hover"] = bool(behavior.enable_hover)
		if hasattr(behavior, "airspeed"):
			kwargs["air_speed"] = behavior.airspeed
		if hasattr(behavior, "max_airspeed"):
			kwargs["max_air_speed"] = behavior.max_airspeed
		if hasattr(behavior, "vertical_velocity"):
			kwargs["vertical_velocity"] = behavior.vertical_velocity
		if hasattr(behavior, "warning_effect_id"):
			kwargs["warning_effect_id"] = behavior.warning_effect_id
		self.object.char.set_jet_pack_mode(enable=True, effect_id=167, **kwargs)

class SkillEvent(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		pass

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		if behavior.id == 14211:
			event_name = "waterspray"
		elif behavior.id == 27031:
			event_name = "spinjitzu"
		else:
			event_name = None

		target.handle("skill_event", self.object, event_name, silent=True)

class SkillCastFailed(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		pass

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		self.skill_cast_failed = True

class Chain(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		chain_index = bitstream.read(c_uint)
		log.debug("chain index %i", chain_index)
		self.deserialize_behavior(behavior.behaviors[chain_index-1], bitstream, target, level+1)

class ForceMovement(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		if getattr(behavior, "hit_action", None) is not None or \
			 getattr(behavior, "hit_action_enemy", None) is not None or \
			 getattr(behavior, "hit_action_faction", None) is not None:
			handle = bitstream.read(c_uint)
			log.debug("move handle %s", handle)
			self.delayed_behaviors[handle] = None # not known yet

class Interrupt(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		if target != self.object:
			log.debug("Interrupt: target != self, writing bit")
			bitstream.write(c_bit(False))
		if not getattr(behavior, "interrupt_block", False):
			bitstream.write(c_bit(False))
		bitstream.write(c_bit(False))

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		if target != self.object:
			log.debug("Interrupt: target != self, reading bit")
			assert not bitstream.read(c_bit)
		if not getattr(behavior, "interrupt_block", False):
			log.debug("Interrupt: not block, reading bit")
			assert not bitstream.read(c_bit)
		assert not bitstream.read(c_bit)

class SwitchMultiple(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		charge_time = bitstream.read(c_float)
		for behav, value in behavior.behaviors:
			if charge_time <= value:
				self.deserialize_behavior(behav, bitstream, target, level+1)
				break

class Start(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		self.deserialize_behavior(behavior.action, bitstream, target, level+1)

class NPCCombatSkill(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		self.serialize_behavior(behavior.behavior, bitstream, target, level+1)

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		self.deserialize_behavior(behavior.behavior, bitstream, target, level+1)

class Verify(_Behavior):
	@staticmethod
	def serialize(self, behavior: Any, bitstream: WriteStream, target: GameObject, level: int) -> None:
		bitstream.write(c_bit(False))
		bitstream.write(c_uint(0))
		bitstream.write(c_bit(False)) # blocking
		bitstream.write(c_bit(False)) # charging
		self.serialize_behavior(behavior.action, bitstream, target, level+1)

	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		assert not bitstream.read(c_bit)
		assert bitstream.read(c_uint) == 0
		assert not bitstream.read(c_bit)
		assert not bitstream.read(c_bit)
		self.deserialize_behavior(behavior.action, bitstream, target, level+1)

class AirMovement(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		handle = bitstream.read(c_uint)
		log.debug("move handle %s", handle)
		self.delayed_behaviors[handle] = None # not known yet

class ClearTarget(_Behavior):
	@staticmethod
	def deserialize(self, behavior: Any, bitstream: ReadStream, target: GameObject, level: int) -> None:
		self.deserialize_behavior(behavior.action, bitstream, target, level+1)
