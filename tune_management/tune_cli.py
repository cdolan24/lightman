# tune_cli.py

"""Human-facing tune actions: python -m tune_management.tune_cli --car-id 1 <command> ..."""

import argparse
import sys
from pathlib import Path

from tune_management.tune_manager import ApprovalRefused, InvalidTuneFile, StockTuneExists, TuneManager, TuneNotFound

def main(argv=None):
    parser = argparse.ArgumentParser(description="Manage a car's tunes.")
    parser.add_argument('--car-id', type=int, required=True)
    commands = parser.add_subparsers(dest='command', required=True)

    commands.add_parser('list', help="list tunes with origin and approval")

    imp = commands.add_parser('import', help="import a .lmtune export (arrives unapproved)")
    imp.add_argument('path')

    stock = commands.add_parser('save-stock', help="store the car's protected stock tune from a raw image file")
    stock.add_argument('path')
    stock.add_argument('--name', default="Stock")

    approve = commands.add_parser('approve', help="approve an imported or generated tune")
    approve.add_argument('tune_id', type=int)
    approve.add_argument('--by', required=True, help="your name")
    approve.add_argument('--note')

    args = parser.parse_args(argv)
    tm = TuneManager(args.car_id)
    try:
        if args.command == 'list':
            for t in tm.list_tunes():
                status = f"approved by {t['approved_by']}" if t['approved_at'] else "NOT APPROVED"
                print(f"{t['id']:>4}  {t['name']:<24} {t['origin']:<10} {status}")
        elif args.command == 'import':
            tune_id = tm.import_tune(args.path)
            print(f"Imported as tune {tune_id} (unapproved). Review it, then: approve {tune_id} --by <name>")
        elif args.command == 'save-stock':
            print(f"Stock tune saved as tune {tm.save_stock_tune(Path(args.path).read_bytes(), name=args.name)}")
        elif args.command == 'approve':
            tune = tm.approve_tune(args.tune_id, args.by, 'manual', args.note)
            print(f"Tune {tune['id']} '{tune['name']}' approved by {tune['approved_by']}")
    except (ApprovalRefused, InvalidTuneFile, StockTuneExists, TuneNotFound, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
