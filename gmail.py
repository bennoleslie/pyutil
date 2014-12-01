import email.message
import imaplib
import random
import time
import xoauth
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

class Gmail:
    def __init__(self, email, token, secret):
        self.email = email
        self.token = token
        self.secret = secret
        self._imap = None

    @classmethod
    def from_config_file(cls, filename):
        with open(filename) as f:
            email = f.readline().strip()
            token = f.readline().strip()
            secret = f.readline().strip()
            return cls(email, token, secret)

    @property
    def imap(self):
        if self._imap is None:
            nonce = str(random.randrange(2**64 - 1))
            timestamp = str(int(time.time()))
            consumer = xoauth.OAuthEntity('anonymous', 'anonymous')
            access = xoauth.OAuthEntity(self.token, self.secret)
            token = xoauth.GenerateXOauthString(consumer, access, self.email,
                                                'imap', self.email, nonce, timestamp)
            self._imap = imaplib.IMAP4_SSL('imap.googlemail.com')
            self._imap.authenticate(b'XOAUTH', lambda x: token.encode())
        return self._imap

    def add_to_draft(self, msg):
        now = imaplib.Time2Internaldate(time.time())
        self.imap.append('[Gmail]/Drafts', '', now, str(msg).encode())

    def simple_message(self, subject, recipient, body, attachments):
        # create the message
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email
        msg['To'] = recipient
        msg.attach(MIMEText(body))

        for f in attachments:
            part = MIMEBase('application', "octet-stream")
            part.set_payload( open(f,"rb").read() )
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
            msg.attach(part)

        return msg

    def close(self):
        if self._imap is not None:
            self._imap.logout()
