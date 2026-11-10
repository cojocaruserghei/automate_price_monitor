from price_monitor.cli import main


def test_help_command_returns_success(capsys):
    assert main(["--help"]) == 0
    assert "run_once" in capsys.readouterr().out
