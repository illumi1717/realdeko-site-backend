import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

import os
from dotenv import load_dotenv

load_dotenv()


# --- КОНФИГУРАЦИЯ ---
smtp_server = "smtp.seznam.cz"
smtp_port = 465  # Порт для SSL (защищенное соединение)
context = ssl.create_default_context()

sender_email = os.getenv("SENDER_MAIL")  # Ваш полный адрес
password = os.getenv("SENDER_PASS")  # Пароль (лучше использовать App Password)
receiver_email = os.getenv("RECIVER_MAIL")  # Кому отправляем

DEKOSTAVBY_HTML_TEMPLATE = """\
<html>
  <body>
    <p>Заявка з сайту DekoStavby<br>
       Ім'я: [Ім'я]<br>
       Телефон: [Телефон]<br>
       Email: [Email]<br>
       Послуга: [Послуга]<br>
       Повідомлення: [Повідомлення]<br>
    </p>
  </body>
</html>
"""

REALDEKOGROUP_HTML_TEMPLATE = """\
<html>
  <body>
    <h2>Нова заявка з сайту RealDekoGroup</h2>
    <table style="border-collapse:collapse;">
      <tr><td style="padding:4px 12px;font-weight:bold;">Ім'я:</td><td style="padding:4px 12px;">[Ім'я]</td></tr>
      <tr><td style="padding:4px 12px;font-weight:bold;">Телефон:</td><td style="padding:4px 12px;">[Телефон]</td></tr>
      <tr><td style="padding:4px 12px;font-weight:bold;">Повідомлення:</td><td style="padding:4px 12px;">[Повідомлення]</td></tr>
    </table>
  </body>
</html>
"""


def send_email(name: str, phone: str, email: str, service: str, user_message: str):
    """Send application email via Seznam SMTP with simple HTML body (DekoStavby)."""
    html_body = (
        DEKOSTAVBY_HTML_TEMPLATE.replace("[Ім'я]", name)
        .replace("[Телефон]", phone)
        .replace("[Email]", email or "")
        .replace("[Послуга]", service or "")
        .replace("[Повідомлення]", user_message)
    )

    email_message = MIMEMultipart("alternative")
    email_message["Subject"] = "Заявка з сайту DekoStavby"
    email_message["From"] = sender_email
    email_message["To"] = receiver_email
    email_message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, email_message.as_string())
            return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def send_realdekogroup_email(name: str, phone: str, message: str):
    """Send application email via Seznam SMTP for RealDekoGroup site."""
    html_body = (
        REALDEKOGROUP_HTML_TEMPLATE.replace("[Ім'я]", name)
        .replace("[Телефон]", phone)
        .replace("[Повідомлення]", message)
    )

    email_message = MIMEMultipart("alternative")
    email_message["Subject"] = "Нова заявка з сайту RealDekoGroup"
    email_message["From"] = sender_email
    email_message["To"] = 'mykhailo.kohutka@seznam.cz'
    email_message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, 'mykhailo.kohutka@seznam.cz', email_message.as_string())
            return True
    except Exception as e:
        print(f"RealDekoGroup email send error: {e}")
        return False

