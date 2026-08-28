"""Retroactively clean up existing orphan SavedGrant rows.

Issue #22: orphan SavedGrant rows accumulated before the sync-time GC in #21
was deployed. This one-off data migration deletes them so the table starts clean.

Revision ID: 49d90bcc1dd5
Revises: abc123def456
Create Date: 2026-08-28
"""
from __future__ import annotations

import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49d90bcc1dd5'
down_revision: Union[str, Sequence[str], None] = 'abc123def456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Compiled patterns — same as sync_service._cleanup_orphan_saved_grants.
_FOUNDATION_GRANT_ID_RE = re.compile(r"^foundation-(\d+)$")
_GRANT_GRANT_ID_RE = re.compile(r"^grant-(\d+)$")


def _cleanup_orphan_saved_grants(conn, log=print) -> tuple[int, int]:
    """Delete SavedGrant rows whose grant_id no longer resolves to a live row.

    Extracted so the data-cleanup logic is unit-testable with a fake connection.

    An "orphan" is one of:
      * `foundation-N` where no Foundation row has `foundation_id = N`
      * `grant-N`       where no Grant row has `id = N`

    Rows whose grant_id does not match either pattern are LEFT ALONE — they
    represent valid saved grants in some other format we don't manage here.

    Returns a (foundation_orphans_deleted, grant_orphans_deleted) tuple.
    Safe to call when there are zero orphans (no-op).
    """
    meta = sa.MetaData()
    saved_grants = sa.Table('saved_grants', meta, autoload_with=conn)
    foundations = sa.Table('foundations', meta, autoload_with=conn)
    grants = sa.Table('grants', meta, autoload_with=conn)

    # --- foundation-{N} orphans ----------------------------------------------
    # Build the set of currently-live foundation_ids from the foundations table.
    live_foundation_ids: set[int] = set()
    for row in conn.execute(sa.select(foundations.c.foundation_id)).fetchall():
        live_foundation_ids.add(int(row[0]))

    # Select all rows that look like foundation-{digits} (regex match in SQL).
    foundation_candidate_rows = conn.execute(
        sa.select(saved_grants.c.id, saved_grants.c.grant_id).where(
            saved_grants.c.grant_id.op('~')('^foundation-\\d+$')
        )
    ).fetchall()

    foundation_orphan_ids: list[int] = []
    for saved_id, grant_id in foundation_candidate_rows:
        m = _FOUNDATION_GRANT_ID_RE.match(grant_id)
        if not m:
            continue
        foundation_id = int(m.group(1))
        if foundation_id not in live_foundation_ids:
            foundation_orphan_ids.append(saved_id)

    foundation_orphans = 0
    if foundation_orphan_ids:
        foundation_orphans = len(foundation_orphan_ids)
        # Delete in a single statement using SQLAlchemy's IN clause.
        conn.execute(
            saved_grants.delete().where(saved_grants.c.id.in_(foundation_orphan_ids))
        )

    # --- grant-{N} orphans ----------------------------------------------------
    # Re-read: the previous DELETE hasn't been committed yet so the second
    # SELECT still sees foundation-prefix rows that survived (live ones).
    # Grant-prefix rows are unaffected.
    live_grant_ids: set[int] = set()
    for row in conn.execute(sa.select(grants.c.id)).fetchall():
        live_grant_ids.add(int(row[0]))

    grant_candidate_rows = conn.execute(
        sa.select(saved_grants.c.id, saved_grants.c.grant_id).where(
            saved_grants.c.grant_id.op('~')('^grant-\\d+$')
        )
    ).fetchall()

    grant_orphan_ids: list[int] = []
    for saved_id, grant_id in grant_candidate_rows:
        m = _GRANT_GRANT_ID_RE.match(grant_id)
        if not m:
            continue
        grant_id_int = int(m.group(1))
        if grant_id_int not in live_grant_ids:
            grant_orphan_ids.append(saved_id)

    grant_orphans = 0
    if grant_orphan_ids:
        grant_orphans = len(grant_orphan_ids)
        conn.execute(
            saved_grants.delete().where(saved_grants.c.id.in_(grant_orphan_ids))
        )

    log(
        f"[49d90bcc1dd5] Orphan cleanup: {foundation_orphans} foundation orphans, "
        f"{grant_orphans} grant orphans deleted."
    )
    return foundation_orphans, grant_orphans


def upgrade() -> None:
    """Delete all orphan SavedGrant rows accumulated before #21 sync-time GC."""
    conn = op.get_bind()
    _cleanup_orphan_saved_grants(conn)


def downgrade() -> None:
    """No-op — rows are deleted and cannot be recovered safely."""
    pass
