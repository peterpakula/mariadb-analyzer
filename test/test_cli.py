from src.mariadb_analyzer.cli import format_uptime

def test_format_uptime():
    assert format_uptime(297760) == "3 days, 10 hours, 42 minutes, 40 seconds"
