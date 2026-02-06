import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailNotification():
    def __init__(self):
        pass

    def sendNotification(self, subject: str, body="") -> None:
        sender_email = os.getenv('EMAIL')
        receiver_email = os.getenv('RECEIVER')
        password = os.getenv('PASSWORD')
        subject = subject

        if body == "":
            body = "No se agregaron nuevos eventos"

        body = str(body)

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain", "utf-8"))

        try:
            # Conecta con el servidor SMTP de Gmail
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()  # Inicia la conexión segura
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            server.quit()
            print("\nCorreo enviado con éxito. 🚀")
        except Exception as e:
            print(f"Error enviando el correo: {e}")
