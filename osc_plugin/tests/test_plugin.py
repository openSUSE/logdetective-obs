import pytest


@pytest.fixture
def ld():
    from osc_ld_plugin.plugin import LogDetective
    ld = LogDetective("ld.LogDetective")
    return ld


def test_import():
    import osc_ld_plugin.plugin
    assert osc_ld_plugin.plugin is not None


def test_cli_help(ld, capsys):
    with pytest.raises(SystemExit):
        ld.parser.parse_args(["--help"])

    captured = capsys.readouterr()
    assert "LogDetective" in captured.out


@pytest.mark.vcr
def test_package_remote(ld, capsys):
    args = ld.parser.parse_args("-r --repo openSUSE_Tumbleweed --project devel:languages:python --package python-actdiag".split(" "))
    ld.run(args)

    captured = capsys.readouterr()
    assert "test_generate_diagram.py" in captured.out
