"""Rewrite saved-grant foundation ids to canonical external ids

Issue #19: saved grants stored grant_id as `foundation-{db_id}` where db_id is
the auto-increment surrogate (foundations.id). That surrogate renumbers on a
"clear database" + re-sync, silently breaking SavedGrant.grant_id rows.

This one-off data migration rewrites existing rows from
`foundation-{db_id}` → `foundation-{foundation_id}` using the CURRENT (still
present) foundations table mapping (id → foundation_id). Only `foundation-`
prefixed ids are touched; `grant-` ids are left untouched. Rows whose db_id no
longer has a matching foundation row are left UNCHANGED (best-effort; we do not
delete user data). The rewrite is idempotent — running it twice is a no-op.

Revision ID: abc123def456
Revises: 93d610535c3d
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, Sequence[str], None] = '93d610535c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rewrite_saved_grant_ids(conn, log=print):
    """Rewrite SavedGrant.grant_id from foundation-{db_id} to foundation-{foundation_id}.

    Extracted so the data-rewrite logic is unit-testable with a fake connection.

    - Selects rows whose grant_id matches the legacy `foundation-<digits>` shape.
    - Builds db_id -> foundation_id from the CURRENT foundations table.
    - Rewrites matching rows; leaves rows without a matching foundation UNCHANGED.
    - Idempotent (already-canonical rows are skipped).
    """
    meta = sa.MetaData()
    saved_grants = sa.Table('saved_grants', meta, autoload_with=conn)
    foundations = sa.Table('foundations', meta, autoload_with=conn)

    # Select rows whose grant_id is a legacy foundation-{db_id} reference.
    legacy_rows = conn.execute(
        sa.select(saved_grants.c.id, saved_grants.c.grant_id)
        .where(saved_grants.c.grant_id.op('~')('^foundation-\\d+$'))
    ).fetchall()

    # Map db_id -> foundation_id from the CURRENT foundations table while it exists.
    db_id_to_foundation_id = {}
    for row in conn.execute(sa.select(foundations.c.id, foundations.c.foundation_id)):
        db_id_to_foundation_id[row[0]] = row[1]

    rewritten = 0
    unchanged = 0
    for saved_id, grant_id in legacy_rows:
        db_id = int(grant_id.split('-', 1)[1])
        foundation_id = db_id_to_foundation_id.get(db_id)
        if foundation_id is None:
            # No matching foundation row (renumbered / deleted). Leave unchanged —
            # do not delete user data. Logged below for observability.
            unchanged += 1
            continue
        new_grant_id = f"foundation-{foundation_id}"
        if new_grant_id == grant_id:
            # Already canonical — idempotency guard.
            continue
        conn.execute(
            saved_grants.update()
            .where(saved_grants.c.id == saved_id)
            .values(grant_id=new_grant_id)
        )
        rewritten += 1

    log(
        f"[abc123def456] SavedGrant foundation-id rewrite: {rewritten} rewritten, "
        f"{unchanged} left unchanged (no matching foundation row)."
    )
    return rewritten, unchanged


def upgrade() -> None:
    """Rewrite SavedGrant.grant_id from foundation-{db_id} to foundation-{foundation_id}."""
    conn = op.get_bind()
    _rewrite_saved_grant_ids(conn)


def downgrade() -> None:
    """Reverse is a best-effort no-op.

    We deliberately do not attempt to reverse the rewrite: the foundations db_id
    -> foundation_id mapping may no longer be trustworthy by downgrade time, and
    reverting would risk writing wrong surrogate ids. A clean downgrade would
    require re-running a full sync with canonical ids.
    """
    pass
