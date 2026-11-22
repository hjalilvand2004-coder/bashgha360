"""integrity triggers: append-only rows + balanced ledger transactions (LED-01, DM-03).

Revision ID: a1b2c3d4e5f6
Revises: 278c1303e6e6
Create Date: 2026-11-11
"""
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "278c1303e6e6"
branch_labels = None
depends_on = None

_APPEND_ONLY_TABLES = ["ledger_entries", "audit_logs", "educational_events", "auth_audit"]


def upgrade() -> None:
    for table in _APPEND_ONLY_TABLES:
        op.execute(f"""
        CREATE OR REPLACE FUNCTION deny_mutate_{table}() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'جدول {table} بی‌ردپاست؛ ویرایش/حذف مجاز نیست (append-only)';
        END;
        $$ LANGUAGE plpgsql;
        """)
        op.execute(f"""
        DROP TRIGGER IF EXISTS trg_deny_mutate_{table} ON {table};
        CREATE TRIGGER trg_deny_mutate_{table}
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION deny_mutate_{table}();
        """)

    # Balanced transactions: Σdebit == Σcredit per tx, checked at COMMIT (deferrable)
    op.execute("""
    CREATE OR REPLACE FUNCTION check_ledger_tx_balanced() RETURNS trigger AS $$
    DECLARE
        debit_sum NUMERIC(14,2);
        credit_sum NUMERIC(14,2);
    BEGIN
        SELECT COALESCE(SUM(CASE WHEN direction='debit' THEN amount ELSE 0 END), 0),
               COALESCE(SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END), 0)
        INTO debit_sum, credit_sum
        FROM ledger_entries WHERE tx_id = NEW.id;
        IF debit_sum <> credit_sum THEN
            RAISE EXCEPTION 'تراکنش % متوازن نیست: debit=% credit=%', NEW.id, debit_sum, credit_sum;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    DROP TRIGGER IF EXISTS trg_ledger_tx_balanced ON ledger_transactions;
    CREATE CONSTRAINT TRIGGER trg_ledger_tx_balanced
        AFTER INSERT ON ledger_transactions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION check_ledger_tx_balanced();
    """)


def downgrade() -> None:
    for table in _APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_deny_mutate_{table} ON {table};")
        op.execute(f"DROP FUNCTION IF EXISTS deny_mutate_{table}();")
    op.execute("DROP TRIGGER IF EXISTS trg_ledger_tx_balanced ON ledger_transactions;")
    op.execute("DROP FUNCTION IF EXISTS check_ledger_tx_balanced();")
