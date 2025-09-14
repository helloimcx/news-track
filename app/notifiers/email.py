"""
Email Notifier for sending news digests via email.
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from app.models import Digest
from app.config import EmailConfig

class EmailNotifier:
    """
    A notifier that sends news digests via email.
    """

    def __init__(self, config: EmailConfig | None):
        """
        Initializes the Email Notifier using configuration.

        Args:
            config: An EmailConfig object containing SMTP and email settings.
                    Can be None, in which case sending will fail gracefully.
        """
        if config is None:
            raise ValueError("Email configuration is required for EmailNotifier.")
            
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port
        self.username = config.username
        self.password = config.password
        self.sender_email = config.sender_email
        # Split the comma-separated string into a list
        self.recipient_emails = [email.strip() for email in config.recipient_emails.split(',')]

    async def send_digest(self, digest: Digest):
        """
        Asynchronously sends a Digest via email.

        Args:
            digest: The Digest object to send.
            
        Raises:
            Exception: If an error occurs during the sending process.
        """
        # 1. Create the email message
        message = MIMEMultipart("alternative")
        message["Subject"] = digest.title
        message["From"] = self.sender_email
        message["To"] = ", ".join(self.recipient_emails)

        # 2. Create the HTML version of the message
        html_content = self._create_html_content(digest)
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # 3. Send the email using aiosmtplib
        try:
            # Choose encryption method based on port
            if self.smtp_port == 465:
                # Port 465 uses SSL
                await aiosmtplib.send(
                    message,
                    recipients=self.recipient_emails,
                    hostname=self.smtp_server,
                    port=self.smtp_port,
                    username=self.username,
                    password=self.password,
                    use_tls=True  # Use SSL for port 465
                )
            else:
                # Port 587 and others use STARTTLS
                await aiosmtplib.send(
                    message,
                    recipients=self.recipient_emails,
                    hostname=self.smtp_server,
                    port=self.smtp_port,
                    username=self.username,
                    password=self.password,
                    start_tls=True  # Use STARTTLS for port 587
                )
        except Exception as e:
            # Re-raise the exception for the caller to handle
            raise e

    def _create_html_content(self, digest: Digest) -> str:
        """
        Creates the HTML content for the email body.

        Args:
            digest: The Digest object.

        Returns:
            A string containing the HTML content.
        """
        html = f"""
        <html>
          <body>
            <h2>{digest.title}</h2>
        """
        # 如果有汇总摘要，先显示它
        if digest.overall_summary:
            html += f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <h3>📋 广东考公汇总摘要</h3>
                <p>{digest.overall_summary}</p>
            </div>
            <hr>
            <h3>各文章详细内容：</h3>
            """
        else:
            html += "<p>以下是最新的文章摘要：</p>"
            
        for i, article in enumerate(digest.articles, 1):
            html += f"""
            <h3>{i}. {article.original_article.title}</h3>
            <p><b>摘要:</b> {article.summary}</p>
            <p><b>要点:</b> {', '.join(article.key_points)}</p>
            <p><b>标签:</b> {', '.join(article.tags)}</p>
            <p><a href="{article.original_article.url}" style="color: #0066cc;">阅读原文</a></p>
            <hr>
            """
        
        html += """
          </body>
        </html>
        """
        return html