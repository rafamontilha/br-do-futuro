"""Keep the documented fresh-database bootstrap in sync with versioned migrations."""
import re
from pathlib import Path


def test_compose_initializes_all_migrations_in_order_read_only():
    # Inspect the short bind-mount syntax used by the database service. No Docker
    # daemon or destructive volume reset is needed to detect a missing migration.
    compose = Path('compose.yaml').read_text()
    db_service = compose.split('\n  db:\n', 1)[1].split('\n  ingestion:\n', 1)[0]
    mounts = re.findall(
        r'^\s+- \./(db/[^:\s]+\.sql):(/docker-entrypoint-initdb\.d/[^:\s]+):(\S+)\s*$',
        db_service, re.MULTILINE,
    )
    expected = sorted(Path('db').glob('[0-9][0-9][0-9]_*.sql'))
    assert expected, 'No versioned migrations found'
    assert [source for source, _, _ in mounts] == [p.as_posix() for p in expected]
    assert [target for _, target, _ in mounts] == [
        f'/docker-entrypoint-initdb.d/{p.name[:3]}.sql' for p in expected
    ]
    assert all(mode == 'ro' for _, _, mode in mounts)
