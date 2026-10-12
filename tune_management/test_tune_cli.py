# test_tune_cli.py

from tune_management.tune_cli import main
from tune_management.tune_manager import TuneManager

def test_import_approve_list(tmp_path, capsys):
    src = TuneManager(1)
    src.export_tune(src.save_tune("Shared", b"\x01"), tmp_path / "shared.lmtune")

    assert main(['--car-id', '2', 'import', str(tmp_path / "shared.lmtune")]) == 0
    main(['--car-id', '2', 'list'])
    assert "NOT APPROVED" in capsys.readouterr().out

    assert main(['--car-id', '2', 'approve', '1', '--by', 'Connor', '--note', 'checked']) == 0
    main(['--car-id', '2', 'list'])
    out = capsys.readouterr().out
    assert "approved by Connor (manual)" in out and "imported" in out

def test_save_stock_and_errors(tmp_path, capsys):
    image = tmp_path / "stock.bin"
    image.write_bytes(b"factory")
    assert main(['--car-id', '1', 'save-stock', str(image)]) == 0
    assert TuneManager(1).get_stock_tune()['data'] == b"factory"
    assert main(['--car-id', '1', 'save-stock', str(image)]) == 1
    assert main(['--car-id', '1', 'approve', '99', '--by', 'Connor']) == 1
    assert "already has a stock tune" in capsys.readouterr().err
