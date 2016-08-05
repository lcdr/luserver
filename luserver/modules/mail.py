import time
from enum import IntEnum

import persistent

from ..bitstream import BitStream, c_bool, c_int, c_int64, c_uint, c_uint64, c_ushort
from ..messages import WorldClientMsg, WorldServerMsg
from .module import ServerModule

class MailID(IntEnum):
	MailSend = 0
	MailSendResponse = 1
	MailNotification = 2
	MailDataRequest = 3
	MailData = 4
	MailDelete = 7
	MailDeleteResponse = 8
	MailRead = 9
	MailReadResponse = 10
	MailNotificationRequest = 11

class MailSendReturnCode:
	Success = 0
	ItemCannotBeMailed = 3
	CannotMailYourself = 4
	RecipientNotFound = 5
	UnknownFailure = 7

class MailHandling(ServerModule):
	def on_validated(self, address):
		self.server.register_handler(WorldServerMsg.Mail, self.on_mail, address)

	def on_mail(self, message, address):
		mail_id = message.read(c_uint)
		player = self.server.accounts[address].characters.selected()
		if mail_id == MailID.MailSend:
			self.on_mail_send(message, player)
		elif mail_id == MailID.MailDataRequest:
			self.send_mail_data(player)
		elif mail_id == MailID.MailDelete:
			self.on_mail_delete(message, player)
		elif mail_id == MailID.MailRead:
			self.on_mail_read(message, player)
		elif mail_id == MailID.MailNotificationRequest:
			if player.mails:
				self.send_mail_notification(player)

	def on_mail_send(self, data, player):
		subject = data.read(str, allocated_length=100)
		body = data.read(str, allocated_length=800)
		recipient_name = data.read(str, allocated_length=64)
		assert data.read(c_uint64) == 0
		attachment_item_object_id = data.read(c_int64)
		attachment_item_count = data.read(c_ushort)

		return_code = MailSendReturnCode.Success
		try:
			if attachment_item_count != 0:
				self.server.chat.send_general_chat_message("", "Attachments aren't implemented at the moment.", player.address, broadcast=False)
				return_code = MailSendReturnCode.ItemCannotBeMailed
				return
			if recipient_name == player.name:
				return_code = MailSendReturnCode.CannotMailYourself
				return
			try:
				recipient = self.server.find_player_by_name(recipient_name)
			except KeyError:
				return_code = MailSendReturnCode.RecipientNotFound
				return
			self.send_mail(player.name, subject, body, recipient)
		except Exception:
			import traceback
			traceback.print_exc()
			return_code = MailSendReturnCode.UnknownFailure
		finally:
			out = BitStream()
			out.write_header(WorldClientMsg.Mail)
			out.write(c_uint(MailID.MailSendResponse))
			out.write(c_uint(return_code))
			self.server.send(out, player.address)

	def send_mail(self, sender, subject, body, recipient):
		mail = Mail(self.server.new_object_id(), sender=sender, subject=subject, body=body)
		recipient.mails.append(mail)
		self.send_mail_notification(recipient)

	def send_mail_data(self, player):
		mails = BitStream()
		mails.write_header(WorldClientMsg.Mail)
		mails.write(c_uint(MailID.MailData))
		mails.write(bytes(4)) # return code success (enum is a bit overkill here)
		mails.write(c_ushort(len(player.mails)))
		mails.write(bytes(2)) # unknown
		for mail in player.mails:
			mails.write(c_int64(mail.id))
			mails.write(mail.subject, allocated_length=100)
			mails.write(mail.body, allocated_length=800)
			mails.write(mail.sender, allocated_length=64)
			mails.write(bytes(12))
			mails.write(c_int64(0)) # attachment object id
			mails.write(c_int(-1)) # attachment LOT
			mails.write(bytes(12))
			mails.write(c_ushort(0)) # attachment amount
			mails.write(bytes(6))
			mails.write(c_uint64(mail.send_time))
			mails.write(c_uint64(mail.send_time))
			mails.write(c_bool(mail.is_read))
			mails.write(bytes(1))
			mails.write(bytes(2))
			mails.write(bytes(4))
		self.server.send(mails, player.address)

	def on_mail_delete(self, data, player):
		data.skip_read(4) # ???
		mail_id = data.read(c_int64)
		for mail in player.mails:
			if mail.id == mail_id:
				player.mails.remove(mail)
				break
		out = BitStream()
		out.write_header(WorldClientMsg.Mail)
		out.write(c_uint(MailID.MailDeleteResponse))
		out.write(bytes(4))
		out.write(c_int64(mail_id))
		self.server.send(out, player.address)

	def on_mail_read(self, data, player):
		data.skip_read(4) # ???
		mail_id = data.read(c_int64)
		for mail in player.mails:
			if mail.id == mail_id:
				mail.is_read = True
				break
		out = BitStream()
		out.write_header(WorldClientMsg.Mail)
		out.write(c_uint(MailID.MailReadResponse))
		out.write(bytes(4))
		out.write(c_int64(mail_id))
		self.server.send(out, player.address)

	def send_mail_notification(self, player):
		notification = BitStream()
		notification.write_header(WorldClientMsg.Mail)
		notification.write(c_uint(MailID.MailNotification))
		notification.write(bytes(4)) # notification type, seems only 0 is used
		notification.write(bytes(32))
		notification.write(c_uint(len([mail for mail in player.mails if not mail.is_read])))
		notification.write(bytes(4))
		self.server.send(notification, player.address)


class Mail(persistent.Persistent):
	def __init__(self, id, sender, subject, body):
		self.id = id
		self.send_time = int(time.time())
		self.is_read = False
		self.sender = sender
		self.subject = subject
		self.body = body
