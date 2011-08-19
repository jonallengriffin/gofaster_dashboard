# taken from http://hg.mozilla.org/automation/orangefactor/file/5894e67315f8/sendemail.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def SendEmail(From=None, To=None, Subject='No Subject', 
              TextData=None, HtmlData=None,
              Server='mail.mozilla.com', Port=465,
              Username=None, Password=None, UseSsl=True):
  """Sends an e-mail.
  
     From is an e-mail address, To is a list of e-mail adresses.
     
     TextData and HtmlData are both strings.  You can specify one or both.
     If you specify both, the e-mail will be sent as a MIME multipart
     alternative; i.e., the recipient will see the HTML content if his
     viewer supports it, otherwise he'll see the text content.
  """

  if From is None or To is None:
    raise Exception("Both From and To must be specified")
  if TextData is None and HtmlData is None:
    raise Exception("Must specify either TextData or HtmlData")

  if UseSsl:
    server = smtplib.SMTP_SSL(Server, Port)
  else:
    server = smtplib.SMTP(Server, Port)

  if Username is not None and Password is not None:
    server.login(Username, Password)

  if HtmlData is None:
    msg = MIMEText(TextData)
  elif TextData is None:
    msg = MIMEMultipart()
    msg.preamble = Subject
    msg.attach(MIMEText(HtmlData, 'html'))
  else:
    msg = MIMEMultipart('alternative')
    msg.attach(MIMEText(TextData, 'plain'))
    msg.attach(MIMEText(HtmlData, 'html'))

  msg['Subject'] = Subject
  msg['From'] = From
  msg['To'] = ', '.join(To)

  server.sendmail(From, To, msg.as_string())

  server.quit()
