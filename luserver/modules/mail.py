from enum import IntEnum

class MailID(IntEnum):
	MailSend = 0
	MailSendResponse = 1
	MailNotification = 2
	MailDataRequest = 3
	MailData = 4
	MailAttachmentCollect = 5
	MailAttachmentCollectResponse = 6
	MailDelete = 7
	MailDeleteResponse = 8
	MailRead = 9
	MailReadResponse = 10
	MailNotificationRequest = 11

import time

import persistent

from pyraknet.bitstream import c_bool, c_int, c_int64, c_uint, c_uint64, c_ushort, ReadStream
from pyraknet.messages import Address
from ..bitstream import WriteStream
from ..game_object import Player
from ..messages import WorldClientMsg, WorldServerMsg
from ..world import server
from ..components.inventory import InventoryType, LootType, Stack
from ..math.vector import Vector3

_MAIL_SEND_COST = 25

class _MailSendReturnCode:
	Success = 0
	ItemCannotBeMailed = 3
	CannotMailYourself = 4
	RecipientNotFound = 5
	UnknownFailure = 7

class MailHandling:
	def __init__(self) -> None:
		server.register_handler(WorldServerMsg.Mail, self._on_mail)

	def _on_mail(self, message: ReadStream, address: Address) -> None:
		mail_id = message.read(c_uint)
		player = server.accounts[address].selected_char()
		if mail_id == MailID.MailSend:
			self._on_mail_send(message, player)
		elif mail_id == MailID.MailDataRequest:
			self._send_mail_data(player)
		elif mail_id == MailID.MailAttachmentCollect:
			self._on_mail_attachment_collect(message, player)
		elif mail_id == MailID.MailDelete:
			self._on_mail_delete(message, player)
		elif mail_id == MailID.MailRead:
			self._on_mail_read(message, player)
		elif mail_id == MailID.MailNotificationRequest:
			self._send_mail_notification(player)

	def _on_mail_send(self, data: ReadStream, player: Player) -> None:
		subject = data.read(str, allocated_length=50)
		body = data.read(str, allocated_length=400)
		recipient_name = data.read(str, allocated_length=32)
		assert data.read(c_uint64) == 0
		attachment_item_object_id = data.read(c_int64)
		attachment_item_count = data.read(c_ushort)

		return_code = _MailSendReturnCode.Success
		try:
			if attachment_item_count != 0:
				removed_item = player.inventory.remove_item(InventoryType.Max, object_id=attachment_item_object_id, count=attachment_item_count)
				object_id = server.new_object_id()
				attachment = Stack(server.db, object_id, removed_item.lot)
				attachment_cost = (removed_item.base_value * attachment_item_count)//10
			else:
				attachment = None
				attachment_cost = 0
			if recipient_name == player.name:
				return_code = _MailSendReturnCode.CannotMailYourself
				return
			try:
				recipient = server.find_player_by_name(recipient_name)
			except KeyError:
				return_code = _MailSendReturnCode.RecipientNotFound
				return
			self.send_mail(player.name, subject, body, recipient, attachment)
			player.char.set_currency(currency=player.char.currency - _MAIL_SEND_COST - attachment_cost, loot_type=LootType.Mail, position=Vector3.zero)
		except Exception:
			import traceback
			traceback.print_exc()
			return_code = _MailSendReturnCode.UnknownFailure
		finally:
			out = WriteStream()
			out.write_header(WorldClientMsg.Mail)
			out.write(c_uint(MailID.MailSendResponse))
			out.write(c_uint(return_code))
			server.send(out, player.char.address)

	def send_mail(self, sender_name: str, subject: str, body: str, recipient: Player, attachment: Stack=None) -> None:
		mail = Mail(server.new_object_id(), sender_name, subject, body, attachment)
		with server.multi:
			recipient.char.mails.append(mail)
		if recipient.char.address in server._server._connected:
			self._send_mail_notification(recipient)

	def _send_mail_data(self, player: Player) -> None:
		mails = WriteStream()
		mails.write_header(WorldClientMsg.Mail)
		mails.write(c_uint(MailID.MailData))
		mails.write(bytes(4)) # return code success (enum is a bit overkill here)
		mails.write(c_ushort(len(player.char.mails)))
		mails.write(bytes(2)) # unknown
		for mail in player.char.mails:
			mails.write(c_int64(mail.id))
			mails.write(mail.subject, allocated_length=50)
			mails.write(mail.body, allocated_length=400)
			mails.write(mail.sender, allocated_length=32)
			mails.write(bytes(12))
			if mail.attachment is None:
				mails.write(c_int64(0)) # attachment object id
				mails.write(c_int(-1)) # attachment LOT
				mails.write(bytes(12))
				mails.write(c_ushort(0)) # attachment count
			else:
				mails.write(c_int64(mail.attachment.object_id))
				mails.write(c_int(mail.attachment.lot))
				mails.write(bytes(12))
				mails.write(c_ushort(mail.attachment.count))
			mails.write(bytes(6))
			mails.write(c_uint64(mail.send_time))
			mails.write(c_uint64(mail.send_time))
			mails.write(c_bool(mail.is_read))
			mails.write(bytes(1))
			mails.write(bytes(2))
			mails.write(bytes(4))
		server.send(mails, player.char.address)

	def _on_mail_attachment_collect(self, data: ReadStream, player: Player) -> None:
		data.skip_read(4) # ???
		mail_id = data.read(c_int64)
		for mail in player.char.mails:
			if mail.id == mail_id:
				player.inventory.add_item(mail.attachment.lot, mail.attachment.count)
				mail.attachment = None
				out = WriteStream()
				out.write_header(WorldClientMsg.Mail)
				out.write(c_uint(MailID.MailAttachmentCollectResponse))
				out.write(bytes(4))
				out.write(c_int64(mail_id))
				server.send(out, player.char.address)
				break

	def _on_mail_delete(self, data: ReadStream, player: Player) -> None:
		data.skip_read(4) # ???
		mail_id = data.read(c_int64)
		for mail in player.char.mails:
			if mail.id == mail_id:
				player.char.mails.remove(mail)
				out = WriteStream()
				out.write_header(WorldClientMsg.Mail)
				out.write(c_uint(MailID.MailDeleteResponse))
				out.write(bytes(4))
				out.write(c_int64(mail_id))
				server.send(out, player.char.address)
				break

	def _on_mail_read(self, data: ReadStream, player: Player) -> None:
		data.skip_read(4) # ???
		mail_id = data.read(c_int64)
		for mail in player.char.mails:
			if mail.id == mail_id:
				mail.is_read = True
				out = WriteStream()
				out.write_header(WorldClientMsg.Mail)
				out.write(c_uint(MailID.MailReadResponse))
				out.write(bytes(4))
				out.write(c_int64(mail_id))
				server.send(out, player.char.address)
				break

	def _send_mail_notification(self, player: Player) -> None:
		unread_mails_count = len([mail for mail in player.char.mails if not mail.is_read])
		if unread_mails_count == 0:
			return
		notification = WriteStream()
		notification.write_header(WorldClientMsg.Mail)
		notification.write(c_uint(MailID.MailNotification))
		notification.write(bytes(4)) # notification type, seems only 0 is used
		notification.write(bytes(32))
		notification.write(c_uint(unread_mails_count))
		notification.write(bytes(4))
		server.send(notification, player.char.address)

class Mail(persistent.Persistent):
	def __init__(self, id: int, sender: str, subject: str, body: str, attachment: Stack=None):
		self.id = id
		self.send_time = int(time.time())
		self.is_read = False
		self.sender = sender
		self.subject = subject
		if len(body) >= 400:
			raise ValueError("Body too long")
		self.body = body
		self.attachment = attachment
