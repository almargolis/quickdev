from unittest.mock import patch, MagicMock
import os
import tempfile

from qdbase.qdemail import SmtpConfig, send_email, init_email
import qdbase.qdemail as qdemail_module


def setup_function():
    """Reset module-level config before each test."""
    qdemail_module._config = None


# ---- SmtpConfig tests ----


def test_smtp_config_defaults():
    cfg = SmtpConfig()
    assert cfg.server == 'localhost'
    assert cfg.port == 587
    assert cfg.use_tls is True
    assert cfg.username == ''
    assert cfg.password == ''
    assert cfg.default_sender == 'noreply@example.com'


def test_smtp_config_custom():
    cfg = SmtpConfig(
        server='smtp.example.com', port=465, use_tls=False,
        username='user', password='pass', default_sender='me@example.com',
    )
    assert cfg.server == 'smtp.example.com'
    assert cfg.port == 465
    assert cfg.use_tls is False


# ---- send_email without real SMTP ----


def test_send_unconfigured_returns_false():
    """Default config (server=localhost) skips sending."""
    cfg = SmtpConfig()
    result = send_email("Test", ["a@b.com"], "body", config=cfg)
    assert result is False


def test_send_empty_server_returns_false():
    cfg = SmtpConfig(server='')
    result = send_email("Test", ["a@b.com"], "body", config=cfg)
    assert result is False


def test_send_no_recipients_returns_false():
    cfg = SmtpConfig(server='smtp.example.com')
    result = send_email("Test", [], "body", config=cfg)
    assert result is False


def test_send_blank_recipients_returns_false():
    cfg = SmtpConfig(server='smtp.example.com')
    result = send_email("Test", ["", "  "], "body", config=cfg)
    assert result is False


def test_send_string_recipient_normalized():
    """A single string recipient is accepted."""
    cfg = SmtpConfig(server='smtp.example.com')
    with patch('qdbase.qdemail.smtplib') as mock_smtplib:
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value = mock_server
        result = send_email("Subj", "one@example.com", "body", config=cfg)
    assert result is True
    mock_server.sendmail.assert_called_once()
    args = mock_server.sendmail.call_args[0]
    assert args[1] == ["one@example.com"]


@patch('qdbase.qdemail.smtplib')
def test_send_tls(mock_smtplib):
    """TLS uses SMTP + starttls."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server
    cfg = SmtpConfig(server='smtp.example.com', use_tls=True)
    result = send_email("Subj", ["a@b.com"], "body", config=cfg)
    assert result is True
    mock_smtplib.SMTP.assert_called_once_with('smtp.example.com', 587)
    mock_server.starttls.assert_called_once()
    mock_server.sendmail.assert_called_once()
    mock_server.quit.assert_called_once()


@patch('qdbase.qdemail.smtplib')
def test_send_ssl(mock_smtplib):
    """Non-TLS uses SMTP_SSL, no starttls."""
    mock_server = MagicMock()
    mock_smtplib.SMTP_SSL.return_value = mock_server
    cfg = SmtpConfig(server='smtp.example.com', port=465, use_tls=False)
    result = send_email("Subj", ["a@b.com"], "body", config=cfg)
    assert result is True
    mock_smtplib.SMTP_SSL.assert_called_once_with('smtp.example.com', 465)
    mock_server.sendmail.assert_called_once()


@patch('qdbase.qdemail.smtplib')
def test_send_with_login(mock_smtplib):
    """Credentials trigger server.login()."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server
    cfg = SmtpConfig(
        server='smtp.example.com', username='user', password='pass',
    )
    send_email("Subj", ["a@b.com"], "body", config=cfg)
    mock_server.login.assert_called_once_with('user', 'pass')


@patch('qdbase.qdemail.smtplib')
def test_send_without_login(mock_smtplib):
    """No credentials means no login call."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server
    cfg = SmtpConfig(server='smtp.example.com')
    send_email("Subj", ["a@b.com"], "body", config=cfg)
    mock_server.login.assert_not_called()


@patch('qdbase.qdemail.smtplib')
def test_send_custom_sender(mock_smtplib):
    """Explicit sender overrides config default."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server
    cfg = SmtpConfig(
        server='smtp.example.com', default_sender='default@example.com',
    )
    send_email("Subj", ["a@b.com"], "body",
               sender="custom@example.com", config=cfg)
    args = mock_server.sendmail.call_args[0]
    assert args[0] == "custom@example.com"


