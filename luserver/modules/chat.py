import argparse
import functools
import logging

from ..bitstream import BitStream, c_bool, c_int64, c_ubyte, c_uint
from ..messages import SocialMsg, WorldClientMsg, WorldServerMsg
from ..commands.minifig import EyebrowsCommand, EyesCommand, HairColorCommand, HairStyleCommand, MouthCommand, StyleCommand
from ..commands.misc import AddItemCommand, BuildCommand, CheckForLeaksCommand, CurrencyCommand, DanceCommand, DestroySpawnedCommand, DismountCommand, EverlastingCommand, ExtendInventoryCommand, FactionCommand, FactionTokensCommand, FilelogCommand, GlowCommand, GravityCommand, HelpCommand, HighStatsCommand, JetpackCommand, LevelCommand, LocationCommand, LogCommand, NoConsoleLogCommand, PlayCineCommand, PlaySoundCommand, RefillStatsCommand, RestartCommand, SendCommand, SetFlagCommand, SetRespawnCommand, SpawnCommand, SpawnPhantomCommand, TeleportCommand, UnlockEmoteCommand, VendorCommand, WhisperCommand, WorldCommand
from ..commands.mission import AddMissionCommand, AutocompleteMissionsCommand, CompleteMissionCommand, RemoveMissionCommand, ResetMissionsCommand
from .module import ServerModule

log = logging.getLogger(__file__)

class ChatCommandExit(Exception):
	pass

class CustomHelpFormatter(argparse.HelpFormatter):
	def _get_default_metavar_for_positional(self, action):
		return action.dest+" "+self._get_default_metavar_for_optional(action)

	def _get_default_metavar_for_optional(self, action):
		str_ = ""
		if action.type is not None:
			str_ += " <"+action.type.__name__ +">"
		if action.default is not None:
			str_ += " (def:"+str(action.default)+")"
		return str_[1:]

	def _metavar_formatter(self, action, default_metavar):
		if isinstance(action, argparse._SubParsersAction):
			choice_strs = [str(choice) for choice in action.choices]
			result = "%s" % ("\n"+" "*self._current_indent).join(choice_strs)

			def format(tuple_size):
				if isinstance(result, tuple):
					return result
				else:
					return (result, ) * tuple_size
			return format
		return super()._metavar_formatter(action, default_metavar)


class CustomArgumentParser(argparse.ArgumentParser):
	def __init__(self, *args, usage=argparse.SUPPRESS, formatter_class=CustomHelpFormatter, add_help=True, chat=None, **kwargs):
		self.chat = chat
		super().__init__(*args, usage=usage, formatter_class=formatter_class, add_help=False, **kwargs)
		if add_help:
			self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

	def _print_message(self, message, *args, **kwargs):
		self.chat.sys_msg_sender(message)

	def exit(self, status=0, message=None):
		"""Modified to raise exception instead of exiting."""
		self._print_message(message)
		raise ChatCommandExit

	def error(self, message):
		"""Modified to raise exception."""
		self._print_message(message)
		raise ChatCommandExit

	def _check_value(self, action, value):
		"""Modified to raise original LU error message."""
		if action.choices is not None and value not in action.choices:
			if type(action) == argparse._SubParsersAction:
				raise argparse.ArgumentError(action, "Invalid command \"%s\". Type /--help for a list of commands." % value)
			else:
				super()._check_value(action, value)

