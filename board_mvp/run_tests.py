import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from board_mvp.tests import test_schema


def run():
    test_schema.test_schema_creation(tmp_path=ROOT)
    print('All tests passed.')


if __name__ == '__main__':
    run()
