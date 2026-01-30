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

HTML_TEMPLATE = """\
<html>
  <body>
    <p>Заявка з сайту DekoStavby<br>
       Ім'я: [Ім'я]<br>
       Телефон: [Телефон]<br>
       Послуга: [Послуга]<br>
       Повідомлення: [Повідомлення]<br>
    </p>
  </body>
</html>
"""


def send_email(name: str, phone: str, service: str, user_message: str):
    """Send application email via Seznam SMTP with simple HTML body."""
    html_body = (
        HTML_TEMPLATE.replace("[Ім'я]", name)
        .replace("[Телефон]", phone)
        .replace("[Послуга]", service)
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
        return False


if __name__ == "__main__":
    send_email("John Doe", "+420 777 000 000", "Consultation", "I want to consult you about the project")