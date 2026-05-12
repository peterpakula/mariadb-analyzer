import mariadb
from unittest.mock import Mock
from src.mariadb_analyzer.cli import format_uptime, get_processlist, get_variables, get_status
from src.mariadb_analyzer.cli import format_bytes

def test_get_processlist():
    mariadb.connect = Mock()
    mock_cursor = mariadb.connect.return_value.cursor.return_value
    mock_cursor.fetchall.return_value = [
        (310, 'dev', '192.168.178.46:47170', None, 'Query', 0, 'starting', 'SHOW PROCESSLIST', 0.0)
    ]
    for mock_cursor_row in get_processlist(mock_cursor):
        assert mock_cursor_row[2] == "192.168.178.46:47170"

def test_get_variables():
    mariadb.connect = Mock()
    mock_cursor = mariadb.connect.return_value.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ('hostname', 'test-server'),
        ('uptime', 297760)
    ]
    mock_cursor_dict = get_variables(mock_cursor)
    assert mock_cursor_dict.get("hostname") == "test-server"
    assert format_uptime(mock_cursor_dict.get("uptime")) == "3 days, 10 hours, 42 minutes, 40 seconds"

def test_get_status():
    mariadb.connect = Mock()
    mock_cursor = mariadb.connect.return_value.cursor.return_value
    mock_cursor.fetchall.return_value = [
        ('Qcache_hits', 9999)
    ]
    mock_cursor_dict = get_status(mock_cursor)
    assert mock_cursor_dict.get("Qcache_hits") == 9999

def test_format_uptime():
    assert format_uptime(297760) == "3 days, 10 hours, 42 minutes, 40 seconds"

def test_format_bytes_128mb():
    assert format_bytes(134217728) == "128.0 MB"

def test_format_bytes_1024kb():
    assert format_bytes(1048576) == "1024.0 KB"

def test_format_bytes_100kb():
    assert format_bytes(102400) == "100.0 KB"
