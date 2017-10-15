import argparse
import datetime
import functools
import importlib
import inspect
import logging
import os
import time

from ..auth import GMLevel
from ..bitstream import BitStream, c_bool, c_int64, c_ubyte, c_uint, c_ushort
from ..messages import SocialMsg, WorldClientMsg, WorldServerMsg
from ..world import server
from ..commands.command import ChatCommand, object_selector

log = logging.getLogger(__file__)

class ChatCommandExit(Exception):
	pass

class ChatPermissionError(Exception):
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
	def __init__(self, *args, usage=argparse.SUPPRESS, formatter_class=CustomHelpFormatter, add_help=False, **kwargs):
		super().__init__(*args, usage=usage, formatter_class=formatter_class, add_help=False, **kwargs)
		if add_help:
			self.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

	def _print_message(self, message, *args, **kwargs):
		server.chat.sys_msg_sender(message)

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

class ChatHandling:
	def __init__(self):
		server.chat = self
		self.chat_parser = CustomArgumentParser(prog="server command line")
		self.commands = self.chat_parser.add_subparsers(title="Available commands", parser_class=lambda *args, **kwargs: CustomArgumentParser(*args, **kwargs))

		cmds = []
		cmd_dir = os.path.normpath(os.path.join(__file__, "..", "..", "commands"))

		for filename in os.listdir(cmd_dir):
			name, ext = os.path.splitext(filename)
			if ext == ".py":
				mod = importlib.import_module("luserver.commands."+name)
				for name in dir(mod):
					var = getattr(mod, name)
					if not name.startswith("_") and inspect.isclass(var) and var is not ChatCommand and issubclass(var, ChatCommand):
						cmds.append(var)

		for cmd in cmds:
			cmd()

		clientside_cmds = "dance", "giggle", "talk", "tell", "wave", "w", "whisper"
		for cmd in clientside_cmds:
			parser = self.commands.add_parser(cmd)
			parser.add_argument("args", nargs="*")

		server.register_handler(WorldServerMsg.GeneralChatMessage, self.on_general_chat_message)
		server.register_handler(SocialMsg.PrivateChatMessage, self.on_private_chat_message)
		server.register_handler(WorldServerMsg.StringCheck, self.on_moderation_string_check)

	def on_moderation_string_check(self, request, address):
		request.skip_read(1) # super chat level
		request_id = request.read(c_ubyte)

		response = BitStream()
		response.write_header(WorldClientMsg.Moderation)
		response.write(c_bool(True)) # we always greenlight the content
		response.write(bytes(2))
		response.write(c_ubyte(request_id))

		server.send(response, address)

	def on_general_chat_message(self, message, address):
		sender = server.accounts[address].characters.selected()
		if sender.char.account.gm_level != GMLevel.Admin and sender.char.account.muted_until > time.time():
			self.system_message("Your account is muted until %s" % datetime.datetime.fromtimestamp(sender.char.account.muted_until), address, broadcast=False)
			return

		message.skip_read(3)
		text = message.read(str, length_type=c_uint)[:-1]
		self.send_general_chat_message(sender, text)

	def send_general_chat_message(self, sender, text):
		chat_channel = 4
		# have to do this because the length is variable but has no length specifier directly before it
		encoded_text = text.encode("utf-16-le")
		message = BitStream()
		message.write_header(SocialMsg.GeneralChatMessage)
		message.write(bytes(8))
		message.write(c_ubyte(chat_channel))
		message.write(c_uint(len(encoded_text)))
		message.write(sender.name, allocated_length=33)
		message.write(c_int64(sender.object_id))
		message.write(bytes(2))
		if hasattr(sender, "char"):
			message.write(c_bool(sender.char.show_gm_status))
		else:
			message.write(c_bool(False))
		message.write(encoded_text)
		message.write(bytes(2)) # null terminator

		server.send(message, broadcast=True)

	def system_message(self, text, address=None, broadcast=True, log_level=logging.INFO):
		if text:
			text = str(text)
			log.log(log_level, text)
			chat_channel = 4
			# have to do this because the length is variable but has no length specifier directly before it
			encoded_text = text.encode("utf-16-le")
			message = BitStream()
			message.write_header(SocialMsg.GeneralChatMessage)
			message.write(bytes(8))
			message.write(c_ubyte(chat_channel))
			message.write(c_uint(len(encoded_text)))
			message.write("", allocated_length=33)
			message.write(bytes(11))
			message.write(encoded_text)
			message.write(bytes(2)) # null terminator

			server.send(message, address, broadcast)

	def send_private_chat_message(self, sender, text, recipient):
		participants = []
		if hasattr(sender, "char"):
			participants.append((sender.char.address, 0))
		if hasattr(recipient, "char"):
			participants.append((recipient.char.address, 3))

		for address, return_code in participants:
			message = BitStream()
			message.write_header(SocialMsg.PrivateChatMessage)
			message.write(c_int64(0))
			message.write(c_ubyte(7))
			message.write(c_uint(len(text)))
			if isinstance(sender, str):
				message.write(sender, allocated_length=33)
				message.write(c_int64(0))
			else:
				message.write(sender.name, allocated_length=33)
				message.write(c_int64(sender.object_id))
			message.write(c_ushort(0))
			if hasattr(sender, "char"):
				message.write(c_bool(sender.char.show_gm_status))
			else:
				message.write(c_bool(False))
			message.write(recipient.name, allocated_length=33)
			if hasattr(recipient, "char"):
				message.write(c_bool(recipient.char.show_gm_status))
			else:
				message.write(c_bool(False))
			message.write(c_ubyte(return_code))
			message.write(text, allocated_length=(len(text)+1))

			server.send(message, address)

	def on_private_chat_message(self, message, address):
		assert message.read(c_int64) == 0 # unknown
		assert message.read(c_ubyte) == 7 # chat channel
		text_length = message.read(c_uint)
		message.skip_read(66) # seems unused?
		sender_id = message.read(c_int64)
		assert sender_id == 0
		assert message.read(c_ushort) == 0
		message.read(c_bool) # is sender mythran
		recipient_name = message.read(str, allocated_length=33)
		message.read(c_bool) # is recipient mythran
		return_code = message.read(c_ubyte)
		print("return code", return_code)
		text = message.read(str, allocated_length=text_length)
		assert message.all_read()

		sender = server.accounts[address].characters.selected()

		if recipient_name.startswith("!"):
			recipients = object_selector(recipient_name)
			for recipient in recipients:
				recipient.handle("on_private_chat_message", sender, text)
		else:
			recipient = server.find_player_by_name(recipient_name)
			self.send_private_chat_message(sender, text, recipient)

	def parse_command(self, command, sender):
		self.sys_msg_sender = functools.partial(self.system_message, address=sender.char.address, broadcast=False)
		try:
			# todo: sender privilege level check (if possible in argparse)
			args = self.chat_parser.parse_args(command.split())

			if sender.char.account.gm_level != GMLevel.Admin:
				raise ChatPermissionError("Must be admin to do this")

			if hasattr(args, "func"):
				args.func(args, sender)
		except ChatCommandExit:
			pass
		except Exception as e:
			import traceback
			traceback.print_exc()
			self.sys_msg_sender("%s: %s" % (type(e).__name__, e))