class ChatHandling(ServerModule):
	def __init__(self, server):
		super().__init__(server)
		self.chat_parser = CustomArgumentParser(chat=self, prog="server command line")
		self.commands = self.chat_parser.add_subparsers(title="Available commands", parser_class=lambda *args, **kwargs: CustomArgumentParser(*args, chat=self, **kwargs))

		cmds = AddItemCommand, AddMissionCommand, AutocompleteMissionsCommand, BuildCommand, CheckForLeaksCommand, CompleteMissionCommand, CurrencyCommand, DanceCommand, DestroySpawnedCommand, DismountCommand, EverlastingCommand, ExtendInventoryCommand, EyebrowsCommand, EyesCommand, FactionCommand, FactionTokensCommand, FilelogCommand, GlowCommand, GravityCommand, HairColorCommand, HairStyleCommand, HelpCommand, HighStatsCommand, JetpackCommand, LevelCommand, LocationCommand, LogCommand, MouthCommand, NoConsoleLogCommand, PlayCineCommand, PlaySoundCommand, RefillStatsCommand, RemoveMissionCommand, ResetMissionsCommand, RestartCommand, SendCommand, SetFlagCommand, SetRespawnCommand, SpawnCommand, SpawnPhantomCommand, StyleCommand, TeleportCommand, UnlockEmoteCommand, VendorCommand, WhisperCommand, WorldCommand

		for cmd in cmds:
			cmd(self)

	def on_validated(self, address):
		self.server.register_handler(WorldServerMsg.GeneralChatMessage, self.on_general_chat_message, address)
		self.server.register_handler(SocialMsg.PrivateChatMessage, self.on_private_chat_message, address)
		self.server.register_handler(WorldServerMsg.StringCheck, self.on_moderation_string_check, address)

	def on_moderation_string_check(self, request, address):
		request.skip_read(1) # super chat level
		request_id = request.read(c_ubyte)

		response = BitStream()
		response.write_header(WorldClientMsg.Moderation)
		response.write(c_bool(True)) # we always greenlight the content
		response.write(bytes(2))
		response.write(c_ubyte(request_id))

		self.server.send(response, address)

	def on_general_chat_message(self, message, address):
		message.skip_read(3)
		text = message.read(str, length_type=c_uint)[:-1]
		self.send_general_chat_message(self.server.accounts[address].characters.selected(), text)

	def send_general_chat_message(self, sender, text):
		chat_channel = 4
		# have to do this because the length is variable but has no length specifier directly before it
		encoded_text = text.encode("utf-16-le")
		message = BitStream()
		message.write_header(SocialMsg.GeneralChatMessage)
		message.write(bytes(8))
		message.write(c_ubyte(chat_channel))
		message.write(c_uint(len(encoded_text)))
		message.write(sender.name, allocated_length=66)
		message.write(c_int64(sender.object_id))
		message.write(bytes(3))
		message.write(encoded_text)
		message.write(bytes(2)) # null terminator

		self.server.send(message, broadcast=True)

	def system_message(self, text, address=None, broadcast=True, log_level=logging.INFO):
		if text:
			log.log(log_level, text)
			chat_channel = 4
			# have to do this because the length is variable but has no length specifier directly before it
			encoded_text = text.encode("utf-16-le")
			message = BitStream()
			message.write_header(SocialMsg.GeneralChatMessage)
			message.write(bytes(8))
			message.write(c_ubyte(chat_channel))
			message.write(c_uint(len(encoded_text)))
			message.write("", allocated_length=66)
			message.write(bytes(11))
			message.write(encoded_text)
			message.write(bytes(2)) # null terminator

			self.server.send(message, address, broadcast)

	def on_private_chat_message(self, message, address):
		log.warning("TODO: urgently needs refactoring")
		message.skip_read(90)
		recipient_name = message.read(str, allocated_length=66)

		recipient = self.server.find_player_by_name(recipient_name)
		sender = self.server.accounts[address].characters.selected()

		for address, return_code in ((recipient.char.address, 3), (address, 0)):
			relayed_message = BitStream()
			relayed_message.write_header(SocialMsg.PrivateChatMessage)
			relayed_message.write(message[:13])
			relayed_message.write(sender.name, allocated_length=66)
			relayed_message.write(c_int64(sender.object_id))
			relayed_message.write(message[87:87+70])
			relayed_message.write(c_ubyte(return_code))
			relayed_message.write(message[87+71:])

			self.server.send(relayed_message, address)

	def parse_command(self, command, sender):
		self.sys_msg_sender = functools.partial(self.system_message, address=sender.char.address, broadcast=False)
		try:
			# todo: sender privilege level check (if possible in argparse)
			args = self.chat_parser.parse_args(command.split())
			if hasattr(args, "func"):
				args.func(args, sender)
		except ChatCommandExit:
			pass
		except Exception as e:
			import traceback
			traceback.print_exc()
			self.sys_msg_sender("%s: %s" % (type(e).__name__, e))
