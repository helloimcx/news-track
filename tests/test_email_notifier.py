import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.notifiers.email import EmailNotifier
from app.models import Article, ProcessedArticle, Digest
from app.config import EmailConfig

class TestEmailNotifier:

    @pytest.fixture
    def sample_digest(self):
        """Fixture to create a sample Digest instance."""
        article1 = Article(
            title="Test Article 1",
            url="https://example.com/article1",
            content="Content of test article 1.",
            source="Test Source"
        )
        processed_article1 = ProcessedArticle(
            original_article=article1,
            summary="Summary of article 1.",
            key_points=["Point A", "Point B"],
            sentiment=0.5,
            tags=["tag1", "tag2"]
        )
        
        article2 = Article(
            title="Test Article 2",
            url="https://example.com/article2",
            content="Content of test article 2.",
            source="Test Source"
        )
        processed_article2 = ProcessedArticle(
            original_article=article2,
            summary="Summary of article 2.",
            key_points=["Point C"],
            sentiment=-0.2,
            tags=["tag3"]
        )

        return Digest(
            title="Weekly Tech News Digest",
            articles=[processed_article1, processed_article2]
        )

    @pytest.fixture
    def email_config(self, monkeypatch):
        """Fixture to provide a mock EmailConfig and set required env vars."""
        # Define test environment variables
        test_env_vars = {
            "EMAIL__SMTP_SERVER": "smtp.test.com",
            "EMAIL__SMTP_PORT": "587",
            "EMAIL__USERNAME": "test_user",
            "EMAIL__PASSWORD": "test_pass",
            "EMAIL__SENDER_EMAIL": "sender@test.com",
            "EMAIL__RECIPIENT_EMAILS": "recipient1@test.com, recipient2@test.com"
        }
        
        # Set the environment variables using monkeypatch
        for key, value in test_env_vars.items():
            monkeypatch.setenv(key, value)
            
        # Create and return the EmailConfig instance
        # This will now load the values from the mocked environment
        return EmailConfig(
            smtp_server="smtp.test.com",
            smtp_port=587,
            username="test_user",
            password="test_pass",
            sender_email="sender@test.com",
            recipient_emails="recipient1@test.com, recipient2@test.com"
        )

    @pytest.mark.asyncio
    async def test_send_digest_success(self, sample_digest, email_config):
        """Test successful sending of a digest."""
        # Create notifier with the fixture config
        notifier = EmailNotifier(config=email_config)

        # Mock the aiosmtplib.send method
        with patch('app.notifiers.email.aiosmtplib.send') as mock_send:
            # Mock send to do nothing and return a successful result
            mock_send.return_value = (None, None) # aiosmtplib.send returns (response, reply)

            await notifier.send_digest(sample_digest)

            # Assert that aiosmtplib.send was called
            mock_send.assert_called_once()
            
            # Get the arguments passed to send
            # aiosmtplib.send(message, recipients=..., hostname=..., port=..., ...)
            call_args = mock_send.call_args
            args, kwargs = call_args
            
            # Assert message (first positional arg) and other keyword args
            message_arg = args[0] # message is the first positional argument
            recipients_arg = kwargs['recipients']
            hostname_arg = kwargs['hostname']
            port_arg = kwargs['port']
            username_arg = kwargs['username']
            password_arg = kwargs['password']
            
            # Assert the message content
            # The message is a MIMEText object, we need to check its string representation
            # or access its .as_string() method
            message_str = message_arg.as_string()
            assert "Weekly Tech News Digest" in message_str
            assert "Test Article 1" in message_str
            assert "Summary of article 1." in message_str
            assert "Test Article 2" in message_str
            
            # Assert the recipients and server config
            assert recipients_arg == ["recipient1@test.com", "recipient2@test.com"]
            assert hostname_arg == "smtp.test.com"
            assert port_arg == 587
            assert username_arg == "test_user"
            assert password_arg == "test_pass"


    @pytest.mark.asyncio
    async def test_send_digest_smtp_error(self, sample_digest, email_config):
        """Test handling of SMTP errors during sending."""
        notifier = EmailNotifier(config=email_config)

        # Mock the aiosmtplib.send method to raise an SMTP exception
        with patch('app.notifiers.email.aiosmtplib.send', side_effect=Exception("SMTP Error")):
            # Depending on the desired behavior, this could raise the exception
            # or log it and continue. For this test, let's assume it raises.
            with pytest.raises(Exception, match="SMTP Error"):
                await notifier.send_digest(sample_digest)