@patch('qdbase.qdemail.smtplib')
def test_send_default_sender(mock_smtplib):
    """No explicit sender uses config default."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server
    cfg = SmtpConfig(
        server='smtp.example.com', default_sender='default@example.com',
    )
    send_email("Subj", ["a@b.com"], "body", config=cfg)
    args = mock_server.sendmail.call_args[0]
    assert args[0] == "default@example.com"


@patch('qdbase.qdemail.smtplib')
def test_send_smtp_failure_returns_false(mock_smtplib):
    """SMTP exception returns False instead of raising."""
    mock_smtplib.SMTP.side_effect = Exception("connection refused")
    cfg = SmtpConfig(server='smtp.example.com')
    result = send_email("Subj", ["a@b.com"], "body", config=cfg)
    assert result is False


@patch('qdbase.qdemail.smtplib')
def test_send_with_file_attachment(mock_smtplib):
    """File path attachment is included in the message."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server
    cfg = SmtpConfig(server='smtp.example.com')

    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b"attachment content")
        tmp_path = f.name

    try:
        result = send_email(
            "Subj", ["a@b.com"], "body",
            config=cfg, attachments=[tmp_path],
        )
        assert result is True
        raw_msg = mock_server.sendmail.call_args[0][2]
        assert os.path.basename(tmp_path) in raw_msg
        assert 'attachment content' not in raw_msg  # base64 encoded
    finally:
        os.unlink(tmp_path)


@patch('qdbase.qdemail.smtplib')
def test_send_with_named_attachment(mock_smtplib):
    """Tuple attachment uses the display name."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server
    cfg = SmtpConfig(server='smtp.example.com')

    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b"data")
        tmp_path = f.name

    try:
        result = send_email(
            "Subj", ["a@b.com"], "body",
            config=cfg, attachments=[("report.txt", tmp_path)],
        )
        assert result is True
        raw_msg = mock_server.sendmail.call_args[0][2]
        assert 'report.txt' in raw_msg
    finally:
        os.unlink(tmp_path)


# ---- init_email / auto-init tests ----


@patch('qdbase.qdemail.QdConf')
def test_init_email(mock_qdconf_class):
    """init_email loads config from QdConf and returns SmtpConfig."""
    mock_conf = MagicMock()
    mock_conf.get.side_effect = lambda key, default=None: {
        'qdemail.MAIL_SERVER': 'smtp.test.com',
        'qdemail.MAIL_PORT': 465,
        'qdemail.MAIL_USE_TLS': False,
        'qdemail.MAIL_USERNAME': 'testuser',
        'denv.SMTP_PW': 'testpass',
        'qdemail.MAIL_DEFAULT_SENDER': 'test@test.com',
    }.get(key, default)
    mock_qdconf_class.return_value = mock_conf

    cfg = init_email(conf_dir='/tmp/test')
    assert cfg.server == 'smtp.test.com'
    assert cfg.port == 465
    assert cfg.use_tls is False
    assert cfg.username == 'testuser'
    assert cfg.password == 'testpass'
    assert cfg.default_sender == 'test@test.com'
    mock_qdconf_class.assert_called_once_with(conf_dir='/tmp/test')


@patch('qdbase.qdemail.QdConf')
@patch('qdbase.qdemail.smtplib')
def test_auto_init_on_first_send(mock_smtplib, mock_qdconf_class):
    """send_email auto-calls init_email when no config exists."""
    mock_conf = MagicMock()
    mock_conf.get.side_effect = lambda key, default=None: {
        'qdemail.MAIL_SERVER': 'smtp.auto.com',
    }.get(key, default)
    mock_qdconf_class.return_value = mock_conf

    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server

    result = send_email("Subj", ["a@b.com"], "body")
    assert result is True
    mock_qdconf_class.assert_called_once()
