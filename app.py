import hashlib
from datetime import date, datetime, timezone
import streamlit as st
from supabase import create_client
import uuid
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(
    page_title="S.P. Enterprise | Control System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------
# PROFESSIONAL UI THEME
# ---------------------------------------------------------------------
st.markdown("""
<style>
    /* ================================================================
       S.P. ENTERPRISE — GLOBAL DARK ERP THEME
       Component-specific selectors only; do not override arbitrary divs.
       ================================================================ */
    :root {
        --sp-bg: #0f1115;
        --sp-surface: #171a21;
        --sp-surface-2: #1d222b;
        --sp-border: #2b313c;
        --sp-text: #f3f4f6;
        --sp-muted: #a7b0bf;
        --sp-accent: #ff6b35;
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--sp-surface);
        border-right: 1px solid var(--sp-border);
    }
    [data-testid="stSidebar"] h1 {
        font-size: 1.25rem;
        margin-bottom: .25rem;
        color: var(--sp-text);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label {
        color: var(--sp-text);
    }

    /* Page headings */
    .module-title {
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -.02em;
        margin-bottom: .2rem;
        color: var(--sp-text);
    }
    .module-subtitle {
        color: var(--sp-muted);
        margin-bottom: 1.2rem;
    }
    .section-label {
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: var(--sp-muted);
        margin: .7rem 0 .45rem;
    }

    /* Metric cards — force the dark ERP treatment across Streamlit versions */
    div[data-testid="stMetric"],
    div[data-testid="stMetric"] > div,
    div[data-testid="stMetric"] [data-testid="metric-container"] {
        background: var(--sp-surface) !important;
        border: 1px solid var(--sp-border) !important;
        border-radius: 12px !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetric"] {
        padding: .9rem 1rem !important;
        min-height: 92px;
        overflow: hidden;
    }
    div[data-testid="stMetric"] * {
        background: transparent !important;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"],
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] * {
        color: var(--sp-muted) !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"],
    div[data-testid="stMetric"] [data-testid="stMetricValue"] * {
        color: var(--sp-text) !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"],
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] * {
        color: var(--sp-muted) !important;
    }

    /* Expander / bordered containers */
    div[data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid var(--sp-border);
        background: var(--sp-surface);
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary span {
        color: var(--sp-text) !important;
    }

    /* Custom status cards */
    .status-card {
        border: 1px solid var(--sp-border);
        border-radius: 12px;
        padding: 1rem;
        background: var(--sp-surface);
        min-height: 100px;
    }
    .status-card h4 {
        margin: 0 0 .3rem;
        color: var(--sp-text);
    }
    .status-card p {
        margin: 0;
        color: var(--sp-muted);
        font-size: .9rem;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        color: var(--sp-muted) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--sp-accent) !important;
    }

    /* Inputs and BaseWeb controls */
    div[data-baseweb="input"],
    div[data-baseweb="select"],
    div[data-baseweb="textarea"],
    div[data-baseweb="popover"] {
        background: var(--sp-surface-2) !important;
        border-color: var(--sp-border) !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] input,
    div[data-baseweb="select"] span {
        color: var(--sp-text) !important;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--sp-border);
        border-radius: 10px;
        overflow: hidden;
    }

    /* Alerts / info boxes */
    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    /* Buttons */
    div.stButton > button {
        border-radius: 9px;
        font-weight: 600;
    }

    /* Keep horizontal rules subtle on dark theme */
    hr {
        border-color: var(--sp-border) !important;
    }

    /* ================================================================
       FINAL PROFESSIONAL ERP POLISH — VISUAL ONLY
       Existing functionality and business logic remain unchanged.
       ================================================================ */

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    .block-container {
        width: 100%;
        max-width: 1500px;
        box-sizing: border-box;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Responsive sizing: keep the ERP chrome inside the viewport on
       desktop, tablet and phone screens. */
    .stApp, .stAppViewContainer, .main, section.main, .block-container,
    .sp-topbar {
        box-sizing: border-box;
        max-width: 100%;
    }

    h1, h2, h3, h4 {
        font-family: "Inter", "Segoe UI", sans-serif;
        letter-spacing: -.02em;
    }

    /* Top application bar */
    .sp-topbar {
        width: 100%;
        max-width: 100%;
        min-width: 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: .75rem;
        padding: .65rem .9rem;
        margin: 0 0 1.1rem;
        background: linear-gradient(90deg, #151922 0%, #1a1f29 100%);
        border: 1px solid var(--sp-border);
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,.18);
        overflow: hidden;
    }
    .sp-topbar-left {
        display: flex;
        align-items: center;
        gap: .6rem;
        min-width: 0;
        flex: 1 1 auto;
        overflow: hidden;
    }
    .sp-topbar-brand {
        font-weight: 800;
        letter-spacing: .04em;
        color: var(--sp-text);
        font-size: .82rem;
        flex: 0 1 auto;
        white-space: nowrap;
    }
    .sp-topbar-sep {
        color: var(--sp-border);
    }
    .sp-topbar-module {
        color: var(--sp-muted);
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .sp-online-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: .3rem;
        flex: 0 0 auto;
        max-width: 42%;
        box-sizing: border-box;
        padding: .28rem .55rem;
        border-radius: 999px;
        border: 1px solid rgba(34,197,94,.28);
        background: rgba(34,197,94,.08);
        color: #86efac;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .045em;
        text-transform: uppercase;
        white-space: nowrap;
    }

    @media (max-width: 900px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .sp-topbar {
            padding: .55rem .7rem;
            gap: .5rem;
        }

        .sp-topbar-brand {
            font-size: .74rem;
        }

        .sp-topbar-module {
            font-size: .68rem;
        }

        .sp-online-pill {
            max-width: none;
            font-size: .62rem;
            padding: .25rem .48rem;
        }
    }

    @media (max-width: 560px) {
        .block-container {
            padding-left: .65rem;
            padding-right: .65rem;
        }

        .sp-topbar {
            align-items: stretch;
            flex-wrap: wrap;
            padding: .55rem .65rem;
        }

        .sp-topbar-left {
            flex: 1 1 100%;
            width: 100%;
        }

        .sp-online-pill {
            align-self: flex-start;
            max-width: 100%;
            font-size: .6rem;
        }
    }

    /* Sidebar brand */
    .sp-brand {
        display: flex;
        align-items: center;
        gap: .75rem;
        padding: .35rem 0 .9rem;
        margin-bottom: .55rem;
    }
    .sp-brand-mark {
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        background: linear-gradient(145deg, var(--sp-accent), #ff8a5b);
        color: #111318;
        font-size: .9rem;
        font-weight: 900;
        letter-spacing: -.02em;
        box-shadow: 0 5px 16px rgba(255,107,53,.22);
    }
    .sp-brand-name {
        color: var(--sp-text);
        font-size: .88rem;
        font-weight: 850;
        letter-spacing: .05em;
    }
    .sp-brand-sub {
        color: var(--sp-muted);
        font-size: .62rem;
        font-weight: 700;
        letter-spacing: .12em;
        text-transform: uppercase;
        margin-top: .12rem;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > label {
        color: var(--sp-muted) !important;
        font-size: .72rem !important;
        font-weight: 800 !important;
        letter-spacing: .1em;
        text-transform: uppercase;
        margin-bottom: .4rem;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: .28rem;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: .48rem .65rem;
        border-radius: 9px;
        border: 1px solid transparent;
        transition: all .15s ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background: var(--sp-surface-2);
        border-color: var(--sp-border);
    }

    /* Refined section titles */
    .section-label {
        position: relative;
        padding-left: .7rem;
    }
    .section-label::before {
        content: "";
        position: absolute;
        left: 0;
        top: .1rem;
        bottom: .1rem;
        width: 3px;
        border-radius: 4px;
        background: var(--sp-accent);
    }

    /* ERP panels */
    .erp-panel {
        background: linear-gradient(180deg, rgba(29,34,43,.82), rgba(23,26,33,.94));
        border: 1px solid var(--sp-border);
        border-radius: 12px;
        padding: .95rem 1rem;
        min-height: 104px;
        box-shadow: 0 7px 22px rgba(0,0,0,.12);
    }
    .erp-panel-title {
        color: var(--sp-muted);
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .09em;
        text-transform: uppercase;
        margin-bottom: .35rem;
    }
    .erp-panel-value {
        color: var(--sp-text);
        font-size: 1.18rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .erp-panel-sub {
        color: var(--sp-muted);
        font-size: .78rem;
        margin-top: .25rem;
    }

    /* Management alerts */
    .control-alert {
        border: 1px solid var(--sp-border);
        border-left: 4px solid var(--sp-accent);
        border-radius: 10px;
        padding: .72rem .8rem;
        background: var(--sp-surface);
        min-height: 76px;
    }
    .control-alert.ok { border-left-color: #22c55e; }
    .control-alert.warn { border-left-color: #f59e0b; }
    .control-alert.danger { border-left-color: #ef4444; }
    .control-alert-title {
        color: var(--sp-text);
        font-size: .76rem;
        font-weight: 800;
        letter-spacing: .04em;
        text-transform: uppercase;
    }
    .control-alert-value {
        color: var(--sp-text);
        font-size: 1.1rem;
        font-weight: 850;
        margin-top: .15rem;
    }
    .control-alert-sub {
        color: var(--sp-muted);
        font-size: .73rem;
        margin-top: .08rem;
    }

    /* Consistent buttons */
    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        border-radius: 9px !important;
        font-weight: 700 !important;
        letter-spacing: .01em;
        min-height: 38px;
        border: 1px solid var(--sp-border) !important;
        background: var(--sp-surface-2) !important;
        color: var(--sp-text) !important;
    }
    div.stButton > button:hover,
    div.stDownloadButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        border-color: #3b4554 !important;
        background: #232935 !important;
        color: #ffffff !important;
    }

    /* Tables */
    div[data-testid="stDataFrame"] {
        border-radius: 11px !important;
        border: 1px solid var(--sp-border) !important;
        background: var(--sp-surface) !important;
        box-shadow: 0 6px 20px rgba(0,0,0,.10);
    }

    /* Search inputs */
    div[data-baseweb="input"]:has(input[placeholder*="Search"]),
    div[data-baseweb="input"]:has(input[placeholder*="search"]) {
        border-color: #394352 !important;
        box-shadow: 0 0 0 1px rgba(255,107,53,.04);
    }

    /* Cleaner expanders */
    div[data-testid="stExpander"] {
        box-shadow: 0 6px 20px rgba(0,0,0,.08);
    }

    /* Footer */
    .sp-footer {
        margin-top: 2rem;
        padding: .85rem 0 .3rem;
        border-top: 1px solid var(--sp-border);
        color: #7f8998;
        font-size: .68rem;
        text-align: center;
        letter-spacing: .05em;
    }

</style>
""", unsafe_allow_html=True)

@st.cache_resource
def db():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )

try:
    supabase = db()
except Exception:
    st.error(
        "Supabase is not configured. Add SUPABASE_URL and "
        "SUPABASE_ANON_KEY to Streamlit secrets."
    )
    st.stop()


def fp(*parts):
    raw = "||".join(
        "" if x is None else str(x).strip().upper()
        for x in parts
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def find_account_id(accounts, keywords, account_types=None):
    """Return the first active ledger whose name matches the supplied keywords."""
    keys = [k.lower() for k in keywords]
    allowed = {x.upper() for x in account_types} if account_types else None
    for account in accounts:
        if allowed and str(account.get("account_type", "")).upper() not in allowed:
            continue
        name = str(account.get("account_name") or "").lower()
        if any(k in name for k in keys):
            return account.get("id")
    return None


def cleanup_deletion_audit():
    """Remove audit snapshots after their configured 3-day retention window."""
    try:
        supabase.table("deletion_audit").delete().lt(
            "expires_at", datetime.now(timezone.utc).isoformat()
        ).execute()
    except Exception:
        pass


def audit_delete(table_name, record):
    """Keep a deletion snapshot for at least the configured 3-day window."""
    cleanup_deletion_audit()
    try:
        supabase.table("deletion_audit").insert({
            "table_name": table_name,
            "record_id": str(record.get("id")),
            "deleted_data": record,
            "deleted_by": str(user.id)
        }).execute()
    except Exception:
        # Deletion itself is not blocked if audit logging fails.
        pass


def delete_record(table_name, record_id):
    """Delete one record after taking an audit snapshot."""
    record_response = (
        supabase.table(table_name)
        .select("*")
        .eq("id", record_id)
        .limit(1)
        .execute()
    )
    record = (record_response.data or [None])[0]
    if not record:
        raise Exception("Record not found.")
    audit_delete(table_name, record)
    supabase.table(table_name).delete().eq("id", record_id).execute()


def delete_journal_reference(reference_id):
    """Delete journal lines and their journal header for an operational record."""
    try:
        journals = (
            supabase.table("journal_entries")
            .select("*")
            .eq("reference_id", str(reference_id))
            .execute().data or []
        )
    except Exception:
        journals = []

    for journal in journals:
        journal_id = journal.get("id")
        if journal_id:
            lines = (
                supabase.table("journal_lines")
                .select("*")
                .eq("journal_entry_id", journal_id)
                .execute().data or []
            )
            for line in lines:
                audit_delete("journal_lines", line)
            if lines:
                supabase.table("journal_lines").delete().eq(
                    "journal_entry_id", journal_id
                ).execute()
            audit_delete("journal_entries", journal)
            supabase.table("journal_entries").delete().eq(
                "id", journal_id
            ).execute()


def delete_transaction(table_name, record_id):
    """Delete a test transaction and its directly generated accounting/stock children."""
    record = (
        supabase.table(table_name).select("*").eq("id", record_id).limit(1).execute().data
        or []
    )
    record = record[0] if record else None
    if not record:
        raise Exception("Record not found.")

    if table_name == "accounts_purchases":
        delete_journal_reference(record_id)
        linked = supabase.table("stock_movements").select("*").eq(
            "purchase_id", record_id
        ).execute().data or []
        for movement in linked:
            audit_delete("stock_movements", movement)
        if linked:
            supabase.table("stock_movements").delete().eq(
                "purchase_id", record_id
            ).execute()

    elif table_name == "accounts_expenses":
        delete_journal_reference(record_id)

    elif table_name == "accounts_receipts":
        delete_journal_reference(record_id)

    elif table_name == "accounts_payments":
        delete_journal_reference(record_id)

    elif table_name == "sales_invoices":
        delete_journal_reference(record_id)
        items = supabase.table("sales_invoice_items").select("*").eq(
            "sales_invoice_id", record_id
        ).execute().data or []
        for item in items:
            audit_delete("sales_invoice_items", item)
        if items:
            supabase.table("sales_invoice_items").delete().eq(
                "sales_invoice_id", record_id
            ).execute()
        invoice_no = record.get("invoice_number")
        if invoice_no:
            linked = supabase.table("stock_movements").select("*").eq(
                "direction", "OUT"
            ).eq("reference_no", invoice_no).execute().data or []
            for movement in linked:
                audit_delete("stock_movements", movement)
            for movement in linked:
                supabase.table("stock_movements").delete().eq(
                    "id", movement["id"]
                ).execute()

    elif table_name == "journal_entries":
        lines = supabase.table("journal_lines").select("*").eq(
            "journal_entry_id", record_id
        ).execute().data or []
        for line in lines:
            audit_delete("journal_lines", line)
        if lines:
            supabase.table("journal_lines").delete().eq(
                "journal_entry_id", record_id
            ).execute()

    elif table_name == "stock_movements":
        purchase_id = record.get("purchase_id")
        if purchase_id:
            purchase_rows = supabase.table("accounts_purchases").select("*").eq(
                "id", purchase_id
            ).execute().data or []
            if purchase_rows:
                delete_transaction("accounts_purchases", purchase_id)
        elif record.get("direction") == "OUT" and record.get("reference_no"):
            # Sales-generated dispatches are identified by their invoice reference.
            sales_rows = supabase.table("sales_invoices").select("*").eq(
                "invoice_number", record.get("reference_no")
            ).execute().data or []
            for sale in sales_rows:
                delete_transaction("sales_invoices", sale["id"])
                # The stock movement will be removed by the sale deletion.
                return

    audit_delete(table_name, record)
    supabase.table(table_name).delete().eq("id", record_id).execute()


def render_delete_control(table_name, records, label_builder, key, transaction=False):
    """Reusable test-data deletion control with a 3-day deletion audit."""
    valid = [r for r in records if r.get("id")]
    if not valid:
        return
    with st.expander("🗑️ Delete test data", expanded=False):
        st.caption("Deleted records are retained in the deletion audit for 3 days.")
        options = {label_builder(r): r["id"] for r in valid}
        selected_label = st.selectbox("Select record", list(options.keys()), key=key)
        confirm = st.checkbox("I confirm this is test data and should be deleted.", key=f"{key}_confirm")
        if st.button("Delete selected record", type="secondary", key=f"{key}_button"):
            if not confirm:
                st.warning("Tick the confirmation box before deleting.")
            else:
                try:
                    if transaction:
                        delete_transaction(table_name, options[selected_label])
                    else:
                        delete_record(table_name, options[selected_label])
                    st.success("Record deleted. The deletion snapshot is retained for 3 days.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Unable to delete record: {e}")


def stock_balance(item_id):
    rows = (
        supabase.table("stock_movements")
        .select("direction,quantity,weight_kg")
        .eq("item_id", item_id)
        .execute()
        .data
    )

    incoming_qty = sum(
        float(x["quantity"]) for x in rows
        if x["direction"] == "IN"
    )
    outgoing_qty = sum(
        float(x["quantity"]) for x in rows
        if x["direction"] == "OUT"
    )

    incoming_weight = sum(
        float(x["weight_kg"] or 0) for x in rows
        if x["direction"] == "IN"
    )
    outgoing_weight = sum(
        float(x["weight_kg"] or 0) for x in rows
        if x["direction"] == "OUT"
    )

    return (
        incoming_qty,
        outgoing_qty,
        incoming_qty - outgoing_qty,
        incoming_weight,
        outgoing_weight,
        incoming_weight - outgoing_weight
    )


# ================================================================
# JOURNAL POSTING ENGINE
# ================================================================

def create_journal_entry(
    entry_date,
    voucher_type,
    reference_type,
    reference_id,
    narration,
    lines,
    entered_by
):

    total_debit = round(
        sum(float(line.get("debit", 0) or 0) for line in lines),
        2
    )

    total_credit = round(
        sum(float(line.get("credit", 0) or 0) for line in lines),
        2
    )

    if total_debit <= 0:

        raise Exception(
            "Journal debit amount must be greater than zero."
        )

    if abs(total_debit - total_credit) >= 0.01:

        raise Exception(
            "Journal entry is not balanced."
        )

    journal_number = (
        "JV-"
        + entry_date.strftime("%Y%m%d")
        + "-"
        + uuid.uuid4().hex[:6].upper()
    )

    journal_header = {

        "entry_no":
            journal_number,

        "entry_date":
            entry_date.isoformat(),

        "voucher_type":
            voucher_type,

        "reference_type":
            reference_type,

        "reference_id":
            reference_id,

        "narration":
            narration,

        "entered_by":
            str(entered_by)
    }

    journal_response = (
        supabase
        .table("journal_entries")
        .insert(journal_header)
        .execute()
    )

    if not journal_response.data:

        raise Exception(
            "Journal entry header could not be created."
        )

    journal_entry_id = (
        journal_response.data[0]["id"]
    )

    journal_lines = []

    for line in lines:

        journal_lines.append({

            "journal_entry_id":
                journal_entry_id,

            "account_id":
                line["account_id"],

            "party_id":
                line.get("party_id"),

            "debit":
                float(line.get("debit", 0) or 0),

            "credit":
                float(line.get("credit", 0) or 0),

            "narration":
                line.get("narration") or narration
        })

    (
        supabase
        .table("journal_lines")
        .insert(journal_lines)
        .execute()
    )

    return journal_number

# ================================================================
# ADDED: EXCEL EXPORT + SALES INVOICE PDF
# ================================================================

COMPANY_DETAILS = {
    "name": "S.P. Enterprise",
    "gstin": "19AAOPH1340Q2Z8",
    "address": "Jalan Industrial Complex, Gate 1, Lane 4, Biprannapara, Howrah-711411",
    "email": "spenterprise97@gmail.com",
    "bank": "Indian Overseas Bank",
    "account_name": "S.P. Enterprise",
    "account_number": "015102000003971",
    "ifsc": "IOBA0000151",
    "branch": "Howrah (0151)"
}

def rows_to_excel_bytes(rows, sheet_name="Export"):
    wb = Workbook()
    ws = wb.active
    ws.title = str(sheet_name or "Export")[:31]

    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        headers = list(rows[0].keys())
        for col, header in enumerate(headers, 1):
            c = ws.cell(1, col, str(header))
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="172033")
            c.alignment = Alignment(horizontal="center", vertical="center")
        for r, row in enumerate(rows, 2):
            for c, header in enumerate(headers, 1):
                value = row.get(header)
                if isinstance(value, (dict, list)):
                    value = str(value)
                ws.cell(r, c, value)
    elif isinstance(rows, list) and rows:
        for r, row in enumerate(rows, 1):
            if isinstance(row, (list, tuple)):
                for c, value in enumerate(row, 1):
                    ws.cell(r, c, value)
            else:
                ws.cell(r, 1, row)
    else:
        ws.cell(1, 1, "No records available")

    thin = Side(style="thin", color="D9E2EC")
    for row in ws.iter_rows():
        for cell in row:
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col_cells in ws.columns:
        width = 12
        for cell in col_cells:
            if cell.value is not None:
                width = min(max(width, len(str(cell.value)) + 2), 40)
        ws.column_dimensions[col_cells[0].column_letter].width = width

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

def add_excel_download(rows, filename, label, key, sheet_name="Export"):
    st.download_button(
        label=label,
        data=rows_to_excel_bytes(rows, sheet_name),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key
    )

def invoice_to_pdf_bytes(invoice, item_rows):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=14*mm, leftMargin=14*mm,
        topMargin=14*mm, bottomMargin=14*mm
    )
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 18
    title_style.leading = 22
    normal = styles["Normal"]
    normal.fontName = "Helvetica"
    normal.fontSize = 9
    normal.leading = 12

    story = [
        Paragraph(COMPANY_DETAILS["name"], title_style),
        Paragraph(f'<b>GSTIN:</b> {COMPANY_DETAILS["gstin"]}', normal),
        Paragraph(COMPANY_DETAILS["address"], normal),
        Paragraph(f'<b>Email:</b> {COMPANY_DETAILS["email"]}', normal),
        Spacer(1, 6*mm)
    ]

    invoice_info = [
        [Paragraph("<b>Invoice No.</b>", normal), str(invoice.get("invoice_number") or ""),
         Paragraph("<b>Invoice Date</b>", normal), str(invoice.get("invoice_date") or "")],
        [Paragraph("<b>Invoice Type</b>", normal), str(invoice.get("invoice_type") or ""),
         Paragraph("<b>Due Date</b>", normal), str(invoice.get("due_date") or "")],
        [Paragraph("<b>Bill To</b>", normal), str(invoice.get("customer_name") or ""),
         Paragraph("<b>Payment Status</b>", normal), str(invoice.get("payment_status") or "")]
    ]
    info = Table(invoice_info, colWidths=[28*mm, 65*mm, 30*mm, 52*mm])
    info.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#C9D2DC")),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#EEF2F7")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#EEF2F7")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5)
    ]))
    story += [info, Spacer(1, 6*mm)]

    data = [["#", "Description", "Qty", "Unit", "Rate", "Taxable", "GST", "Amount"]]
    for i, item in enumerate(item_rows or [], 1):
        gst = sum(float(item.get(k) or 0) for k in ("cgst_amount", "sgst_amount", "igst_amount"))
        data.append([
            str(i), str(item.get("description") or ""),
            f'{float(item.get("quantity") or 0):g}', str(item.get("unit") or ""),
            f'₹{float(item.get("rate") or 0):,.2f}',
            f'₹{float(item.get("taxable_amount") or 0):,.2f}',
            f'₹{gst:,.2f}', f'₹{float(item.get("line_total") or 0):,.2f}'
        ])
    if len(data) == 1:
        subtotal = float(invoice.get("subtotal") or 0)
        total = float(invoice.get("total_amount") or 0)
        data.append(["1", "Sales Item", "", "", "", f'₹{subtotal:,.2f}', f'₹{total-subtotal:,.2f}', f'₹{total:,.2f}'])

    item_table = Table(data, repeatRows=1, colWidths=[9*mm,43*mm,15*mm,15*mm,22*mm,25*mm,22*mm,25*mm])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#172033")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#C9D2DC")),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FC")])
    ]))
    story += [item_table, Spacer(1, 5*mm)]

    subtotal = float(invoice.get("subtotal") or 0)
    discount = float(invoice.get("discount_amount") or 0)
    cgst = float(invoice.get("cgst_amount") or 0)
    sgst = float(invoice.get("sgst_amount") or 0)
    igst = float(invoice.get("igst_amount") or 0)
    total = float(invoice.get("total_amount") or 0)
    received = float(invoice.get("amount_received") or 0)
    balance = float(invoice.get("balance_amount") or 0)
    totals = [
        ["Subtotal", f'₹{subtotal:,.2f}'], ["Discount", f'₹{discount:,.2f}'],
        ["CGST", f'₹{cgst:,.2f}'], ["SGST", f'₹{sgst:,.2f}'],
        ["IGST", f'₹{igst:,.2f}'], ["Invoice Total", f'₹{total:,.2f}'],
        ["Amount Received", f'₹{received:,.2f}'], ["Balance Due", f'₹{balance:,.2f}']
    ]
    totals_table = Table(totals, colWidths=[42*mm,38*mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#C9D2DC")),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("FONTNAME", (0,5), (-1,5), "Helvetica-Bold"),
        ("FONTNAME", (0,7), (-1,7), "Helvetica-Bold"),
        ("BACKGROUND", (0,5), (-1,5), colors.HexColor("#EEF2F7")),
        ("BACKGROUND", (0,7), (-1,7), colors.HexColor("#FFF4E5")),
        ("FONTSIZE", (0,0), (-1,-1), 9)
    ]))
    story += [totals_table, Spacer(1, 7*mm),
        Paragraph(
            f'<b>Bank Details</b><br/>Bank: {COMPANY_DETAILS["bank"]}<br/>'
            f'Account Name: {COMPANY_DETAILS["account_name"]}<br/>'
            f'A/C No.: {COMPANY_DETAILS["account_number"]}<br/>'
            f'IFSC: {COMPANY_DETAILS["ifsc"]}<br/>'
            f'Branch: {COMPANY_DETAILS["branch"]}', normal),
        Spacer(1, 10*mm), Paragraph("Authorised Signatory", normal)]

    pdf.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ================================================================
# NEW FEATURE HELPERS - ADDITIVE ONLY
# ================================================================

def has_feature(feature_name):
    """Return True only when the current authenticated user has an active feature grant."""
    try:
        rows = (
            supabase.table("feature_access")
            .select("id")
            .eq("user_id", str(user.id))
            .eq("feature", feature_name)
            .eq("active", True)
            .limit(1)
            .execute()
            .data
            or []
        )
        return bool(rows)
    except Exception:
        return False


def filter_display_rows(rows, query, fields=None):
    """Case-insensitive local filter used by the read-only registers."""
    if not query or not str(query).strip():
        return rows
    q = str(query).strip().lower()
    filtered = []
    for row in rows or []:
        if fields:
            values = [row.get(f) for f in fields]
        elif isinstance(row, dict):
            values = list(row.values())
        else:
            values = [row]
        if any(q in str(v or "").lower() for v in values):
            filtered.append(row)
    return filtered


def refresh_order_status(order_id):
    """Recalculate a Purchase/Sales Order's fulfillment status from linked stock movements."""
    if not order_id:
        return
    try:
        order_rows = (
            supabase.table("orders")
            .select("*")
            .eq("id", order_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not order_rows:
            return
        order = order_rows[0]
        item_rows = (
            supabase.table("order_items")
            .select("quantity,weight_kg")
            .eq("order_id", order_id)
            .execute()
            .data
            or []
        )
        ordered_qty = sum(float(x.get("quantity") or 0) for x in item_rows)
        ordered_weight = sum(float(x.get("weight_kg") or 0) for x in item_rows)
        direction = "IN" if order.get("order_type") == "PURCHASE" else "OUT"
        movement_rows = (
            supabase.table("stock_movements")
            .select("quantity,weight_kg")
            .eq("order_id", order_id)
            .eq("direction", direction)
            .execute()
            .data
            or []
        )
        fulfilled_qty = sum(float(x.get("quantity") or 0) for x in movement_rows)
        fulfilled_weight = sum(float(x.get("weight_kg") or 0) for x in movement_rows)
        if order.get("status") == "CANCELLED":
            return
        qty_complete = ordered_qty <= 0 or fulfilled_qty + 0.0001 >= ordered_qty
        weight_complete = ordered_weight <= 0 or fulfilled_weight + 0.0001 >= ordered_weight
        if fulfilled_qty <= 0 and fulfilled_weight <= 0:
            new_status = "OPEN"
        elif qty_complete and weight_complete:
            new_status = "COMPLETED"
        else:
            new_status = "PARTIAL"
        supabase.table("orders").update({"status": new_status}).eq("id", order_id).execute()
    except Exception:
        pass


def order_summary_rows(order_type=None, query="", status_filter="ALL"):
    """Build human-readable order register rows with dynamically calculated fulfillment."""
    try:
        q = supabase.table("orders").select("*").order("order_date", desc=True).limit(1000)
        if order_type:
            q = q.eq("order_type", order_type)
        if status_filter != "ALL":
            q = q.eq("status", status_filter)
        orders = q.execute().data or []
    except Exception:
        orders = []

    party_rows = {}
    try:
        parties_local = supabase.table("business_parties").select("id,name,party_type").execute().data or []
        party_rows = {str(x.get("id")): x for x in parties_local}
    except Exception:
        pass

    try:
        item_rows = supabase.table("order_items").select("*").execute().data or []
    except Exception:
        item_rows = []
    items_by_order = {}
    for item in item_rows:
        items_by_order.setdefault(str(item.get("order_id")), []).append(item)

    try:
        movements = supabase.table("stock_movements").select("order_id,quantity,weight_kg,direction").not_.is_("order_id", "null").execute().data or []
    except Exception:
        movements = []
    movement_by_order = {}
    for m in movements:
        oid = str(m.get("order_id"))
        movement_by_order.setdefault(oid, []).append(m)

    output = []
    for order in orders:
        oid = str(order.get("id"))
        items = items_by_order.get(oid, [])
        ordered_qty = sum(float(x.get("quantity") or 0) for x in items)
        ordered_weight = sum(float(x.get("weight_kg") or 0) for x in items)
        direction = "IN" if order.get("order_type") == "PURCHASE" else "OUT"
        linked = [m for m in movement_by_order.get(oid, []) if m.get("direction") == direction]
        fulfilled_qty = sum(float(x.get("quantity") or 0) for x in linked)
        fulfilled_weight = sum(float(x.get("weight_kg") or 0) for x in linked)
        pending_qty = max(ordered_qty - fulfilled_qty, 0)
        pending_weight = max(ordered_weight - fulfilled_weight, 0)
        party = party_rows.get(str(order.get("party_id")), {})
        item_names = ", ".join(dict.fromkeys(str(x.get("description") or "") for x in items if x.get("description")))
        row = {
            "Order No.": order.get("order_number"),
            "Type": order.get("order_type"),
            "Date": order.get("order_date"),
            "Party": party.get("name") or "",
            "Reference": order.get("reference_no"),
            "Item(s)": item_names,
            "Ordered Qty": ordered_qty,
            "Fulfilled Qty": fulfilled_qty,
            "Pending Qty": pending_qty,
            "Ordered Weight KG": ordered_weight,
            "Fulfilled Weight KG": fulfilled_weight,
            "Pending Weight KG": pending_weight,
            "Status": order.get("status"),
            "Expected / Required": order.get("expected_date") or order.get("required_date"),
            "Notes": order.get("notes")
        }
        if query:
            searchable = " ".join(str(v or "") for v in row.values()).lower()
            if str(query).strip().lower() not in searchable:
                continue
        output.append(row)
    return output, orders


def jobwork_summary(jobwork_id):
    """Return calculated input/output/waste values for a jobwork record."""
    try:
        record_rows = supabase.table("jobwork_records").select("*").eq("id", jobwork_id).limit(1).execute().data or []
        record = record_rows[0] if record_rows else {}
    except Exception:
        record = {}
    try:
        movements = (
            supabase.table("stock_movements")
            .select("direction,movement_type,quantity,weight_kg,item_id,reference_no,stock_items(name,unit)")
            .eq("jobwork_id", jobwork_id)
            .order("movement_date")
            .execute()
            .data
            or []
        )
    except Exception:
        movements = []
    sent = [m for m in movements if m.get("movement_type") == "JOBWORK_OUT"]
    returned = [m for m in movements if m.get("movement_type") == "JOBWORK_IN"]
    sent_qty = sum(float(x.get("quantity") or 0) for x in sent)
    sent_weight = sum(float(x.get("weight_kg") or 0) for x in sent)
    returned_qty = sum(float(x.get("quantity") or 0) for x in returned)
    returned_weight = sum(float(x.get("weight_kg") or 0) for x in returned)
    waste_qty = float(record.get("waste_quantity") or 0)
    waste_weight = float(record.get("waste_weight_kg") or 0)
    pending_qty = max(sent_qty - returned_qty - waste_qty, 0)
    pending_weight = max(sent_weight - returned_weight - waste_weight, 0)
    return {
        "record": record,
        "movements": movements,
        "sent_qty": sent_qty,
        "sent_weight": sent_weight,
        "returned_qty": returned_qty,
        "returned_weight": returned_weight,
        "waste_qty": waste_qty,
        "waste_weight": waste_weight,
        "pending_qty": pending_qty,
        "pending_weight": pending_weight,
    }


def refresh_jobwork_status(jobwork_id):
    try:
        summary = jobwork_summary(jobwork_id)
        if not summary["record"] or summary["record"].get("status") == "CANCELLED":
            return
        if summary["returned_weight"] <= 0 and summary["returned_qty"] <= 0:
            new_status = "SENT"
        elif summary["pending_weight"] <= 0.01 and (summary["sent_weight"] > 0 or summary["pending_qty"] <= 0.01):
            new_status = "COMPLETED"
        else:
            new_status = "PARTIAL"
        supabase.table("jobwork_records").update({"status": new_status}).eq("id", jobwork_id).execute()
    except Exception:
        pass


def global_search(query):
    """Read-only cross-register search for the Dashboard."""
    q = str(query or "").strip().lower()
    if not q:
        return {}
    results = {}

    def match_rows(rows, key_fields=None):
        matched = []
        for row in rows or []:
            if key_fields:
                vals = [row.get(k) for k in key_fields]
            else:
                vals = list(row.values()) if isinstance(row, dict) else [row]
            if any(q in str(v or "").lower() for v in vals):
                matched.append(row)
        return matched

    try:
        items_local = supabase.table("stock_items").select("id,name,unit,minimum_level,active").eq("active", True).execute().data or []
        matched = match_rows(items_local, ["name", "unit"])
        if matched:
            results["Stock Items"] = matched
    except Exception:
        pass

    try:
        parties_local = supabase.table("business_parties").select("id,name,party_type,phone,gstin").execute().data or []
        matched = match_rows(parties_local, ["name", "party_type", "phone", "gstin"])
        if matched:
            results["Parties"] = matched
    except Exception:
        pass

    try:
        movements_local = (
            supabase.table("stock_movements")
            .select("movement_date,direction,movement_type,reference_no,quantity,bags,weight_kg,rate_per_kg,billing_amount,vehicle_no,handled_by,notes,stock_items(name,unit),business_parties(name)")
            .order("movement_date", desc=True).limit(1000).execute().data or []
        )
        movement_rows = []
        for r in movements_local:
            item = r.get("stock_items") or {}
            party = r.get("business_parties") or {}
            movement_rows.append({
                "Date": r.get("movement_date"),
                "Movement": r.get("movement_type") or r.get("direction"),
                "Direction": r.get("direction"),
                "Party": party.get("name"),
                "Challan / Reference": r.get("reference_no"),
                "Item": item.get("name"),
                "Qty": r.get("quantity"),
                "Weight KG": r.get("weight_kg"),
                "Billing ₹": r.get("billing_amount"),
                "Vehicle": r.get("vehicle_no"),
                "Handled By": r.get("handled_by"),
                "Notes": r.get("notes")
            })
        matched = match_rows(movement_rows)
        if matched:
            results["Stock Movements"] = matched[:100]
    except Exception:
        pass

    try:
        orders_data, _ = order_summary_rows(query=q)
        if orders_data:
            results["Orders"] = orders_data[:100]
    except Exception:
        pass

    try:
        sales_local = supabase.table("sales_invoices").select("invoice_number,invoice_date,customer_name,total_amount,amount_received,balance_amount,payment_status,due_date").order("invoice_date", desc=True).limit(1000).execute().data or []
        matched = match_rows(sales_local)
        if matched:
            results["Sales Invoices"] = matched[:100]
    except Exception:
        pass

    try:
        purchases_local = supabase.table("accounts_purchases").select("bill_no,bill_date,supplier,gstin,taxable_value,gst_amount,bill_total,reference_no,party_id").order("bill_date", desc=True).limit(1000).execute().data or []
        matched = match_rows(purchases_local)
        if matched:
            results["Purchases"] = matched[:100]
    except Exception:
        pass

    for title, table_name, date_field, fields in [
        ("Expenses", "accounts_expenses", "expense_date", ["expense_date","description","reference_no","total_amount"]),
        ("Receipts", "accounts_receipts", "receipt_date", ["receipt_no","receipt_date","reference_no","narration","amount"]),
        ("Payments", "accounts_payments", "payment_date", ["payment_no","payment_date","reference_no","narration","amount"]),
        ("Documents", "business_documents", "expiry_date", ["document_type","document_name","document_number","reference_no","status","notes"]),
        ("Journal Entries", "journal_entries", "entry_date", ["entry_no","entry_date","voucher_type","reference_type","reference_id","narration"]),
    ]:
        try:
            data = supabase.table(table_name).select("*").order(date_field, desc=True).limit(1000).execute().data or []
            matched = match_rows(data, fields)
            if matched:
                results[title] = matched[:100]
        except Exception:
            pass

    try:
        jobwork_rows = supabase.table("jobwork_records").select("*").order("jobwork_date", desc=True).limit(500).execute().data or []
        jobwork_movements = (
            supabase.table("stock_movements")
            .select("jobwork_id,movement_type,quantity,weight_kg,stock_items(name,unit)")
            .not_.is_("jobwork_id", "null")
            .execute().data or []
        )
        parties_local = supabase.table("business_parties").select("id,name").execute().data or []
        party_map = {str(x.get("id")): x.get("name") for x in parties_local}
        agg = {}
        for m in jobwork_movements:
            jid = str(m.get("jobwork_id"))
            a = agg.setdefault(jid, {"sent_weight":0, "returned_weight":0, "items_sent":[], "items_returned":[]})
            if m.get("movement_type") == "JOBWORK_OUT":
                a["sent_weight"] += float(m.get("weight_kg") or 0)
                name = (m.get("stock_items") or {}).get("name")
                if name: a["items_sent"].append(name)
            elif m.get("movement_type") == "JOBWORK_IN":
                a["returned_weight"] += float(m.get("weight_kg") or 0)
                name = (m.get("stock_items") or {}).get("name")
                if name: a["items_returned"].append(name)
        display = []
        for j in jobwork_rows:
            a = agg.get(str(j.get("id")), {})
            waste = float(j.get("waste_weight_kg") or 0)
            sent = float(a.get("sent_weight") or 0)
            returned = float(a.get("returned_weight") or 0)
            pending = max(sent - returned - waste, 0)
            display.append({
                "Challan": j.get("challan_no"),
                "Date": j.get("jobwork_date"),
                "Jobwork Party": party_map.get(str(j.get("party_id")), ""),
                "Material Sent": ", ".join(dict.fromkeys(a.get("items_sent", []))),
                "Material Returned": ", ".join(dict.fromkeys(a.get("items_returned", []))),
                "Sent KG": sent,
                "Returned KG": returned,
                "Waste KG": waste,
                "Pending KG": pending,
                "Status": j.get("status"),
                "Notes": j.get("notes")
            })
        matched = match_rows(display)
        if matched:
            results["JOBWORK"] = matched[:100]
    except Exception:
        pass

    return results


def render_recent_frame(title, rows, query_key, empty_text="No records yet."):
    st.markdown(f"### {title}")
    q = st.text_input(f"🔎 Search {title}", key=query_key, placeholder="Search this list...")
    filtered = filter_display_rows(rows, q)
    if filtered:
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info(empty_text)
    return filtered


# ---------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------

if "user" not in st.session_state:
    st.title("S.P. Enterprise")
    st.subheader("Cloud Accounts & Stock Control")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign in", type="primary"):
        try:
            r = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state.user = r.user
            st.rerun()
        except Exception:
            st.error("Login failed. Check the credentials.")

    st.stop()

user = st.session_state.user
cleanup_deletion_audit()


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div class="sp-brand">
            <div class="sp-brand-mark">SP</div>
            <div>
                <div class="sp-brand-name">S.P. ENTERPRISE</div>
                <div class="sp-brand-sub">Control System</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.caption(user.email)

    page = st.radio(
        "Module",
        ["Dashboard", "Stock Control", "Orders", "JOBWORK", "Accounts", "Documents"]
    )

    st.markdown(
        '<div style="height:.35rem;border-top:1px solid var(--sp-border);margin:.55rem 0 .65rem;"></div>',
        unsafe_allow_html=True
    )
    st.caption("SECURE BUSINESS WORKSPACE")

    if st.button("Sign out", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()


st.markdown(
    f"""
    <div class="sp-topbar">
        <div class="sp-topbar-left">
            <span class="sp-topbar-brand">S.P. ENTERPRISE</span>
            <span class="sp-topbar-sep">/</span>
            <span class="sp-topbar-module">{page}</span>
        </div>
        <div class="sp-online-pill">● System Online</div>
    </div>
    """,
    unsafe_allow_html=True
)


# ---------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------

if page == "Dashboard":

    st.markdown('<div class="module-title">Control Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="module-subtitle">Operational and financial overview for S.P. Enterprise</div>', unsafe_allow_html=True)

    try:
        items = (supabase.table("stock_items").select("*").eq("active", True).execute().data or [])
        parties = (supabase.table("business_parties").select("*").eq("active", True).execute().data or [])
        movements = (supabase.table("stock_movements").select("id,direction,billing_amount").execute().data or [])
        sales = (supabase.table("sales_invoices").select("total_amount,balance_amount,payment_status").execute().data or [])
        purchases = (supabase.table("accounts_purchases").select("bill_total").execute().data or [])
        expenses = (supabase.table("accounts_expenses").select("total_amount").execute().data or [])
    except Exception as e:
        st.error("Unable to load dashboard data.")
        st.code(str(e))
        items, parties, movements, sales, purchases, expenses = [], [], [], [], [], []

    total_sales = sum(float(x.get("total_amount") or 0) for x in sales if x.get("payment_status") != "CANCELLED")
    receivables = sum(float(x.get("balance_amount") or 0) for x in sales if x.get("payment_status") != "CANCELLED")
    total_purchases = sum(float(x.get("bill_total") or 0) for x in purchases)
    total_expenses = sum(float(x.get("total_amount") or 0) for x in expenses)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Active Stock Items", len(items))
    k2.metric("Active Parties", len(parties))
    k3.metric("Sales", f"₹{total_sales:,.2f}")
    k4.metric("Receivables", f"₹{receivables:,.2f}")

    st.markdown('<div class="section-label">System status</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown('<div class="status-card"><h4>📦 Stock Control</h4><p>Receiving, dispatch, current balances and movement history are connected.</p></div>', unsafe_allow_html=True)
    with s2:
        st.markdown('<div class="status-card"><h4>💰 Accounting</h4><p>Sales, purchases, expenses, receipts, payments and journals share the accounting database.</p></div>', unsafe_allow_html=True)
    with s3:
        st.markdown('<div class="status-card"><h4>📁 Documents</h4><p>Central register for statutory, banking, property and operational documents.</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Financial snapshot</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    f1.metric("Purchases", f"₹{total_purchases:,.2f}")
    f2.metric("Expenses", f"₹{total_expenses:,.2f}")
    f3.metric("Stock Movements", len(movements))

    st.info("Integrated workflow: Stock Receiving → Purchase Confirmation → Payable → Payment; Sales → Stock Dispatch → Receivable → Receipt; Expenses → Journal; all feeding the Chart of Accounts.")

    # ================================================================
    # MANAGEMENT CONTROL ALERTS — READ ONLY
    # ================================================================
    st.markdown('<div class="section-label">Management Control Alerts</div>', unsafe_allow_html=True)

    low_stock_count = 0
    pending_purchase_orders = 0
    pending_sales_orders = 0
    pending_jobwork = 0
    overdue_receivables = 0

    try:
        for _item in items[:500]:
            _bal = stock_balance(_item["id"])
            if _bal[2] <= float(_item.get("minimum_level") or 0):
                low_stock_count += 1
    except Exception:
        low_stock_count = 0

    try:
        _order_rows = (
            supabase.table("orders")
            .select("order_type,status")
            .in_("status", ["OPEN", "PARTIAL"])
            .execute()
            .data or []
        )
        pending_purchase_orders = sum(1 for _x in _order_rows if _x.get("order_type") == "PURCHASE")
        pending_sales_orders = sum(1 for _x in _order_rows if _x.get("order_type") == "SALES")
    except Exception:
        pass

    try:
        _jobwork_rows = (
            supabase.table("jobwork_records")
            .select("status")
            .neq("status", "COMPLETED")
            .neq("status", "CANCELLED")
            .execute()
            .data or []
        )
        pending_jobwork = len(_jobwork_rows)
    except Exception:
        pass

    try:
        _today = date.today()
        overdue_receivables = sum(
            1
            for _x in sales
            if _x.get("payment_status") not in {"PAID", "CANCELLED"}
            and _x.get("due_date")
            and str(_x.get("due_date")) < _today.isoformat()
            and float(_x.get("balance_amount") or 0) > 0
        )
    except Exception:
        overdue_receivables = 0

    ca1, ca2, ca3, ca4, ca5 = st.columns(5)

    with ca1:
        _cls = "warn" if low_stock_count else "ok"
        st.markdown(
            f'<div class="control-alert {_cls}">'
            f'<div class="control-alert-title">Low Stock</div>'
            f'<div class="control-alert-value">{low_stock_count}</div>'
            f'<div class="control-alert-sub">Items at or below minimum level</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with ca2:
        _cls = "warn" if pending_purchase_orders else "ok"
        st.markdown(
            f'<div class="control-alert {_cls}">'
            f'<div class="control-alert-title">Purchase Orders</div>'
            f'<div class="control-alert-value">{pending_purchase_orders}</div>'
            f'<div class="control-alert-sub">Open / partially received</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with ca3:
        _cls = "warn" if pending_sales_orders else "ok"
        st.markdown(
            f'<div class="control-alert {_cls}">'
            f'<div class="control-alert-title">Sales Orders</div>'
            f'<div class="control-alert-value">{pending_sales_orders}</div>'
            f'<div class="control-alert-sub">Open / partially dispatched</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with ca4:
        _cls = "warn" if pending_jobwork else "ok"
        st.markdown(
            f'<div class="control-alert {_cls}">'
            f'<div class="control-alert-title">JOBWORK</div>'
            f'<div class="control-alert-value">{pending_jobwork}</div>'
            f'<div class="control-alert-sub">Challans not yet completed</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with ca5:
        _cls = "danger" if overdue_receivables else "ok"
        st.markdown(
            f'<div class="control-alert {_cls}">'
            f'<div class="control-alert-title">Overdue Receivables</div>'
            f'<div class="control-alert-value">{overdue_receivables}</div>'
            f'<div class="control-alert-sub">Invoices past due date</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ================================================================
    # ENTERPRISE-WIDE SEARCH
    # ================================================================
    st.markdown('<div class="section-label">Enterprise Search</div>', unsafe_allow_html=True)
    dashboard_search = st.text_input(
        "🔎 Search across the Enterprise",
        key="dashboard_global_search",
        placeholder="Item, party, challan, invoice, order no., Jobwork challan, reference..."
    )
    if dashboard_search.strip():
        search_results = global_search(dashboard_search)
        if search_results:
            st.success(f"Search results for: {dashboard_search.strip()}")
            for section_name, section_rows in search_results.items():
                st.markdown(f"**{section_name}**")
                st.dataframe(section_rows, use_container_width=True, hide_index=True)
        else:
            st.warning("No matching records found.")

    # ================================================================
    # MANAGEMENT SNAPSHOT
    # ================================================================
    st.markdown('<div class="section-label">Enterprise Activity Snapshot</div>', unsafe_allow_html=True)
    dash_tab1, dash_tab2, dash_tab3, dash_tab4, dash_tab5 = st.tabs([
        "📦 Stock", "📋 Orders", "💰 Accounts", "🏭 JOBWORK", "📁 Documents"
    ])

    with dash_tab1:
        try:
            recent_stock = (
                supabase.table("stock_movements")
                .select("movement_date,direction,movement_type,reference_no,quantity,bags,weight_kg,rate_per_kg,billing_amount,stock_items(name,unit),business_parties(name)")
                .order("movement_date", desc=True).limit(25).execute().data or []
            )
            stock_snapshot = []
            for r in recent_stock:
                item = r.get("stock_items") or {}
                party = r.get("business_parties") or {}
                stock_snapshot.append({
                    "Date": r.get("movement_date"),
                    "Movement": r.get("movement_type") or r.get("direction"),
                    "Direction": r.get("direction"),
                    "Party": party.get("name"),
                    "Challan": r.get("reference_no"),
                    "Item": item.get("name"),
                    "Qty": r.get("quantity"),
                    "Weight KG": r.get("weight_kg"),
                    "Value": r.get("billing_amount")
                })
            render_recent_frame("Recent Stock Movements", stock_snapshot, "dashboard_recent_stock_search")
        except Exception as e:
            st.error(f"Unable to load stock snapshot: {e}")

        try:
            current_stock_snapshot = []
            for x in items[:500]:
                _, _, bal_qty, _, _, bal_weight = stock_balance(x["id"])
                current_stock_snapshot.append({
                    "Item": x.get("name"),
                    "Unit": x.get("unit"),
                    "Current Qty": bal_qty,
                    "Current Weight KG": bal_weight,
                    "Minimum Level": x.get("minimum_level"),
                    "Status": "⚠️ LOW" if bal_qty <= float(x.get("minimum_level") or 0) else "OK"
                })
            render_recent_frame("Current Stock", current_stock_snapshot, "dashboard_current_stock_search")
        except Exception as e:
            st.error(f"Unable to load current stock snapshot: {e}")

    with dash_tab2:
        try:
            purchase_orders, _ = order_summary_rows(order_type="PURCHASE")
            render_recent_frame("Purchase Orders", purchase_orders[:25], "dashboard_purchase_orders_search")
        except Exception as e:
            st.error(f"Unable to load purchase orders: {e}")
        try:
            sales_orders, _ = order_summary_rows(order_type="SALES")
            render_recent_frame("Sales Orders", sales_orders[:25], "dashboard_sales_orders_search")
        except Exception as e:
            st.error(f"Unable to load sales orders: {e}")

    with dash_tab3:
        try:
            sales_snapshot = []
            for x in sales[:25]:
                sales_snapshot.append({
                    "Invoice": x.get("invoice_number"),
                    "Date": x.get("invoice_date"),
                    "Customer": x.get("customer_name"),
                    "Total": x.get("total_amount"),
                    "Received": x.get("amount_received"),
                    "Balance": x.get("balance_amount"),
                    "Status": x.get("payment_status")
                })
            render_recent_frame("Recent Sales", sales_snapshot, "dashboard_sales_search")
        except Exception as e:
            st.error(f"Unable to load sales snapshot: {e}")
        try:
            purchase_snapshot = supabase.table("accounts_purchases").select("bill_no,bill_date,supplier,bill_total,gst_amount").order("bill_date", desc=True).limit(25).execute().data or []
            render_recent_frame("Recent Purchases", purchase_snapshot, "dashboard_purchases_search")
        except Exception as e:
            st.error(f"Unable to load purchase snapshot: {e}")
        try:
            expense_snapshot = supabase.table("accounts_expenses").select("expense_date,description,total_amount,payment_mode,reference_no").order("expense_date", desc=True).limit(25).execute().data or []
            render_recent_frame("Recent Expenses", expense_snapshot, "dashboard_expenses_search")
        except Exception as e:
            st.error(f"Unable to load expense snapshot: {e}")
        try:
            receipt_snapshot = supabase.table("accounts_receipts").select("receipt_no,receipt_date,party_id,amount,payment_mode,reference_no,narration").order("receipt_date", desc=True).limit(25).execute().data or []
            render_recent_frame("Recent Receipts", receipt_snapshot, "dashboard_receipts_search")
        except Exception as e:
            st.error(f"Unable to load receipt snapshot: {e}")
        try:
            payment_snapshot = supabase.table("accounts_payments").select("payment_no,payment_date,party_id,amount,payment_mode,reference_no,narration").order("payment_date", desc=True).limit(25).execute().data or []
            render_recent_frame("Recent Payments", payment_snapshot, "dashboard_payments_search")
        except Exception as e:
            st.error(f"Unable to load payment snapshot: {e}")

    with dash_tab4:
        try:
            jobwork_data = supabase.table("jobwork_records").select("*").order("jobwork_date", desc=True).limit(25).execute().data or []
            party_map_rows = supabase.table("business_parties").select("id,name").execute().data or []
            party_map = {str(x.get("id")): x.get("name") for x in party_map_rows}
            jobwork_snapshot = []
            for j in jobwork_data:
                s = jobwork_summary(j.get("id"))
                jobwork_snapshot.append({
                    "Challan": j.get("challan_no"),
                    "Date": j.get("jobwork_date"),
                    "Party": party_map.get(str(j.get("party_id"))),
                    "Sent KG": s["sent_weight"],
                    "Returned KG": s["returned_weight"],
                    "Waste KG": s["waste_weight"],
                    "Pending KG": s["pending_weight"],
                    "Status": j.get("status")
                })
            render_recent_frame("JOBWORK Register", jobwork_snapshot, "dashboard_jobwork_search")
        except Exception as e:
            st.error(f"Unable to load Jobwork snapshot: {e}")

    with dash_tab5:
        try:
            docs_snapshot = supabase.table("business_documents").select("document_type,document_name,document_number,expiry_date,status").order("expiry_date").limit(25).execute().data or []
            render_recent_frame("Documents", docs_snapshot, "dashboard_documents_search")
        except Exception as e:
            st.error(f"Unable to load document snapshot: {e}")


# ---------------------------------------------------------------------
# STOCK CONTROL
# ---------------------------------------------------------------------

elif page == "Stock Control":

    st.title("📦 Stock Control")
    st.caption(
        "One cloud register for stock received and dispatched. "
        "Party, challan, quantity, bags and weight are recorded together."
    )

    # Load active stock items
    items = (
        supabase.table("stock_items")
        .select("*")
        .eq("active", True)
        .order("name")
        .execute()
        .data
    )

    # Load active parties
    parties = (
        supabase.table("business_parties")
        .select("*")
        .eq("active", True)
        .order("name")
        .execute()
        .data
    )

    lookup_items = {
        f'{x["name"]} ({x["unit"]})': x
        for x in items
    }

    lookup_parties = {
        f'{x["name"]} [{x["party_type"]}]': x
        for x in parties
    }

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Receive / Dispatch",
    "Current Stock",
    "Parties",
    "Party Ledger",
    "Movement Register"
])


     # -----------------------------------------------------------------
    # TAB 1 - RECEIVE / DISPATCH
    # -----------------------------------------------------------------

    with tab1:

        if not items:
            st.warning(
                "Add stock items first in Current Stock."
            )

        elif not parties:
            st.warning(
                "Add at least one company/party first in the Parties tab."
            )

        else:

            movement_types = [
                "📥 Receive Stock",
                "📤 New Dispatch"
            ]
            if has_feature("LEGACY_STOCK"):
                movement_types.append("📥 Legacy / Opening Stock")
            movement_mode = st.radio(
                "Transaction Type",
                movement_types,
                horizontal=True,
                key="movement_mode"
            )

            # =========================================================
            # RECEIVE STOCK
            # =========================================================

            if movement_mode == "📥 Receive Stock":

                st.subheader("📥 Receive Stock")

                st.caption(
                    "Record stock received from a supplier or other party."
                )

                c1, c2, c3 = st.columns(3)

                movement_date = c1.date_input(
                    "Receipt Date",
                    date.today(),
                    key="receive_date"
                )

                item_label = c2.selectbox(
                    "Item",
                    list(lookup_items),
                    key="receive_item"
                )

                party_label = c3.selectbox(
                    "Supplier / Party",
                    list(lookup_parties),
                    key="receive_party"
                )

                item = lookup_items[item_label]
                party = lookup_parties[party_label]

                # Optional link to an existing Purchase Order. This does not affect stock until the receipt is saved.
                purchase_order_options = {"No Purchase Order": None}
                try:
                    purchase_orders_for_party = (
                        supabase.table("orders")
                        .select("id,order_number,reference_no")
                        .eq("order_type", "PURCHASE")
                        .eq("party_id", party["id"])
                        .neq("status", "CANCELLED")
                        .neq("status", "COMPLETED")
                        .order("order_date", desc=True)
                        .limit(100)
                        .execute().data or []
                    )
                    purchase_order_ids = [x.get("id") for x in purchase_orders_for_party]
                    if purchase_order_ids:
                        order_item_rows = (
                            supabase.table("order_items")
                            .select("order_id,stock_item_id,description")
                            .in_("order_id", purchase_order_ids)
                            .execute().data or []
                        )
                        valid_order_ids = {str(x.get("order_id")) for x in order_item_rows if str(x.get("stock_item_id")) == str(item["id"])}
                        for po in purchase_orders_for_party:
                            if str(po.get("id")) in valid_order_ids:
                                purchase_order_options[f'{po.get("order_number")} | {po.get("reference_no") or "No Ref"}'] = po.get("id")
                except Exception:
                    pass

                order_choice_label = st.selectbox("Link to Purchase Order (optional)", list(purchase_order_options.keys()), key="receive_order_link")
                selected_purchase_order_id = purchase_order_options[order_choice_label]

                c1, c2, c3 = st.columns(3)

                reference_no = c1.text_input(
                    "Invoice / Challan / Gate Pass No.",
                    key="receive_reference"
                )

                vehicle_no = c2.text_input(
                    "Vehicle No.",
                    key="receive_vehicle"
                )

                handler = c3.text_input(
                    "Handled by / Driver",
                    key="receive_handler"
                )

                c1, c2, c3 = st.columns(3)

                quantity = c1.number_input(
                    f"Quantity ({item['unit']})",
                    min_value=0.0,
                    step=1.0,
                    key="receive_quantity"
                )

                bags = c2.number_input(
                    "No. of Bags",
                    min_value=0.0,
                    step=1.0,
                    key="receive_bags"
                )

                weight_kg = c3.number_input(
                    "Weight (KG)",
                    min_value=0.0,
                    step=1.0,
                    key="receive_weight"
                )

                c1, c2, c3 = st.columns(3)

                rate_per_kg = c1.number_input(
                    "Rate per KG (₹)",
                    min_value=0.0,
                    step=0.50,
                    key="receive_rate"
                )

                transportation = c2.number_input(
                    "Transportation (₹)",
                    min_value=0.0,
                    step=1.0,
                    key="receive_transport"
                )

                notes = c3.text_input(
                    "Notes",
                    key="receive_notes"
                )

                billing_amount = weight_kg * rate_per_kg

                st.divider()

                a, b, c = st.columns(3)

                a.metric(
                    "Material Value",
                    f"₹{billing_amount:,.2f}"
                )

                b.metric(
                    "Transportation",
                    f"₹{transportation:,.2f}"
                )

                c.metric(
                    "Total Value",
                    f"₹{billing_amount + transportation:,.2f}"
                )

                st.caption(
                    "Material Value = Weight × Rate per KG."
                )

                if st.button(
                    "📥 Save Receipt",
                    type="primary",
                    key="save_receipt"
                ):

                    if not reference_no.strip():
                        st.error(
                            "Invoice / Challan / Gate Pass No. is required."
                        )

                    elif quantity <= 0:
                        st.error(
                            "Quantity must be greater than zero."
                        )

                    elif weight_kg <= 0:
                        st.error(
                            "Weight must be greater than zero."
                        )

                    else:

                        fingerprint = fp(
                            movement_date,
                            item["id"],
                            party["id"],
                            "IN",
                            quantity,
                            bags,
                            weight_kg,
                            reference_no
                        )

                        data = {
                            "movement_date": str(movement_date),
                            "item_id": item["id"],
                            "party_id": party["id"],
                            "direction": "IN",
                            "quantity": quantity,
                            "bags": bags,
                            "weight_kg": weight_kg,
                            "rate_per_kg": rate_per_kg,
                            "transportation": transportation,
                            "billing_amount": billing_amount,
                            "reference_no": reference_no.strip(),
                            "vehicle_no": vehicle_no.strip() or None,
                            "handled_by": handler.strip() or None,
                            "notes": notes.strip() or None,
                            "entered_by": str(user.id),
                            "duplicate_fingerprint": fingerprint,
                            "order_id": selected_purchase_order_id
                        }

                        try:

                            (
                                supabase
                                .table("stock_movements")
                                .insert(data)
                                .execute()
                            )

                            if selected_purchase_order_id:
                                refresh_order_status(selected_purchase_order_id)
                            st.success(
                                "Stock receipt recorded successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            error_text = str(e).lower()

                            if (
                                "duplicate" in error_text
                                or "unique" in error_text
                            ):
                                st.error(
                                    "Blocked: this receipt appears "
                                    "to have already been entered."
                                )
                            else:
                                st.error(str(e))


            # =========================================================
            # OPENING / LEGACY STOCK
            # =========================================================

            elif movement_mode == "📥 Legacy / Opening Stock":

                st.subheader("📥 Opening / Legacy Stock")
                if not has_feature("LEGACY_STOCK"):
                    st.warning("This feature is restricted to the authorised account.")
                else:
                    st.caption("Use this only for verified physical stock already present when the historical receipt cannot be identified.")
                    l1, l2, l3 = st.columns(3)
                    legacy_date = l1.date_input("Stock Date", date.today(), key="legacy_date")
                    legacy_item_label = l2.selectbox("Item", list(lookup_items), key="legacy_item")
                    legacy_reference = l3.text_input("Legacy Reference No.", placeholder="OPENING-001", key="legacy_reference")
                    legacy_item = lookup_items[legacy_item_label]
                    l4, l5, l6 = st.columns(3)
                    legacy_quantity = l4.number_input(f"Quantity ({legacy_item['unit']})", min_value=0.0, step=1.0, key="legacy_quantity")
                    legacy_bags = l5.number_input("No. of Bags", min_value=0.0, step=1.0, key="legacy_bags")
                    legacy_weight = l6.number_input("Weight (KG)", min_value=0.0, step=1.0, key="legacy_weight")
                    legacy_notes = st.text_input("Notes", key="legacy_notes")
                    legacy_reason = st.text_area("Mandatory Reason", placeholder="Existing physical stock; historical source unavailable.", key="legacy_reason")
                    if st.button("📥 Add Legacy Stock to Inventory", type="primary", key="save_legacy_stock"):
                        if legacy_quantity <= 0 or legacy_weight <= 0:
                            st.error("Quantity and weight must be greater than zero.")
                        elif not legacy_reference.strip():
                            st.error("Legacy Reference No. is required.")
                        elif not legacy_reason.strip():
                            st.error("A reason is required for Opening / Legacy Stock.")
                        else:
                            try:
                                data = {
                                    "movement_date": str(legacy_date),
                                    "item_id": legacy_item["id"],
                                    "party_id": None,
                                    "direction": "IN",
                                    "quantity": legacy_quantity,
                                    "bags": legacy_bags,
                                    "weight_kg": legacy_weight,
                                    "rate_per_kg": 0,
                                    "transportation": 0,
                                    "billing_amount": 0,
                                    "reference_no": legacy_reference.strip(),
                                    "vehicle_no": None,
                                    "handled_by": None,
                                    "notes": legacy_notes.strip() or None,
                                    "entered_by": str(user.id),
                                    "duplicate_fingerprint": fp(legacy_date, legacy_item["id"], "OPENING", legacy_quantity, legacy_bags, legacy_weight, legacy_reference),
                                    "movement_type": "OPENING",
                                    "legacy_reason": legacy_reason.strip(),
                                    "purchase_status": "NOT_APPLICABLE",
                                    "order_id": None,
                                    "jobwork_id": None
                                }
                                supabase.table("stock_movements").insert(data).execute()
                                st.success("Opening / Legacy Stock added successfully.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Unable to add legacy stock: {e}")

            # =========================================================
            # NEW DISPATCH
            # =========================================================

            elif movement_mode == "📤 New Dispatch":

                st.subheader("📤 New Dispatch")

                st.caption(
                    "Dispatch stock to a customer/party. "
                    "The system will automatically check available "
                    "quantity and weight before allowing the dispatch."
                )

                # -----------------------------------------------------
                # Dispatch basic details
                # -----------------------------------------------------

                c1, c2, c3 = st.columns(3)

                dispatch_date = c1.date_input(
                    "Dispatch Date",
                    date.today(),
                    key="dispatch_date"
                )

                dispatch_item_label = c2.selectbox(
                    "Item",
                    list(lookup_items),
                    key="dispatch_item"
                )

                dispatch_party_label = c3.selectbox(
                    "Customer / Party",
                    list(lookup_parties),
                    key="dispatch_party"
                )

                dispatch_item = lookup_items[dispatch_item_label]
                dispatch_party = lookup_parties[dispatch_party_label]

                # Optional link to an existing Sales Order. This does not affect stock until the dispatch is saved.
                sales_order_options = {"No Sales Order": None}
                try:
                    sales_orders_for_party = (
                        supabase.table("orders")
                        .select("id,order_number,reference_no")
                        .eq("order_type", "SALES")
                        .eq("party_id", dispatch_party["id"])
                        .neq("status", "CANCELLED")
                        .neq("status", "COMPLETED")
                        .order("order_date", desc=True)
                        .limit(100)
                        .execute().data or []
                    )
                    sales_order_ids = [x.get("id") for x in sales_orders_for_party]
                    if sales_order_ids:
                        order_item_rows = (
                            supabase.table("order_items")
                            .select("order_id,stock_item_id")
                            .in_("order_id", sales_order_ids)
                            .execute().data or []
                        )
                        valid_order_ids = {str(x.get("order_id")) for x in order_item_rows if str(x.get("stock_item_id")) == str(dispatch_item["id"])}
                        for so in sales_orders_for_party:
                            if str(so.get("id")) in valid_order_ids:
                                sales_order_options[f'{so.get("order_number")} | {so.get("reference_no") or "No Ref"}'] = so.get("id")
                except Exception:
                    pass

                sales_order_choice_label = st.selectbox("Link to Sales Order (optional)", list(sales_order_options.keys()), key="dispatch_order_link")
                selected_sales_order_id = sales_order_options[sales_order_choice_label]

                # -----------------------------------------------------
                # LIVE STOCK POSITION
                # -----------------------------------------------------

                (
                    incoming_qty,
                    outgoing_qty,
                    available_qty,
                    incoming_weight,
                    outgoing_weight,
                    available_weight
                ) = stock_balance(dispatch_item["id"])

                st.divider()

                st.subheader("📊 Available Stock")

                s1, s2, s3, s4 = st.columns(4)

                s1.metric(
                    "Available Quantity",
                    f"{available_qty:g} {dispatch_item['unit']}"
                )

                s2.metric(
                    "Available Weight",
                    f"{available_weight:,.2f} KG"
                )

                s3.metric(
                    "Total Received",
                    f"{incoming_qty:g} {dispatch_item['unit']}"
                )

                s4.metric(
                    "Total Dispatched",
                    f"{outgoing_qty:g} {dispatch_item['unit']}"
                )

                if available_qty <= 0:

                    st.error(
                        "🚫 No stock is currently available for dispatch."
                    )

                # -----------------------------------------------------
                # Dispatch quantities
                # -----------------------------------------------------

                st.divider()

                st.subheader("Dispatch Quantity")

                c1, c2, c3 = st.columns(3)

                dispatch_quantity = c1.number_input(
                    f"Dispatch Quantity ({dispatch_item['unit']})",
                    min_value=0.0,
                    max_value=max(float(available_qty), 0.0),
                    step=1.0,
                    key="dispatch_quantity"
                )

                dispatch_bags = c2.number_input(
                    "No. of Bags",
                    min_value=0.0,
                    step=1.0,
                    key="dispatch_bags"
                )

                dispatch_weight = c3.number_input(
                    "Dispatch Weight (KG)",
                    min_value=0.0,
                    max_value=max(float(available_weight), 0.0),
                    step=1.0,
                    key="dispatch_weight"
                )

                # -----------------------------------------------------
                # LIVE REMAINING STOCK
                # -----------------------------------------------------

                remaining_qty = available_qty - dispatch_quantity
                remaining_weight = available_weight - dispatch_weight

                r1, r2 = st.columns(2)

                r1.metric(
                    "Stock After Dispatch",
                    f"{remaining_qty:g} {dispatch_item['unit']}"
                )

                r2.metric(
                    "Weight After Dispatch",
                    f"{remaining_weight:,.2f} KG"
                )

                if remaining_qty < 0:

                    st.error(
                        "🚫 Dispatch quantity exceeds available stock."
                    )

                if remaining_weight < 0:

                    st.error(
                        "🚫 Dispatch weight exceeds available stock."
                    )

                # -----------------------------------------------------
                # Commercial details
                # -----------------------------------------------------

                st.divider()

                st.subheader("💰 Dispatch Value")

                c1, c2, c3 = st.columns(3)

                dispatch_rate = c1.number_input(
                    "Rate per KG (₹)",
                    min_value=0.0,
                    step=0.50,
                    key="dispatch_rate"
                )

                dispatch_transportation = c2.number_input(
                    "Transportation (₹)",
                    min_value=0.0,
                    step=1.0,
                    key="dispatch_transport"
                )

                dispatch_billing = (
                    dispatch_weight * dispatch_rate
                )

                c3.metric(
                    "Material Value",
                    f"₹{dispatch_billing:,.2f}"
                )

                v1, v2 = st.columns(2)

                v1.metric(
                    "Transportation",
                    f"₹{dispatch_transportation:,.2f}"
                )

                v2.metric(
                    "Total Dispatch Value",
                    f"₹{dispatch_billing + dispatch_transportation:,.2f}"
                )

                st.caption(
                    "Material Value = Dispatch Weight × Rate per KG."
                )

                # -----------------------------------------------------
                # Dispatch documentation
                # -----------------------------------------------------

                st.divider()

                st.subheader("🚚 Dispatch Documentation")

                c1, c2, c3 = st.columns(3)

                dispatch_reference = c1.text_input(
                    "Dispatch / Challan No.",
                    key="dispatch_reference"
                )

                dispatch_vehicle = c2.text_input(
                    "Vehicle No.",
                    key="dispatch_vehicle"
                )

                dispatch_handler = c3.text_input(
                    "Driver / Handled By",
                    key="dispatch_handler"
                )

                dispatch_notes = st.text_input(
                    "Dispatch Notes",
                    key="dispatch_notes"
                )

                # -----------------------------------------------------
                # FINAL DISPATCH SUMMARY
                # -----------------------------------------------------

                st.divider()

                st.subheader("📋 Dispatch Summary")

                summary_left, summary_right = st.columns(2)

                with summary_left:

                    st.write(
                        f"**Customer / Party:** "
                        f"{dispatch_party['name']}"
                    )

                    st.write(
                        f"**Item:** "
                        f"{dispatch_item['name']}"
                    )

                    st.write(
                        f"**Quantity:** "
                        f"{dispatch_quantity:g} "
                        f"{dispatch_item['unit']}"
                    )

                    st.write(
                        f"**Weight:** "
                        f"{dispatch_weight:,.2f} KG"
                    )

                    st.write(
                        f"**Bags:** "
                        f"{dispatch_bags:g}"
                    )

                with summary_right:

                    st.write(
                        f"**Material Value:** "
                        f"₹{dispatch_billing:,.2f}"
                    )

                    st.write(
                        f"**Transportation:** "
                        f"₹{dispatch_transportation:,.2f}"
                    )

                    st.write(
                        f"**Total Value:** "
                        f"₹{dispatch_billing + dispatch_transportation:,.2f}"
                    )

                    st.write(
                        f"**Stock Remaining:** "
                        f"{remaining_qty:g} "
                        f"{dispatch_item['unit']}"
                    )

                    st.write(
                        f"**Weight Remaining:** "
                        f"{remaining_weight:,.2f} KG"
                    )

                # -----------------------------------------------------
                # SAVE DISPATCH
                # -----------------------------------------------------

                st.divider()

                save_dispatch = st.button(
                    "🚚 Confirm & Save Dispatch",
                    type="primary",
                    use_container_width=True,
                    key="save_dispatch"
                )

                if save_dispatch:

                    # Final validation against database
                    # immediately before saving.
                    (
                        latest_in_qty,
                        latest_out_qty,
                        latest_available_qty,
                        latest_in_weight,
                        latest_out_weight,
                        latest_available_weight
                    ) = stock_balance(dispatch_item["id"])

                    if not dispatch_reference.strip():

                        st.error(
                            "Dispatch / Challan No. is required."
                        )

                    elif dispatch_quantity <= 0:

                        st.error(
                            "Dispatch quantity must be greater than zero."
                        )

                    elif dispatch_weight <= 0:

                        st.error(
                            "Dispatch weight must be greater than zero."
                        )

                    elif dispatch_quantity > latest_available_qty:

                        st.error(
                            f"🚫 Dispatch blocked: available stock is "
                            f"only {latest_available_qty:g} "
                            f"{dispatch_item['unit']}, but you entered "
                            f"{dispatch_quantity:g}."
                        )

                    elif dispatch_weight > latest_available_weight:

                        st.error(
                            f"🚫 Dispatch blocked: available weight is "
                            f"only {latest_available_weight:,.2f} KG, "
                            f"but you entered "
                            f"{dispatch_weight:,.2f} KG."
                        )

                    else:

                        fingerprint = fp(
                            dispatch_date,
                            dispatch_item["id"],
                            dispatch_party["id"],
                            "OUT",
                            dispatch_quantity,
                            dispatch_bags,
                            dispatch_weight,
                            dispatch_reference
                        )

                        data = {
                            "movement_date": str(dispatch_date),
                            "item_id": dispatch_item["id"],
                            "party_id": dispatch_party["id"],
                            "direction": "OUT",
                            "quantity": dispatch_quantity,
                            "bags": dispatch_bags,
                            "weight_kg": dispatch_weight,
                            "rate_per_kg": dispatch_rate,
                            "transportation":
                                dispatch_transportation,
                            "billing_amount":
                                dispatch_billing,
                            "reference_no":
                                dispatch_reference.strip(),
                            "vehicle_no":
                                dispatch_vehicle.strip() or None,
                            "handled_by":
                                dispatch_handler.strip() or None,
                            "notes":
                                dispatch_notes.strip() or None,
                            "entered_by":
                                str(user.id),
                            "duplicate_fingerprint":
                                fingerprint,
                            "order_id":
                                selected_sales_order_id
                        }

                        try:

                            dispatch_response = (
                                supabase
                                .table("stock_movements")
                                .insert(data)
                                .execute()
                            )

                            if selected_sales_order_id:
                                refresh_order_status(selected_sales_order_id)
                            st.success(
                                "🚚 Dispatch recorded successfully. The dispatch is now available to Accounts for sales processing."
                            )

                            st.info(
                                f"Remaining stock: "
                                f"{latest_available_qty - dispatch_quantity:g} "
                                f"{dispatch_item['unit']} | "
                                f"Remaining weight: "
                                f"{latest_available_weight - dispatch_weight:,.2f} KG"
                            )

                            st.rerun()

                        except Exception as e:

                            error_text = str(e).lower()

                            if (
                                "duplicate" in error_text
                                or "unique" in error_text
                            ):

                                st.error(
                                    "Blocked: this dispatch appears "
                                    "to have already been entered."
                                )

                            else:

                                st.error(str(e))


    # -----------------------------------------------------------------
    # TAB 2 - CURRENT STOCK
    # -----------------------------------------------------------------

    with tab2:

        rows = []

        for x in items:

            (
                incoming_qty,
                outgoing_qty,
                balance_qty,
                incoming_weight,
                outgoing_weight,
                balance_weight
            ) = stock_balance(x["id"])

            rows.append({
                "Item": x["name"],
                "Unit": x["unit"],
                "Total In": incoming_qty,
                "Total Out": outgoing_qty,
                "Current Balance": balance_qty,
                "Weight In (KG)": incoming_weight,
                "Weight Out (KG)": outgoing_weight,
                "Weight Balance (KG)": balance_weight,
                "Minimum Level": x["minimum_level"],
                "Status": (
                    "⚠️ LOW"
                    if balance_qty <= float(x["minimum_level"])
                    else "OK"
                )
            })

        current_stock_search = st.text_input("🔎 Search Current Stock", key="current_stock_search", placeholder="Item name or unit...")
        filtered_current_stock = filter_display_rows(rows, current_stock_search, ["Item", "Unit", "Status"])
        st.dataframe(
            filtered_current_stock,
            use_container_width=True,
            hide_index=True
        )
        add_excel_download(filtered_current_stock, "SP_Enterprise_Current_Stock.xlsx", "📊 Download Current Stock (Excel)", "export_current_stock", "Current Stock")

        if current_stock_search.strip():
            matched_items = [x for x in items if current_stock_search.strip().lower() in str(x.get("name") or "").lower()]
            matched_item_ids = [x.get("id") for x in matched_items]
            if matched_item_ids:
                try:
                    history = (
                        supabase.table("stock_movements")
                        .select("movement_date,direction,movement_type,reference_no,quantity,bags,weight_kg,rate_per_kg,billing_amount,stock_items(name,unit),business_parties(name)")
                        .in_("item_id", matched_item_ids)
                        .order("movement_date", desc=True)
                        .limit(1000)
                        .execute().data or []
                    )
                    history_rows = []
                    for h in history:
                        hi = h.get("stock_items") or {}
                        hp = h.get("business_parties") or {}
                        history_rows.append({
                            "Date": h.get("movement_date"),
                            "Movement": h.get("movement_type") or h.get("direction"),
                            "Direction": h.get("direction"),
                            "Party": hp.get("name"),
                            "Challan / Reference": h.get("reference_no"),
                            "Item": hi.get("name"),
                            "Qty": h.get("quantity"),
                            "Weight KG": h.get("weight_kg"),
                            "Rate/KG": h.get("rate_per_kg"),
                            "Billing ₹": h.get("billing_amount")
                        })
                    st.markdown("### Item Movement History")
                    st.dataframe(history_rows, use_container_width=True, hide_index=True)
                    add_excel_download(history_rows, "SP_Enterprise_Item_Movement_History.xlsx", "📊 Download Item History (Excel)", "export_item_history", "Item History")
                except Exception as e:
                    st.warning(f"Unable to load item movement history: {e}")

        render_delete_control(
            "stock_items",
            items,
            lambda r: f'{r.get("name", "Item")} ({r.get("unit", "")})',
            "delete_stock_item"
        )

        with st.expander("➕ Add stock item"):

            with st.form("new_item"):

                name = st.text_input("Item name")

                unit = st.selectbox(
                    "Unit",
                    ["PCS", "KG", "TON", "MTR", "BOX", "BAG", "OTHER"]
                )

                minimum = st.number_input(
                    "Minimum stock level",
                    min_value=0.0,
                    step=1.0
                )

                if st.form_submit_button("Add item"):

                    if not name.strip():
                        st.error("Item name is required.")

                    else:
                        try:
                            (
                                supabase
                                .table("stock_items")
                                .insert({
                                    "name": name.strip(),
                                    "unit": unit,
                                    "minimum_level": minimum,
                                    "active": True
                                })
                                .execute()
                            )

                            st.success("Item added.")
                            st.rerun()

                        except Exception as e:
                            st.error(str(e))


    # -----------------------------------------------------------------
    # TAB 3 - PARTIES
    # -----------------------------------------------------------------

    with tab3:

        st.subheader("Company / Party Master")

        st.write(
            "Create each supplier/customer once. "
            "All future stock transactions can then be linked "
            "to the same company."
        )

        party_rows = []

        for p in parties:
            party_rows.append({
                "Company / Party": p["name"],
                "Type": p["party_type"],
                "Contact Person": p.get("contact_person"),
                "Phone": p.get("phone"),
                "Address": p.get("address")
            })

        party_search = st.text_input("🔎 Search Parties", key="party_search", placeholder="Company, type, phone, GSTIN...")
        filtered_party_rows = filter_display_rows(party_rows, party_search)
        st.dataframe(
            filtered_party_rows,
            use_container_width=True,
            hide_index=True
        )
        add_excel_download(filtered_party_rows, "SP_Enterprise_Party_List.xlsx", "📊 Download Party List (Excel)", "export_party_list", "Party List")

        render_delete_control(
            "business_parties",
            parties,
            lambda r: f'{r.get("name", "Party")} [{r.get("party_type", "")}]',
            "delete_party"
        )

        with st.expander("➕ Add company / party"):

            with st.form("new_party"):

                name = st.text_input("Company / Party Name")

                party_type = st.selectbox(
                    "Party Type",
                    ["SUPPLIER", "CUSTOMER", "BOTH"]
                )

                st.caption(
                    "JOBWORK companies are created from the separate JOBWORK module."
                )

                contact_person = st.text_input(
                    "Contact Person"
                )

                phone = st.text_input("Phone")

                address = st.text_input("Address")

                if st.form_submit_button("Add Party"):

                    if not name.strip():
                        st.error("Company / Party name is required.")

                    else:

                        try:
                            (
                                supabase
                                .table("business_parties")
                                .insert({
                                    "name": name.strip(),
                                    "party_type": party_type,
                                    "contact_person":
                                        contact_person.strip() or None,
                                    "phone":
                                        phone.strip() or None,
                                    "address":
                                        address.strip() or None,
                                    "active": True
                                })
                                .execute()
                            )

                            st.success("Company / Party added.")
                            st.rerun()

                        except Exception as e:
                            st.error(str(e))


    # -----------------------------------------------------------------
    # TAB 4 - PARTY LEDGER
    # -----------------------------------------------------------------

    with tab4:

        st.subheader("Party-wise Stock Ledger")

        if not parties:
            st.info("Add a company/party first.")

        else:

            selected_party_label = st.selectbox(
                "Select Company / Party",
                list(lookup_parties),
                key="ledger_party"
            )

            selected_party = lookup_parties[selected_party_label]

            ledger_rows = (
                supabase
                .table("stock_movements")
                .select(
                    """
                    movement_date,
                    direction,
                    quantity,
                    bags,
                    weight_kg,
                    rate_per_kg,
                    transportation,
                    billing_amount,
                    reference_no,
                    vehicle_no,
                    handled_by,
                    notes,
                    stock_items(name,unit)
                    """
                )
                .eq("party_id", selected_party["id"])
                .order("movement_date", desc=True)
                .limit(2000)
                .execute()
                .data
            )

            display_rows = []

            total_in_qty = 0
            total_out_qty = 0
            total_in_weight = 0
            total_out_weight = 0
            total_billing = 0

            for r in ledger_rows:

                item = r.get("stock_items") or {}

                qty = float(r.get("quantity") or 0)
                weight = float(r.get("weight_kg") or 0)
                billing = float(r.get("billing_amount") or 0)

                if r["direction"] == "IN":
                    total_in_qty += qty
                    total_in_weight += weight
                else:
                    total_out_qty += qty
                    total_out_weight += weight
                    total_billing += billing

                display_rows.append({
                    "Date": r["movement_date"],
                    "Movement": r["direction"],
                    "Challan / Ref": r.get("reference_no"),
                    "Item": item.get("name"),
                    "Qty": qty,
                    "Unit": item.get("unit"),
                    "Bags": r.get("bags"),
                    "Weight KG": weight,
                    "Rate/KG": r.get("rate_per_kg"),
                    "Transport ₹": r.get("transportation"),
                    "Billing ₹": billing,
                    "Vehicle": r.get("vehicle_no"),
                    "Handled By": r.get("handled_by"),
                    "Notes": r.get("notes")
                })

            a, b, c, d = st.columns(4)

            a.metric("Total IN Qty", f"{total_in_qty:g}")
            b.metric("Total OUT Qty", f"{total_out_qty:g}")
            c.metric(
                "Weight moved",
                f"{total_in_weight + total_out_weight:,.2f} KG"
            )
            d.metric(
                "OUT Billing",
                f"₹{total_billing:,.2f}"
            )

            party_ledger_search = st.text_input("🔎 Search Party Ledger", key="party_ledger_search", placeholder="Item, challan, date, movement...")
            filtered_party_ledger_rows = filter_display_rows(display_rows, party_ledger_search)
            st.dataframe(
                filtered_party_ledger_rows,
                use_container_width=True,
                hide_index=True
            )
            add_excel_download(filtered_party_ledger_rows, "SP_Enterprise_Party_Ledger.xlsx", "📊 Download Party Ledger (Excel)", "export_party_ledger", "Party Ledger")


    # -----------------------------------------------------------------
    # TAB 5 - MOVEMENT REGISTER
    # -----------------------------------------------------------------

    with tab5:

        rows = (
            supabase
            .table("stock_movements")
            .select(
                """
                movement_date,
                direction,
                quantity,
                bags,
                weight_kg,
                rate_per_kg,
                transportation,
                billing_amount,
                reference_no,
                party_id,
                vehicle_no,
                handled_by,
                notes,
                stock_items(name,unit),
                business_parties(name),
                movement_type,
                order_id,
                jobwork_id
                """
            )
            .order("movement_date", desc=True)
            .limit(2000)
            .execute()
            .data
        )

        out = []

        for r in rows:

            item = r.get("stock_items") or {}
            party = r.get("business_parties") or {}

            out.append({
                "Date": r["movement_date"],
                "Movement": r["direction"],
                "Movement Type": r.get("movement_type") or "NORMAL",
                "JOBWORK": "TO JOBWORK" if r.get("movement_type") == "JOBWORK_OUT" else ("FROM JOBWORK" if r.get("movement_type") == "JOBWORK_IN" else ""),
                "Party": party.get("name"),
                "Challan / Reference": r.get("reference_no"),
                "Item": item.get("name"),
                "Qty": r.get("quantity"),
                "Unit": item.get("unit"),
                "Bags": r.get("bags"),
                "Weight KG": r.get("weight_kg"),
                "Rate/KG": r.get("rate_per_kg"),
                "Transport ₹": r.get("transportation"),
                "Billing ₹": r.get("billing_amount"),
                "Vehicle": r.get("vehicle_no"),
                "Handled By": r.get("handled_by"),
                "Notes": r.get("notes")
            })

        movement_search = st.text_input("🔎 Search Movement Register", key="movement_register_search", placeholder="Item, party, challan, movement type, jobwork...")
        filtered_movement = filter_display_rows(out, movement_search)
        st.dataframe(
            filtered_movement,
            use_container_width=True,
            hide_index=True
        )
        add_excel_download(filtered_movement, "SP_Enterprise_Stock_Movement_Register.xlsx", "📊 Download Movement Register (Excel)", "export_movement_register", "Movement Register")

        movement_records = (
            supabase.table("stock_movements")
            .select("*")
            .order("movement_date", desc=True)
            .limit(500)
            .execute().data or []
        )
        render_delete_control(
            "stock_movements",
            movement_records,
            lambda r: f'{r.get("movement_date")} | {r.get("direction")} | {r.get("reference_no") or "No Ref"} | {r.get("quantity", 0)}',
            "delete_stock_movement",
            transaction=True
        )

        if has_feature("MODIFY_STOCK"):
            st.divider()
            with st.expander("✏️ Modify Stock Entry (Authorised Account Only)", expanded=False):
                mod_options = {
                    f'{r.get("movement_date")} | {r.get("direction")} | {r.get("reference_no") or "No Ref"} | {r.get("quantity", 0)}': r.get("id")
                    for r in movement_records if r.get("id")
                }
                if mod_options:
                    mod_label = st.selectbox("Select stock entry to modify", list(mod_options), key="modify_stock_record")
                    mod_id = mod_options[mod_label]
                    try:
                        current_record = (supabase.table("stock_movements").select("*").eq("id", mod_id).limit(1).execute().data or [None])[0]
                        if current_record:
                            edit_item_options = {f'{x.get("name")} ({x.get("unit")})': x for x in items}
                            edit_party_options = {"No Party": None}
                            edit_party_options.update({f'{p.get("name")} [{p.get("party_type")}]': p for p in parties})
                            current_item = next((x for x in items if str(x.get("id")) == str(current_record.get("item_id"))), items[0] if items else None)
                            current_party = next((p for p in parties if str(p.get("id")) == str(current_record.get("party_id"))), None)
                            current_item_label = next((k for k, v in edit_item_options.items() if current_item and str(v.get("id")) == str(current_item.get("id"))), list(edit_item_options)[0] if edit_item_options else None)
                            current_party_label = "No Party" if not current_party else next((k for k, v in edit_party_options.items() if v and str(v.get("id")) == str(current_party.get("id"))), "No Party")
                            st.warning("Modification is audited automatically. Linked Purchase, Sales, Order or JOBWORK records may require separate accounting review.")
                            with st.form("modify_stock_form"):
                                e1, e2, e3 = st.columns(3)
                                new_date = e1.date_input("Movement Date", value=date.fromisoformat(str(current_record.get("movement_date"))))
                                new_item_label = e2.selectbox("Item", list(edit_item_options), index=list(edit_item_options).index(current_item_label) if current_item_label in edit_item_options else 0)
                                new_party_label = e3.selectbox("Party", list(edit_party_options), index=list(edit_party_options).index(current_party_label) if current_party_label in edit_party_options else 0)
                                e4, e5, e6 = st.columns(3)
                                new_qty = e4.number_input("Quantity", min_value=0.0, value=float(current_record.get("quantity") or 0), step=1.0)
                                new_bags = e5.number_input("Bags", min_value=0.0, value=float(current_record.get("bags") or 0), step=1.0)
                                new_weight = e6.number_input("Weight (KG)", min_value=0.0, value=float(current_record.get("weight_kg") or 0), step=1.0)
                                e7, e8, e9 = st.columns(3)
                                new_rate = e7.number_input("Rate per KG (₹)", min_value=0.0, value=float(current_record.get("rate_per_kg") or 0), step=0.50)
                                new_transport = e8.number_input("Transportation (₹)", min_value=0.0, value=float(current_record.get("transportation") or 0), step=1.0)
                                new_billing = e9.number_input("Billing Amount (₹)", min_value=0.0, value=float(current_record.get("billing_amount") or 0), step=1.0)
                                e10, e11, e12 = st.columns(3)
                                new_ref = e10.text_input("Reference / Challan", value=str(current_record.get("reference_no") or ""))
                                new_vehicle = e11.text_input("Vehicle No.", value=str(current_record.get("vehicle_no") or ""))
                                new_handler = e12.text_input("Handled By", value=str(current_record.get("handled_by") or ""))
                                new_notes = st.text_input("Notes", value=str(current_record.get("notes") or ""))
                                st.caption(f"Movement Type: {current_record.get('movement_type') or 'NORMAL'} | Direction: {current_record.get('direction')}")
                                save_mod = st.form_submit_button("💾 Save Modification", type="primary", use_container_width=True)
                            if save_mod:
                                selected_new_item = edit_item_options[new_item_label]
                                selected_new_party = edit_party_options[new_party_label]
                                if new_qty <= 0 or new_weight <= 0 or not new_ref.strip():
                                    st.error("Quantity, weight and reference/challan are required.")
                                else:
                                    # Validate OUT stock against the balance excluding this movement.
                                    if current_record.get("direction") == "OUT":
                                        excluded_rows = (
                                            supabase.table("stock_movements")
                                            .select("direction,quantity,weight_kg")
                                            .eq("item_id", selected_new_item["id"])
                                            .neq("id", mod_id)
                                            .execute().data or []
                                        )
                                        in_qty = sum(float(x.get("quantity") or 0) for x in excluded_rows if x.get("direction") == "IN")
                                        out_qty = sum(float(x.get("quantity") or 0) for x in excluded_rows if x.get("direction") == "OUT")
                                        in_wt = sum(float(x.get("weight_kg") or 0) for x in excluded_rows if x.get("direction") == "IN")
                                        out_wt = sum(float(x.get("weight_kg") or 0) for x in excluded_rows if x.get("direction") == "OUT")
                                        if new_qty > in_qty - out_qty + 0.0001 or new_weight > in_wt - out_wt + 0.0001:
                                            st.error("Modification blocked because the corrected OUT movement would exceed the available stock position.")
                                            st.stop()
                                    new_data = {
                                        "movement_date": str(new_date),
                                        "item_id": selected_new_item["id"],
                                        "party_id": selected_new_party["id"] if selected_new_party else None,
                                        "quantity": new_qty,
                                        "bags": new_bags,
                                        "weight_kg": new_weight,
                                        "rate_per_kg": new_rate,
                                        "transportation": new_transport,
                                        "billing_amount": new_billing,
                                        "reference_no": new_ref.strip(),
                                        "vehicle_no": new_vehicle.strip() or None,
                                        "handled_by": new_handler.strip() or None,
                                        "notes": new_notes.strip() or None,
                                        "duplicate_fingerprint": fp(new_date, selected_new_item["id"], selected_new_party["id"] if selected_new_party else None, current_record.get("direction"), new_qty, new_bags, new_weight, new_ref)
                                    }
                                    try:
                                        supabase.table("stock_movements").update(new_data).eq("id", mod_id).execute()
                                        if current_record.get("order_id"):
                                            refresh_order_status(current_record.get("order_id"))
                                        if current_record.get("jobwork_id"):
                                            refresh_jobwork_status(current_record.get("jobwork_id"))
                                        st.success("Stock entry modified successfully. The before/after record has been added to Modification Audit.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Unable to modify stock entry: {e}")
                    except Exception as e:
                        st.error(f"Unable to load the selected stock entry: {e}")
        elif st.session_state.get("user"):
            st.caption("Modification access is restricted to the authorised account.")




# ---------------------------------------------------------------------
# ORDERS
# ---------------------------------------------------------------------

elif page == "Orders":

    try:
        items = (supabase.table("stock_items").select("*").eq("active", True).order("name").execute().data or [])
        parties = (supabase.table("business_parties").select("*").eq("active", True).order("name").execute().data or [])
    except Exception as e:
        items, parties = [], []
        st.error(f"Unable to load master data for Orders: {e}")

    st.markdown('<div class="module-title">Orders</div>', unsafe_allow_html=True)
    st.markdown('<div class="module-subtitle">Separate pre-transaction order control. Orders do not change physical stock until an actual receipt or dispatch is recorded.</div>', unsafe_allow_html=True)

    order_tab1, order_tab2 = st.tabs(["📥 Purchase Orders", "📤 Sales Orders"])

    def render_order_create_form(order_type):
        is_purchase = order_type == "PURCHASE"
        label_party = "Supplier" if is_purchase else "Customer"
        form_key = "purchase_order_form" if is_purchase else "sales_order_form"
        order_prefix = "PO" if is_purchase else "SO"

        parties_for_order = [p for p in parties if str(p.get("party_type", "")).upper() in ({"SUPPLIER", "BOTH"} if is_purchase else {"CUSTOMER", "BOTH"})]
        party_options = {f'{p.get("name")} [{p.get("party_type")}]': p for p in parties_for_order}
        item_options = {f'{x.get("name")} ({x.get("unit")})': x for x in items}

        with st.expander(f"➕ Create {label_party} Order", expanded=True):
            if not party_options:
                st.warning(f"Create at least one {label_party.lower()} in Stock Control → Parties first.")
                return
            if not item_options:
                st.warning("Create at least one stock item first.")
                return
            with st.form(form_key, clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                order_number = c1.text_input("Order Number", placeholder=f"{order_prefix}-001")
                order_date = c2.date_input("Order Date", value=date.today())
                party_label = c3.selectbox(label_party, list(party_options))
                selected_party = party_options[party_label]

                c4, c5, c6 = st.columns(3)
                item_label = c4.selectbox("Item", list(item_options))
                selected_item = item_options[item_label]
                quantity = c5.number_input(f"Ordered Quantity ({selected_item['unit']})", min_value=0.0, step=1.0)
                weight = c6.number_input("Ordered Weight (KG)", min_value=0.0, step=1.0)

                c7, c8, c9 = st.columns(3)
                rate = c7.number_input("Rate per KG (₹)", min_value=0.0, step=0.50)
                ref_no = c8.text_input("Order / Challan Reference")
                order_date_field = "Expected Date" if is_purchase else "Required Date"
                target_date = c9.date_input(order_date_field, value=date.today())
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("💾 Save Order", type="primary", use_container_width=True)

            if submitted:
                if not order_number.strip() or quantity <= 0:
                    st.error("Order Number and a positive ordered quantity are required.")
                else:
                    try:
                        header = {
                            "order_number": order_number.strip(),
                            "order_type": order_type,
                            "order_date": order_date.isoformat(),
                            "party_id": selected_party["id"],
                            "reference_no": ref_no.strip() or None,
                            "expected_date": target_date.isoformat() if is_purchase else None,
                            "required_date": target_date.isoformat() if not is_purchase else None,
                            "status": "OPEN",
                            "notes": notes.strip() or None,
                            "entered_by": str(user.id)
                        }
                        order_response = supabase.table("orders").insert(header).execute()
                        order_id = order_response.data[0]["id"]
                        supabase.table("order_items").insert({
                            "order_id": order_id,
                            "stock_item_id": selected_item["id"],
                            "description": selected_item["name"],
                            "quantity": quantity,
                            "unit": selected_item["unit"],
                            "weight_kg": weight,
                            "rate_per_kg": rate
                        }).execute()
                        st.success(f"{label_party} order {order_number.strip()} created successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to create order: {e}")

    with order_tab1:
        render_order_create_form("PURCHASE")
        st.divider()
        status_filter = st.selectbox("Purchase Order Status", ["ALL", "OPEN", "PARTIAL", "COMPLETED", "CANCELLED"], key="purchase_order_status_filter")
        order_search = st.text_input("🔎 Search Purchase Orders", key="purchase_order_search", placeholder="Order, supplier, item, challan...")
        purchase_order_rows, raw_purchase_orders = order_summary_rows("PURCHASE", query=order_search, status_filter=status_filter)
        st.dataframe(purchase_order_rows, use_container_width=True, hide_index=True)
        add_excel_download(purchase_order_rows, "SP_Enterprise_Purchase_Orders.xlsx", "📊 Download Purchase Orders (Excel)", "export_purchase_orders", "Purchase Orders")
        if raw_purchase_orders:
            render_delete_control("orders", raw_purchase_orders, lambda r: f'{r.get("order_number")} | {r.get("order_date")} | {r.get("status")}', "delete_purchase_order")

    with order_tab2:
        render_order_create_form("SALES")
        st.divider()
        status_filter = st.selectbox("Sales Order Status", ["ALL", "OPEN", "PARTIAL", "COMPLETED", "CANCELLED"], key="sales_order_status_filter")
        order_search = st.text_input("🔎 Search Sales Orders", key="sales_order_search", placeholder="Order, customer, item, reference...")
        sales_order_rows, raw_sales_orders = order_summary_rows("SALES", query=order_search, status_filter=status_filter)
        st.dataframe(sales_order_rows, use_container_width=True, hide_index=True)
        add_excel_download(sales_order_rows, "SP_Enterprise_Sales_Orders.xlsx", "📊 Download Sales Orders (Excel)", "export_sales_orders", "Sales Orders")
        if raw_sales_orders:
            render_delete_control("orders", raw_sales_orders, lambda r: f'{r.get("order_number")} | {r.get("order_date")} | {r.get("status")}', "delete_sales_order")


# ---------------------------------------------------------------------
# JOBWORK
# ---------------------------------------------------------------------

elif page == "JOBWORK":

    try:
        items = (supabase.table("stock_items").select("*").eq("active", True).order("name").execute().data or [])
        parties = (supabase.table("business_parties").select("*").eq("active", True).order("name").execute().data or [])
    except Exception as e:
        items, parties = [], []
        st.error(f"Unable to load master data for JOBWORK: {e}")

    st.markdown('<div class="module-title">JOBWORK</div>', unsafe_allow_html=True)
    st.markdown('<div class="module-subtitle">Track material sent to and received from Jobwork without treating the movement as a purchase, sale, receipt or payment.</div>', unsafe_allow_html=True)

    # JOBWORK parties are created here so users do not need to leave the JOBWORK module.
    with st.expander("➕ Add JOBWORK Company", expanded=False):
        with st.form("new_jobwork_party", clear_on_submit=True):
            jw1, jw2 = st.columns(2)
            jobwork_name = jw1.text_input("JOBWORK Company Name")
            jobwork_contact = jw2.text_input("Contact Person")
            jw3, jw4 = st.columns(2)
            jobwork_phone = jw3.text_input("Phone")
            jobwork_address = jw4.text_input("Address")
            jobwork_gstin = st.text_input("GSTIN (optional)")

            save_jobwork_party = st.form_submit_button(
                "💾 Add JOBWORK Company",
                type="primary",
                use_container_width=True
            )

        if save_jobwork_party:
            clean_jobwork_name = jobwork_name.strip()
            if not clean_jobwork_name:
                st.error("JOBWORK Company Name is required.")
            else:
                try:
                    existing_jobwork = (
                        supabase
                        .table("business_parties")
                        .select("id,name")
                        .eq("name", clean_jobwork_name)
                        .eq("party_type", "JOBWORK")
                        .limit(1)
                        .execute()
                        .data
                        or []
                    )

                    if existing_jobwork:
                        st.warning("A JOBWORK company with this name already exists.")
                    else:
                        supabase.table("business_parties").insert({
                            "name": clean_jobwork_name,
                            "party_type": "JOBWORK",
                            "contact_person": jobwork_contact.strip() or None,
                            "phone": jobwork_phone.strip() or None,
                            "address": jobwork_address.strip() or None,
                            "gstin": jobwork_gstin.strip() or None,
                            "active": True
                        }).execute()
                        st.success(
                            f"JOBWORK company '{clean_jobwork_name}' added successfully. "
                            "It is now available in Stock Control → Parties and JOBWORK."
                        )
                        st.rerun()
                except Exception as e:
                    st.error(f"Unable to create JOBWORK company: {e}")

    job_tab1, job_tab2, job_tab3 = st.tabs(["📤 Send to JOBWORK", "📥 Receive from JOBWORK", "📋 JOBWORK Register"])

    jobwork_parties = [p for p in parties if str(p.get("party_type", "")).upper() == "JOBWORK"]
    jobwork_party_options = {f'{p.get("name")} [JOBWORK]': p for p in jobwork_parties}
    jobwork_item_options = {f'{x.get("name")} ({x.get("unit")})': x for x in items}

    with job_tab1:
        if not jobwork_party_options:
            st.warning("No JOBWORK company has been created yet. Use the 'Add JOBWORK Company' section above.")
        elif not jobwork_item_options:
            st.warning("Create stock items first.")
        else:
            with st.form("jobwork_send_form", clear_on_submit=True):
                j1, j2, j3 = st.columns(3)
                challan_no = j1.text_input("JOBWORK Challan No.")
                jobwork_date = j2.date_input("Date", value=date.today())
                party_label = j3.selectbox("JOBWORK Company", list(jobwork_party_options))
                selected_job_party = jobwork_party_options[party_label]
                j4, j5, j6 = st.columns(3)
                item_label = j4.selectbox("Raw Material", list(jobwork_item_options))
                selected_job_item = jobwork_item_options[item_label]
                qty = j5.number_input(f"Quantity ({selected_job_item['unit']})", min_value=0.0, step=1.0)
                weight = j6.number_input("Weight (KG)", min_value=0.0, step=1.0)
                bags = st.number_input("No. of Bags", min_value=0.0, step=1.0)
                notes = st.text_area("Notes")
                save_job_send = st.form_submit_button("📤 Send Material to JOBWORK", type="primary", use_container_width=True)

            if save_job_send:
                current_bal = stock_balance(selected_job_item["id"])
                available_qty = current_bal[2]
                available_weight = current_bal[5]
                if not challan_no.strip() or qty <= 0 or weight <= 0:
                    st.error("Challan number, quantity and weight are required.")
                elif qty > available_qty or weight > available_weight:
                    st.error("JOBWORK dispatch exceeds available stock.")
                else:
                    try:
                        job_response = supabase.table("jobwork_records").insert({
                            "challan_no": challan_no.strip(),
                            "jobwork_date": jobwork_date.isoformat(),
                            "party_id": selected_job_party["id"],
                            "status": "SENT",
                            "waste_quantity": 0,
                            "waste_weight_kg": 0,
                            "waste_notes": None,
                            "notes": notes.strip() or None,
                            "entered_by": str(user.id)
                        }).execute()
                        jobwork_id = job_response.data[0]["id"]
                        supabase.table("stock_movements").insert({
                            "movement_date": jobwork_date.isoformat(),
                            "item_id": selected_job_item["id"],
                            "party_id": selected_job_party["id"],
                            "direction": "OUT",
                            "movement_type": "JOBWORK_OUT",
                            "quantity": qty,
                            "bags": bags,
                            "weight_kg": weight,
                            "rate_per_kg": 0,
                            "transportation": 0,
                            "billing_amount": 0,
                            "reference_no": challan_no.strip(),
                            "vehicle_no": None,
                            "handled_by": None,
                            "notes": notes.strip() or None,
                            "entered_by": str(user.id),
                            "duplicate_fingerprint": fp(jobwork_date, selected_job_item["id"], selected_job_party["id"], "JOBWORK_OUT", qty, bags, weight, challan_no),
                            "purchase_status": "NOT_APPLICABLE",
                            "purchase_id": None,
                            "order_id": None,
                            "jobwork_id": jobwork_id,
                            "legacy_reason": None
                        }).execute()
                        st.success(f"{qty:g} {selected_job_item['unit']} / {weight:,.2f} KG sent to JOBWORK under {challan_no.strip()}.")
                        st.rerun()
                    except Exception as e:
                        try:
                            if 'jobwork_id' in locals():
                                supabase.table("jobwork_records").delete().eq("id", jobwork_id).execute()
                        except Exception:
                            pass
                        st.error(f"Unable to record JOBWORK dispatch: {e}")

    with job_tab2:
        try:
            active_jobs = supabase.table("jobwork_records").select("*").neq("status", "CANCELLED").neq("status", "COMPLETED").order("jobwork_date", desc=True).limit(500).execute().data or []
        except Exception:
            active_jobs = []
        if not active_jobs:
            st.info("No active JOBWORK challans are awaiting return.")
        elif not jobwork_item_options:
            st.warning("Create stock items first.")
        else:
            job_options = {}
            for j in active_jobs:
                s = jobwork_summary(j["id"])
                job_options[f'{j.get("challan_no")} | {j.get("jobwork_date")} | Pending {s["pending_weight"]:,.2f} KG'] = j
            selected_job_label = st.selectbox("Select JOBWORK Challan", list(job_options), key="jobwork_receive_select")
            selected_job = job_options[selected_job_label]
            selected_summary = jobwork_summary(selected_job["id"])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sent KG", f'{selected_summary["sent_weight"]:,.2f}')
            c2.metric("Returned KG", f'{selected_summary["returned_weight"]:,.2f}')
            c3.metric("Waste KG", f'{selected_summary["waste_weight"]:,.2f}')
            c4.metric("Pending KG", f'{selected_summary["pending_weight"]:,.2f}')

            with st.form("jobwork_receive_form", clear_on_submit=False):
                r1, r2, r3 = st.columns(3)
                return_date = r1.date_input("Return Date", value=date.today())
                output_item_label = r2.selectbox("Finished / Returned Material", list(jobwork_item_options), key="jobwork_output_item")
                output_item = jobwork_item_options[output_item_label]
                output_qty = r3.number_input(f"Returned Quantity ({output_item['unit']})", min_value=0.0, step=1.0, key="jobwork_output_qty")
                r4, r5, r6 = st.columns(3)
                output_weight = r4.number_input("Returned Weight (KG)", min_value=0.0, step=1.0, key="jobwork_output_weight")
                waste_qty = r5.number_input("Waste Quantity", min_value=0.0, step=1.0, value=float(selected_job.get("waste_quantity") or 0), key="jobwork_waste_qty")
                waste_weight = r6.number_input("Waste Weight (KG)", min_value=0.0, step=1.0, value=float(selected_job.get("waste_weight_kg") or 0), key="jobwork_waste_weight")
                waste_notes = st.text_area("Waste / Process Loss Notes", value=selected_job.get("waste_notes") or "", key="jobwork_waste_notes")
                receive_notes = st.text_area("Return Notes", key="jobwork_return_notes")
                save_job_receive = st.form_submit_button("📥 Receive Material from JOBWORK", type="primary", use_container_width=True)

            if save_job_receive:
                if output_qty <= 0 or output_weight <= 0:
                    st.error("Returned quantity and weight must be greater than zero.")
                elif output_weight + float(waste_weight) > selected_summary["sent_weight"] + 0.01:
                    st.error("Returned weight plus waste cannot exceed the material sent to JOBWORK.")
                else:
                    try:
                        supabase.table("jobwork_records").update({
                            "waste_quantity": waste_qty,
                            "waste_weight_kg": waste_weight,
                            "waste_notes": waste_notes.strip() or None
                        }).eq("id", selected_job["id"]).execute()
                        supabase.table("stock_movements").insert({
                            "movement_date": return_date.isoformat(),
                            "item_id": output_item["id"],
                            "party_id": selected_job["party_id"],
                            "direction": "IN",
                            "movement_type": "JOBWORK_IN",
                            "quantity": output_qty,
                            "bags": 0,
                            "weight_kg": output_weight,
                            "rate_per_kg": 0,
                            "transportation": 0,
                            "billing_amount": 0,
                            "reference_no": selected_job["challan_no"],
                            "vehicle_no": None,
                            "handled_by": None,
                            "notes": receive_notes.strip() or None,
                            "entered_by": str(user.id),
                            "duplicate_fingerprint": fp(return_date, output_item["id"], selected_job["party_id"], "JOBWORK_IN", output_qty, output_weight, selected_job["challan_no"]),
                            "purchase_status": "NOT_APPLICABLE",
                            "purchase_id": None,
                            "order_id": None,
                            "jobwork_id": selected_job["id"],
                            "legacy_reason": None
                        }).execute()
                        refresh_jobwork_status(selected_job["id"])
                        st.success(f"JOBWORK return recorded against {selected_job['challan_no']}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to record JOBWORK return: {e}")

    with job_tab3:
        job_search = st.text_input("🔎 Search JOBWORK Register", key="jobwork_register_search", placeholder="Challan, party, material, status...")
        try:
            job_rows = supabase.table("jobwork_records").select("*").order("jobwork_date", desc=True).limit(1000).execute().data or []
            job_party_map = {str(x.get("id")): x.get("name") for x in (supabase.table("business_parties").select("id,name").execute().data or [])}
            display_job = []
            for j in job_rows:
                s = jobwork_summary(j["id"])
                items_sent = ", ".join(dict.fromkeys(str((m.get("stock_items") or {}).get("name") or "") for m in s["movements"] if m.get("movement_type") == "JOBWORK_OUT" and (m.get("stock_items") or {}).get("name")))
                items_returned = ", ".join(dict.fromkeys(str((m.get("stock_items") or {}).get("name") or "") for m in s["movements"] if m.get("movement_type") == "JOBWORK_IN" and (m.get("stock_items") or {}).get("name")))
                display_job.append({
                    "Date": j.get("jobwork_date"),
                    "Challan": j.get("challan_no"),
                    "JOBWORK Party": job_party_map.get(str(j.get("party_id"))),
                    "Material Sent": items_sent,
                    "Material Returned": items_returned,
                    "Sent KG": s["sent_weight"],
                    "Returned KG": s["returned_weight"],
                    "Waste KG": s["waste_weight"],
                    "Pending KG": s["pending_weight"],
                    "Status": j.get("status"),
                    "Notes": j.get("notes")
                })
            filtered_job = filter_display_rows(display_job, job_search)
            st.dataframe(filtered_job, use_container_width=True, hide_index=True)
            add_excel_download(filtered_job, "SP_Enterprise_JOBWORK_Register.xlsx", "📊 Download JOBWORK Register (Excel)", "export_jobwork_register", "JOBWORK")
        except Exception as e:
            st.error(f"Unable to load JOBWORK register: {e}")


# ---------------------------------------------------------------------
# ACCOUNTS
# ---------------------------------------------------------------------

elif page == "Accounts":

    st.title("💰 Accounts")

    st.caption(
        "Central accounting control for S.P. Enterprise. "
        "Manage the Chart of Accounts, Sales, Purchases, Expenses, "
        "Receipts, Payments and other accounting records from one system."
    )

    st.markdown('<div class="section-label">Account Transaction Search</div>', unsafe_allow_html=True)
    account_challan_search = st.text_input(
        "🔎 Search all transactions by Challan / Reference / Invoice / Order",
        key="accounts_global_search",
        placeholder="Enter challan/reference number..."
    )
    if account_challan_search.strip():
        account_search_results = global_search(account_challan_search)
        if account_search_results:
            for section_name, section_rows in account_search_results.items():
                st.markdown(f"**{section_name}**")
                st.dataframe(section_rows, use_container_width=True, hide_index=True)
        else:
            st.warning("No transaction found for that challan/reference.")

    # ================================================================
    # ACCOUNTING NAVIGATION
    # ================================================================

    account_tab1, account_tab2, account_tab3, account_tab4 = st.tabs([
        "📚 Chart of Accounts",
        "🧾 Sales Register",
        "📊 Accounting Registers",
        "📒 Journal Entries"
    ])

    # ================================================================
    # TAB 1 - CHART OF ACCOUNTS
    # ================================================================

    with account_tab1:

        st.subheader("📚 Chart of Accounts")

        st.caption(
            "Create and manage the accounting ledger structure "
            "used throughout the Accounting module."
        )

        # ------------------------------------------------------------
        # LOAD EXISTING ACCOUNTS
        # ------------------------------------------------------------

        try:

            accounts_response = (
                supabase
                .table("chart_of_accounts")
                .select("*")
                .order("account_code")
                .execute()
            )

            accounts = (
                accounts_response.data
                or []
            )

        except Exception as e:

            st.error(
                f"Unable to load Chart of Accounts: {e}"
            )

            accounts = []


        # ------------------------------------------------------------
        # ACCOUNT TYPES
        # ------------------------------------------------------------

        account_types = [
            "ASSET",
            "LIABILITY",
            "EQUITY",
            "INCOME",
            "EXPENSE"
        ]


        # ------------------------------------------------------------
        # CREATE NEW ACCOUNT
        # ------------------------------------------------------------

        st.markdown("### ➕ Create New Account")

        with st.form(
            "create_chart_account_form",
            clear_on_submit=True
        ):

            c1, c2 = st.columns(2)

            account_code = c1.text_input(
                "Account Code",
                placeholder="Example: 1001",
                key="coa_account_code"
            )

            account_name = c2.text_input(
                "Account Name",
                placeholder="Example: Cash in Hand",
                key="coa_account_name"
            )


            c3, c4 = st.columns(2)

            account_type = c3.selectbox(
                "Account Type",
                account_types,
                key="coa_account_type"
            )


            # --------------------------------------------------------
            # PARENT ACCOUNT
            # --------------------------------------------------------

            parent_options = {
                "No Parent Account": None
            }

            for account in accounts:

                if account.get("active", True):

                    label = (
                        f"{account.get('account_code', '')} - "
                        f"{account.get('account_name', '')}"
                    )

                    parent_options[label] = account["id"]


            parent_account_label = c4.selectbox(
                "Parent Account",
                list(parent_options.keys()),
                key="coa_parent_account"
            )

            parent_id = parent_options[
                parent_account_label
            ]


            # --------------------------------------------------------
            # OPENING BALANCE
            # --------------------------------------------------------

            c5, c6, c7 = st.columns(3)

            opening_balance = c5.number_input(
                "Opening Balance",
                min_value=0.0,
                step=0.01,
                key="coa_opening_balance"
            )

            opening_balance_type = c6.selectbox(
                "Opening Balance Type",
                [
                    "DEBIT",
                    "CREDIT"
                ],
                key="coa_opening_balance_type"
            )

            unit_code = c7.text_input(
                "Unit Code",
                placeholder="Example: HO",
                key="coa_unit_code"
            )


            st.caption(
                "Opening balance is optional. Enter 0 if the "
                "account has no opening balance."
            )


            create_account = st.form_submit_button(
                "💾 Create Account",
                use_container_width=True
            )


        # ------------------------------------------------------------
        # SAVE ACCOUNT
        # ------------------------------------------------------------

        if create_account:

            clean_code = account_code.strip()
            clean_name = account_name.strip()
            clean_unit = unit_code.strip()


            if not clean_code:

                st.error(
                    "Account Code is required."
                )


            elif not clean_name:

                st.error(
                    "Account Name is required."
                )


            else:

                # ----------------------------------------------------
                # CHECK DUPLICATE ACCOUNT CODE
                # ----------------------------------------------------

                duplicate_check = (
                    supabase
                    .table("chart_of_accounts")
                    .select("id")
                    .eq("account_code", clean_code)
                    .execute()
                )


                if duplicate_check.data:

                    st.error(
                        f"Account Code '{clean_code}' already exists."
                    )


                else:

                    try:

                        account_data = {

                            "account_code":
                                clean_code,

                            "account_name":
                                clean_name,

                            "account_type":
                                account_type,

                            "parent_id":
                                parent_id,

                            "opening_balance":
                                opening_balance,

                            "opening_balance_type":
                                opening_balance_type,

                            "active":
                                True,

                            "unit_code":
                                clean_unit or None
                        }


                        (
                            supabase
                            .table("chart_of_accounts")
                            .insert(account_data)
                            .execute()
                        )


                        st.success(
                            f"Account '{clean_name}' "
                            f"created successfully."
                        )

                        st.rerun()


                    except Exception as e:

                        st.error(
                            f"Unable to create account: {e}"
                        )


        st.divider()


        # ============================================================
        # ACCOUNT LIST
        # ============================================================

        st.markdown("### 📋 Account List")


        # ------------------------------------------------------------
        # FILTERS
        # ------------------------------------------------------------

        f1, f2, f3 = st.columns(3)


        search_account = f1.text_input(
            "🔎 Search Account",
            placeholder="Code or account name",
            key="coa_search"
        )


        type_filter = f2.selectbox(
            "Account Type",
            [
                "ALL",
                "ASSET",
                "LIABILITY",
                "EQUITY",
                "INCOME",
                "EXPENSE"
            ],
            key="coa_type_filter"
        )


        status_filter = f3.selectbox(
            "Status",
            [
                "ACTIVE",
                "INACTIVE",
                "ALL"
            ],
            key="coa_status_filter"
        )


        # ------------------------------------------------------------
        # FILTER ACCOUNTS
        # ------------------------------------------------------------

        filtered_accounts = []


        for account in accounts:

            code = str(
                account.get("account_code") or ""
            )

            name = str(
                account.get("account_name") or ""
            )

            acc_type = str(
                account.get("account_type") or ""
            )

            active = account.get(
                "active",
                True
            )


            # Search filter

            if search_account.strip():

                search_text = (
                    search_account
                    .strip()
                    .lower()
                )

                if (
                    search_text not in code.lower()
                    and
                    search_text not in name.lower()
                ):

                    continue


            # Account type filter

            if (
                type_filter != "ALL"
                and acc_type != type_filter
            ):

                continue


            # Status filter

            if status_filter == "ACTIVE" and not active:

                continue

            if status_filter == "INACTIVE" and active:

                continue


            filtered_accounts.append(account)


        # ------------------------------------------------------------
        # CREATE PARENT LOOKUP
        # ------------------------------------------------------------

        account_lookup = {}

        for account in accounts:

            account_lookup[
                account["id"]
            ] = (
                f"{account.get('account_code', '')} - "
                f"{account.get('account_name', '')}"
            )


        # ------------------------------------------------------------
        # DISPLAY TABLE
        # ------------------------------------------------------------

        if filtered_accounts:

            display_accounts = []


            for account in filtered_accounts:

                parent_name = "—"

                if account.get("parent_id"):

                    parent_name = account_lookup.get(
                        account["parent_id"],
                        "—"
                    )


                display_accounts.append({

                    "Code":
                        account.get("account_code"),

                    "Account Name":
                        account.get("account_name"),

                    "Type":
                        account.get("account_type"),

                    "Parent Account":
                        parent_name,

                    "Opening Balance":
                        account.get(
                            "opening_balance",
                            0
                        ),

                    "Dr / Cr":
                        account.get(
                            "opening_balance_type",
                            ""
                        ),

                    "Unit":
                        account.get(
                            "unit_code"
                        ) or "—",

                    "Status":
                        "ACTIVE"
                        if account.get("active", True)
                        else "INACTIVE"
                })


            st.dataframe(
                display_accounts,
                use_container_width=True,
                hide_index=True
            )
            add_excel_download(display_accounts, "SP_Enterprise_Chart_of_Accounts.xlsx", "📊 Download Chart of Accounts (Excel)", "export_chart_of_accounts", "Chart of Accounts")


        else:

            st.info(
                "No accounts match the selected filters."
            )


        # ============================================================
        # ACTIVATE / DEACTIVATE ACCOUNT
        # ============================================================

        st.divider()

        st.markdown("### ⚙️ Account Status")


        active_accounts = {

            f"{a.get('account_code', '')} - "
            f"{a.get('account_name', '')}":
                a["id"]

            for a in accounts
        }


        if active_accounts:

            selected_account_label = st.selectbox(
                "Select Account",
                list(active_accounts.keys()),
                key="coa_status_account"
            )

            selected_account_id = active_accounts[
                selected_account_label
            ]


            selected_account = next(
                (
                    a
                    for a in accounts
                    if a["id"] == selected_account_id
                ),
                None
            )


            if selected_account:

                current_status = selected_account.get(
                    "active",
                    True
                )


                if current_status:

                    if st.button(
                        "🔴 Deactivate Account",
                        use_container_width=True,
                        key="deactivate_coa_account"
                    ):

                        try:

                            (
                                supabase
                                .table("chart_of_accounts")
                                .update({
                                    "active": False
                                })
                                .eq(
                                    "id",
                                    selected_account_id
                                )
                                .execute()
                            )

                            st.success(
                                "Account deactivated successfully."
                            )

                            st.rerun()


                        except Exception as e:

                            st.error(
                                f"Unable to deactivate account: {e}"
                            )


                else:

                    if st.button(
                        "🟢 Activate Account",
                        use_container_width=True,
                        key="activate_coa_account"
                    ):

                        try:

                            (
                                supabase
                                .table("chart_of_accounts")
                                .update({
                                    "active": True
                                })
                                .eq(
                                    "id",
                                    selected_account_id
                                )
                                .execute()
                            )

                            st.success(
                                "Account activated successfully."
                            )

                            st.rerun()


                        except Exception as e:

                            st.error(
                                f"Unable to activate account: {e}"
                            )


        else:

            st.info(
                "No accounts available."
            )

        render_delete_control(
            "chart_of_accounts",
            accounts,
            lambda r: f'{r.get("account_code", "")} - {r.get("account_name", "")}',
            "delete_chart_account"
        )

    # ================================================================
    # TAB 2 - SALES REGISTER
    # ================================================================

    with account_tab2:

        st.subheader("🧾 Sales Register")

        st.caption(
            "Record and monitor sales invoices issued by S.P. Enterprise."
        )

        # ------------------------------------------------------------
        # LOAD SALES INVOICES
        # ------------------------------------------------------------

        try:

            sales_invoices = (
                supabase
                .table("sales_invoices")
                .select("*")
                .order("invoice_date", desc=True)
                .limit(2000)
                .execute()
                .data
            )

        except Exception as e:

            st.error("Unable to load Sales Register.")
            st.code(str(e))

            sales_invoices = []

        # ------------------------------------------------------------
        # SALES SUMMARY
        # ------------------------------------------------------------

        total_sales = sum(
            float(x.get("total_amount") or 0)
            for x in sales_invoices
            if x.get("payment_status") != "CANCELLED"
        )

        total_received = sum(
            float(x.get("amount_received") or 0)
            for x in sales_invoices
            if x.get("payment_status") != "CANCELLED"
        )

        total_outstanding = sum(
            float(x.get("balance_amount") or 0)
            for x in sales_invoices
            if x.get("payment_status") != "CANCELLED"
        )

        unpaid_count = sum(
            1
            for x in sales_invoices
            if x.get("payment_status") == "UNPAID"
        )

        s1, s2, s3, s4 = st.columns(4)

        s1.metric(
            "Total Sales",
            f"₹{total_sales:,.2f}"
        )

        s2.metric(
            "Amount Received",
            f"₹{total_received:,.2f}"
        )

        s3.metric(
            "Outstanding",
            f"₹{total_outstanding:,.2f}"
        )

        s4.metric(
            "Unpaid Invoices",
            unpaid_count
        )

        st.divider()

        # ------------------------------------------------------------
        # SALES REGISTER TABLE
        # ------------------------------------------------------------

        register_rows = []

        for invoice in sales_invoices:

            register_rows.append({

                "Invoice No.": invoice.get(
                    "invoice_number"
                ),

                "Date": invoice.get(
                    "invoice_date"
                ),

                "Customer": invoice.get(
                    "customer_name"
                ),

                "Type": invoice.get(
                    "invoice_type"
                ),

                "Subtotal": invoice.get(
                    "subtotal"
                ),

                "CGST": invoice.get(
                    "cgst_amount"
                ),

                "SGST": invoice.get(
                    "sgst_amount"
                ),

                "IGST": invoice.get(
                    "igst_amount"
                ),

                "Total": invoice.get(
                    "total_amount"
                ),

                "Received": invoice.get(
                    "amount_received"
                ),

                "Balance": invoice.get(
                    "balance_amount"
                ),

                "Status": invoice.get(
                    "payment_status"
                ),

                "Due Date": invoice.get(
                    "due_date"
                )
            })

        sales_search = st.text_input("🔎 Search Sales Register", key="sales_register_search", placeholder="Invoice, customer, challan/reference, status...")
        filtered_sales_rows = filter_display_rows(register_rows, sales_search)
        st.dataframe(
            filtered_sales_rows,
            use_container_width=True,
            hide_index=True
        )
        add_excel_download(filtered_sales_rows, "SP_Enterprise_Sales_Register.xlsx", "📊 Download Sales Register (Excel)", "export_sales_register", "Sales Register")

        render_delete_control(
            "sales_invoices",
            sales_invoices,
            lambda r: f'{r.get("invoice_number", "Invoice")} | {r.get("invoice_date", "")} | {r.get("customer_name", "")}',
            "delete_sales_invoice",
            transaction=True
        )

        st.divider()

        # ------------------------------------------------------------
        # STOCK DISPATCHES AWAITING SALES INVOICE
        # ------------------------------------------------------------
        try:
            pending_dispatches = (
                supabase.table("stock_movements")
                .select("id,movement_date,party_id,reference_no,quantity,bags,weight_kg,rate_per_kg,billing_amount,stock_items(name,unit),business_parties(name)")
                .eq("direction", "OUT")
                .order("movement_date", desc=True)
                .limit(200)
                .execute().data or []
            )
            existing_invoice_refs = {str(x.get("invoice_number")) for x in sales_invoices}
            pending_dispatches = [x for x in pending_dispatches if str(x.get("reference_no")) not in existing_invoice_refs]
        except Exception:
            pending_dispatches = []

        if pending_dispatches:
            st.markdown('<div class="section-label">Stock dispatches awaiting invoice</div>', unsafe_allow_html=True)
            st.info("Dispatches are already recorded in Stock Control. Use the reference below as the invoice number; the customer, item, quantity, rate and billing value are already available to Accounts.")
            pending_display = []
            for d in pending_dispatches:
                item = d.get("stock_items") or {}
                party = d.get("business_parties") or {}
                pending_display.append({
                    "Date": d.get("movement_date"),
                    "Dispatch Ref": d.get("reference_no"),
                    "Customer": party.get("name"),
                    "Item": item.get("name"),
                    "Qty": d.get("quantity"),
                    "Weight KG": d.get("weight_kg"),
                    "Rate/KG": d.get("rate_per_kg"),
                    "Billing ₹": d.get("billing_amount")
                })
            pending_dispatch_search = st.text_input("🔎 Search Dispatches Awaiting Invoice", key="pending_dispatch_search", placeholder="Challan, customer, item...")
            pending_display = filter_display_rows(pending_display, pending_dispatch_search)
            st.dataframe(pending_display, use_container_width=True, hide_index=True)

        # ------------------------------------------------------------
        # ADDED: SALES INVOICE PDF
        # ------------------------------------------------------------
        if sales_invoices:
            st.markdown('<div class="section-label">Sales Invoice PDF</div>', unsafe_allow_html=True)
            pdf_options = {
                f'{x.get("invoice_number", "Invoice")} | {x.get("invoice_date", "")} | {x.get("customer_name", "")}': x
                for x in sales_invoices if x.get("id")
            }
            if pdf_options:
                selected_pdf_label = st.selectbox("Select saved invoice", list(pdf_options.keys()), key="sales_pdf_invoice")
                selected_pdf_invoice = pdf_options[selected_pdf_label]
                try:
                    selected_items = (
                        supabase.table("sales_invoice_items")
                        .select("*")
                        .eq("sales_invoice_id", selected_pdf_invoice["id"])
                        .order("id")
                        .execute().data or []
                    )
                    pdf_bytes = invoice_to_pdf_bytes(selected_pdf_invoice, selected_items)
                    st.download_button(
                        "🧾 Download Invoice PDF",
                        data=pdf_bytes,
                        file_name=f'SP_Enterprise_{selected_pdf_invoice.get("invoice_number") or "Invoice"}.pdf',
                        mime="application/pdf",
                        key="download_sales_invoice_pdf"
                    )
                except Exception as e:
                    st.error("Unable to generate invoice PDF.")
                    st.code(str(e))

        # ------------------------------------------------------------
        # CREATE SALES INVOICE
        # ------------------------------------------------------------

        with st.expander("➕ Create Sales Invoice"):

            st.subheader("New Sales Invoice")

            dispatch_source_options = {
                "Manual Sales Invoice": None,
                **{
                    f'{d.get("movement_date")} | {((d.get("business_parties") or {}).get("name") or "Customer")} | {d.get("reference_no") or "No Ref"}': d
                    for d in pending_dispatches
                }
            }
            dispatch_source_label = st.selectbox(
                "Sales Source",
                list(dispatch_source_options.keys()),
                key="sales_source_dispatch"
            )
            source_dispatch = dispatch_source_options[dispatch_source_label]
            if source_dispatch:
                source_item = source_dispatch.get("stock_items") or {}
                source_party = source_dispatch.get("business_parties") or {}
                st.session_state["sales_invoice_number"] = str(source_dispatch.get("reference_no") or "")
                st.session_state["sales_invoice_date"] = date.fromisoformat(str(source_dispatch.get("movement_date")))
                st.session_state["sales_customer"] = next((f'{p.get("name") or ""} [{p.get("party_type") or ""}]' for p in parties if p.get("id") == source_dispatch.get("party_id")), "Manual Customer")
                st.session_state["sales_customer_name"] = str(source_party.get("name") or "")
                st.session_state["sales_quantity"] = float(source_dispatch.get("quantity") or 0)
                st.session_state["sales_rate"] = float(source_dispatch.get("rate_per_kg") or 0)
                st.session_state["sales_dispatch_weight"] = float(source_dispatch.get("weight_kg") or 0)
                st.session_state["sales_description"] = str(source_item.get("name") or "")

            c1, c2, c3 = st.columns(3)

            invoice_number = c1.text_input(
                "Invoice Number",
                placeholder="Example: INV-001",
                key="sales_invoice_number"
            )

            invoice_date = c2.date_input(
                "Invoice Date",
                date.today(),
                key="sales_invoice_date"
            )

            invoice_type = c3.selectbox(
                "Invoice Type",
                [
                    "TAX_INVOICE",
                    "BILL_OF_SUPPLY",
                    "EXPORT",
                    "OTHER"
                ],
                key="sales_invoice_type"
            )

            # --------------------------------------------------------
            # CUSTOMER
            # --------------------------------------------------------

            st.divider()

            st.subheader("Customer Details")

            # --------------------------------------------------------
            # LOAD PARTIES / CUSTOMERS
            # --------------------------------------------------------

            try:
                parties_response = (
                    supabase
                    .table("business_parties")
                    .select("*")
                    .order("name")
                    .execute()
                )

                parties = parties_response.data or []

            except Exception as e:
                parties = []
                st.warning(f"Could not load customers: {e}")

            customer_options = {
                "Manual Customer": None
            }

            for party in parties:

                party_id = party.get("id")

                if party_id:

                    label = (
                        f'{party.get("name") or ""} '
                        f'[{party.get("party_type") or ""}]'
                    )

                    customer_options[label] = party_id

            selected_customer = st.selectbox(
                "Customer / Party",
                list(customer_options),
                key="sales_customer"
            )

            selected_customer_id = customer_options[
                selected_customer
            ]

            if selected_customer_id:

                selected_party = next(
                    (
                        p for p in parties
                        if p.get("id") == selected_customer_id
                    ),
                    None
                )

                customer_name = st.text_input(
                    "Customer Name",
                    value=selected_party.get("name")
                    if selected_party else "",
                    key="sales_customer_name"
                )

            else:

                customer_name = st.text_input(
                    "Customer Name",
                    key="sales_manual_customer"
                )

            # --------------------------------------------------------
            # INVOICE ITEM
            # --------------------------------------------------------

            st.divider()

            st.subheader("Invoice Item")

            # --------------------------------------------------------
            # LOAD STOCK ITEMS
            # --------------------------------------------------------

            try:
                items_response = (
                    supabase
                    .table("stock_items")
                    .select("*")
                    .order("name")
                    .execute()
                )

                items = items_response.data or []

            except Exception as e:
                items = []
                st.warning(f"Could not load stock items: {e}")

            sales_item_options = {
                f'{x["name"]} ({x["unit"]})': x
                for x in items
            }

            if sales_item_options:

                if source_dispatch:
                    source_item_name = (source_dispatch.get("stock_items") or {}).get("name")
                    source_item_unit = (source_dispatch.get("stock_items") or {}).get("unit")
                    source_item_label = f"{source_item_name} ({source_item_unit})"
                    if source_item_label in sales_item_options:
                        st.session_state["sales_stock_item"] = source_item_label

                selected_sales_item = st.selectbox(
                    "Stock Item",
                    list(sales_item_options),
                    key="sales_stock_item"
                )

                selected_item = sales_item_options[
                    selected_sales_item
                ]

                description = st.text_input(
                    "Description",
                    value=selected_item["name"],
                    key="sales_description"
                )

                c1, c2, c3 = st.columns(3)

                sales_quantity = c1.number_input(
                    "Quantity",
                    min_value=0.001,
                    step=1.0,
                    key="sales_quantity"
                )

                sales_rate = c2.number_input(
                    "Rate",
                    min_value=0.0,
                    step=1.0,
                    key="sales_rate"
                )

                sales_discount_percent = c3.number_input(
                    "Discount %",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.50,
                    key="sales_discount"
                )

                dispatch_weight = st.number_input(
                    "Dispatch Weight (KG)",
                    min_value=0.0,
                    step=0.01,
                    help="Required for weighted stock. For KG items it defaults to the sale quantity.",
                    key="sales_dispatch_weight"
                )

                # ----------------------------------------------------
                # GST
                # ----------------------------------------------------

                c1, c2 = st.columns(2)

                gst_rate = c1.number_input(
                    "GST Rate %",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key="sales_gst"
                )

                tax_type = c2.selectbox(
                    "GST Treatment",
                    [
                        "CGST + SGST",
                        "IGST",
                        "No GST"
                    ],
                    key="sales_tax_type"
                )

                # ----------------------------------------------------
                # CALCULATIONS
                # ----------------------------------------------------

                gross_amount = (
                    sales_quantity * sales_rate
                )

                discount_amount = (
                    gross_amount
                    * sales_discount_percent
                    / 100
                )

                taxable_amount = (
                    gross_amount
                    - discount_amount
                )

                cgst_amount = 0.0
                sgst_amount = 0.0
                igst_amount = 0.0

                if tax_type == "CGST + SGST":

                    cgst_amount = (
                        taxable_amount
                        * gst_rate
                        / 200
                    )

                    sgst_amount = (
                        taxable_amount
                        * gst_rate
                        / 200
                    )

                elif tax_type == "IGST":

                    igst_amount = (
                        taxable_amount
                        * gst_rate
                        / 100
                    )

                line_total = (
                    taxable_amount
                    + cgst_amount
                    + sgst_amount
                    + igst_amount
                )

                # ----------------------------------------------------
                # INVOICE TOTAL
                # ----------------------------------------------------

                st.divider()

                st.subheader("Invoice Calculation")

                a, b, c, d = st.columns(4)

                a.metric(
                    "Gross",
                    f"₹{gross_amount:,.2f}"
                )

                b.metric(
                    "Discount",
                    f"₹{discount_amount:,.2f}"
                )

                c.metric(
                    "Taxable",
                    f"₹{taxable_amount:,.2f}"
                )

                d.metric(
                    "Invoice Total",
                    f"₹{line_total:,.2f}"
                )

                # ----------------------------------------------------
                # PAYMENT
                # ----------------------------------------------------

                st.divider()

                c1, c2 = st.columns(2)

                amount_received = c1.number_input(
                    "Amount Received",
                    min_value=0.0,
                    max_value=max(line_total, 0.0),
                    step=100.0,
                    key="sales_amount_received"
                )

                due_date = c2.date_input(
                    "Due Date",
                    invoice_date,
                    key="sales_due_date"
                )

                balance_amount = (
                    line_total - amount_received
                )

                if amount_received <= 0:

                    payment_status = "UNPAID"

                elif amount_received < line_total:

                    payment_status = "PARTIAL"

                else:

                    payment_status = "PAID"

                st.metric(
                    "Outstanding Balance",
                    f"₹{balance_amount:,.2f}"
                )

                notes = st.text_area(
                    "Notes",
                    key="sales_notes"
                )

                # ----------------------------------------------------
                # SAVE INVOICE
                # ----------------------------------------------------

                save_invoice = st.button(
                    "💾 Save Sales Invoice",
                    type="primary",
                    use_container_width=True,
                    key="save_sales_invoice"
                )

                if save_invoice:

                    if not invoice_number.strip():

                        st.error(
                            "Invoice number is required."
                        )

                    elif not customer_name.strip():

                        st.error(
                            "Customer name is required."
                        )

                    elif sales_quantity <= 0:

                        st.error(
                            "Quantity must be greater than zero."
                        )

                    else:

                        invoice_data = {

                            "invoice_number":
                                invoice_number.strip(),

                            "invoice_date":
                                str(invoice_date),

                            "customer_id":
                                selected_customer_id,

                            "customer_name":
                                customer_name.strip(),

                            "invoice_type":
                                invoice_type,

                            "payment_status":
                                payment_status,

                            "subtotal":
                                taxable_amount,

                            "discount_amount":
                                discount_amount,

                            "cgst_amount":
                                cgst_amount,

                            "sgst_amount":
                                sgst_amount,

                            "igst_amount":
                                igst_amount,

                            "round_off":
                                0,

                            "total_amount":
                                line_total,

                            "amount_received":
                                amount_received,

                            "balance_amount":
                                balance_amount,

                            "due_date":
                                str(due_date),

                            "notes":
                                notes.strip() or None
                        }

                        try:

                            invoice_response = (
                                supabase
                                .table("sales_invoices")
                                .insert(invoice_data)
                                .execute()
                            )

                            created_invoice = (
                                invoice_response.data[0]
                            )

                            invoice_item_data = {

                                "sales_invoice_id":
                                    created_invoice["id"],

                                "stock_item_id":
                                    selected_item["id"],

                                "description":
                                    description.strip(),

                                "quantity":
                                    sales_quantity,

                                "unit":
                                    selected_item["unit"],

                                "rate":
                                    sales_rate,

                                "discount_percent":
                                    sales_discount_percent,

                                "discount_amount":
                                    discount_amount,

                                "taxable_amount":
                                    taxable_amount,

                                "gst_rate":
                                    gst_rate,

                                "cgst_amount":
                                    cgst_amount,

                                "sgst_amount":
                                    sgst_amount,

                                "igst_amount":
                                    igst_amount,

                                "line_total":
                                    line_total
                            }

                            (
                                supabase
                                .table("sales_invoice_items")
                                .insert(invoice_item_data)
                                .execute()
                            )

                            # ------------------------------------------------
                            # STOCK DISPATCH + ACCOUNTING POSTING
                            # ------------------------------------------------
                            if not selected_customer_id:
                                raise Exception("A registered customer/party is required for an integrated stock sale.")

                            _, _, available_qty, _, _, available_weight = stock_balance(selected_item["id"])
                            dispatch_weight = float(st.session_state.get("sales_dispatch_weight", 0) or 0)
                            if dispatch_weight <= 0:
                                dispatch_weight = sales_quantity if str(selected_item.get("unit", "")).upper() == "KG" else 0

                            if sales_quantity > available_qty + 1e-9:
                                raise Exception(f"Insufficient stock quantity. Available: {available_qty:g} {selected_item.get('unit')}")
                            if dispatch_weight > 0 and available_weight > 0 and dispatch_weight > available_weight + 1e-9:
                                raise Exception(f"Insufficient stock weight. Available: {available_weight:,.2f} KG")

                            movement_fingerprint = fp(invoice_number, selected_item["id"], selected_customer_id, "OUT", sales_quantity, dispatch_weight)
                            supabase.table("stock_movements").insert({
                                "movement_date": str(invoice_date),
                                "item_id": selected_item["id"],
                                "party_id": selected_customer_id,
                                "direction": "OUT",
                                "quantity": sales_quantity,
                                "bags": 0,
                                "weight_kg": dispatch_weight,
                                "rate_per_kg": sales_rate,
                                "transportation": 0,
                                "billing_amount": taxable_amount,
                                "reference_no": invoice_number.strip(),
                                "vehicle_no": None,
                                "handled_by": None,
                                "notes": "Auto-created from Sales Invoice",
                                "entered_by": str(user.id),
                                "duplicate_fingerprint": movement_fingerprint
                            }).execute()

                            sales_account_id = find_account_id(accounts, ["sales revenue", "sales"], ["INCOME"])
                            receivable_account_id = find_account_id(accounts, ["receivable", "debtor", "customer"], ["ASSET"])
                            if not sales_account_id or not receivable_account_id:
                                raise Exception("Sales Revenue and Customer Receivables ledgers are required before posting an integrated sale.")

                            journal_lines = [
                                {"account_id": receivable_account_id, "party_id": selected_customer_id, "debit": line_total, "credit": 0, "narration": f"Sales Invoice {invoice_number.strip()}"},
                                {"account_id": sales_account_id, "party_id": selected_customer_id, "debit": 0, "credit": taxable_amount, "narration": f"Sales Invoice {invoice_number.strip()}"}
                            ]
                            if cgst_amount > 0:
                                tax_id = find_account_id(accounts, ["output cgst", "cgst"], ["LIABILITY"])
                                if tax_id:
                                    journal_lines.append({"account_id": tax_id, "party_id": selected_customer_id, "debit": 0, "credit": cgst_amount, "narration": f"CGST {invoice_number.strip()}"})
                            if sgst_amount > 0:
                                tax_id = find_account_id(accounts, ["output sgst", "sgst"], ["LIABILITY"])
                                if tax_id:
                                    journal_lines.append({"account_id": tax_id, "party_id": selected_customer_id, "debit": 0, "credit": sgst_amount, "narration": f"SGST {invoice_number.strip()}"})
                            if igst_amount > 0:
                                tax_id = find_account_id(accounts, ["output igst", "igst"], ["LIABILITY"])
                                if tax_id:
                                    journal_lines.append({"account_id": tax_id, "party_id": selected_customer_id, "debit": 0, "credit": igst_amount, "narration": f"IGST {invoice_number.strip()}"})

                            journal_number = create_journal_entry(invoice_date, "SALES", "SALES", created_invoice["id"], f"Sales Invoice {invoice_number.strip()}", journal_lines, user.id)
                            journal_row = (
                                supabase.table("journal_entries")
                                .select("id")
                                .eq("entry_no", journal_number)
                                .limit(1)
                                .execute().data
                                or []
                            )
                            if journal_row:
                                supabase.table("sales_invoices").update({
                                    "journal_entry_id": journal_row[0]["id"]
                                }).eq("id", created_invoice["id"]).execute()

                            st.success(
                                f"Sales Invoice {invoice_number.strip()} created, stock dispatched and Journal {journal_number} posted."
                            )

                            st.rerun()

                        except Exception as e:

                            error_text = str(e).lower()

                            if (
                                "duplicate" in error_text
                                or "unique" in error_text
                            ):

                                st.error(
                                    "This invoice number already exists."
                                )

                            else:

                                st.error(
                                    "Unable to save sales invoice."
                                )

                                st.code(str(e))

            else:

                st.warning(
                    "No stock items are available. "
                    "Add stock items in Stock Control first."
                )




    # ================================================================
    # TAB 3 - ACCOUNTING REGISTERS
    # ================================================================

    with account_tab3:

        st.subheader("📊 Accounting Registers")

        st.caption(
            "Record and review purchases, expenses, receipts, payments "
            "and cash / bank accounts."
        )

        # ------------------------------------------------------------
        # LOAD CHART OF ACCOUNTS
        # ------------------------------------------------------------

        try:
            coa_response = (
                supabase
                .table("chart_of_accounts")
                .select("*")
                .eq("active", True)
                .order("account_code")
                .execute()
            )

            chart_accounts = coa_response.data or []

        except Exception as e:
            chart_accounts = []
            st.warning(f"Could not load Chart of Accounts: {e}")

        account_options = {
            f'{a.get("account_code", "")} - '
            f'{a.get("account_name", "")}': a.get("id")
            for a in chart_accounts
            if a.get("id")
        }

        # ------------------------------------------------------------
        # LOAD CASH / BANK ACCOUNTS
        # ------------------------------------------------------------

        try:
            bank_response = (
                supabase
                .table("cash_bank_accounts")
                .select("*")
                .eq("active", True)
                .order("account_name")
                .execute()
            )

            cash_bank_accounts = bank_response.data or []

        except Exception as e:
            cash_bank_accounts = []
            st.warning(f"Could not load Cash / Bank accounts: {e}")

        bank_options = {
            f'{b.get("account_name", "")} '
            f'({b.get("account_type", "")})': b.get("id")
            for b in cash_bank_accounts
            if b.get("id")
        }

        # ------------------------------------------------------------
        # REGISTER TABS
        # ------------------------------------------------------------

        reg1, reg2, reg3, reg4, reg5 = st.tabs([
            "🛒 Purchases",
            "💸 Expenses",
            "💰 Receipts",
            "💳 Payments",
            "🏦 Cash / Bank"
        ])

        # ============================================================
        # PURCHASES
        # ============================================================

        with reg1:

            st.subheader("🛒 Purchase Register")
            st.caption("Confirm supplier purchases from Stock Receiving. Data already captured in Stock Control is reused automatically.")

            try:
                pending_receipts = (
                    supabase.table("stock_movements")
                    .select("id,movement_date,party_id,reference_no,quantity,bags,weight_kg,rate_per_kg,transportation,billing_amount,stock_items(name,unit),business_parties(name)")
                    .eq("direction", "IN")
                    .eq("purchase_status", "PENDING")
                    .order("movement_date", desc=True)
                    .limit(200)
                    .execute().data or []
                )
            except Exception:
                # Older databases may not yet have the integration columns.
                pending_receipts = []

            if pending_receipts:
                pending_purchase_search = st.text_input("🔎 Search Pending Stock Receipts", key="pending_purchase_receipts_search", placeholder="Supplier, item, challan...")
                if pending_purchase_search.strip():
                    pending_receipts = [
                        r for r in pending_receipts
                        if pending_purchase_search.strip().lower() in " ".join(str((r.get(k) or "")) for k in ["movement_date", "reference_no", "quantity", "weight_kg"]).lower()
                        or pending_purchase_search.strip().lower() in str((r.get("stock_items") or {}).get("name") or "").lower()
                        or pending_purchase_search.strip().lower() in str((r.get("business_parties") or {}).get("name") or "").lower()
                    ]
                receipt_options = {}
                for r in pending_receipts:
                    item = r.get("stock_items") or {}
                    party = r.get("business_parties") or {}
                    label = f'{r.get("movement_date")} | {party.get("name") or "Unknown Supplier"} | {item.get("name") or "Item"} | {r.get("weight_kg") or 0:g} KG | {r.get("reference_no") or "No Ref"}'
                    receipt_options[label] = r

                st.markdown('<div class="section-label">Pending stock receipts</div>', unsafe_allow_html=True)
                selected_receipt_label = st.selectbox("Select a Stock Receipt to convert into a Purchase", list(receipt_options.keys()), key="purchase_stock_receipt")
                selected_receipt = receipt_options[selected_receipt_label]
                selected_item = selected_receipt.get("stock_items") or {}
                selected_party = selected_receipt.get("business_parties") or {}
                material_value = float(selected_receipt.get("billing_amount") or 0)
                transport_value = float(selected_receipt.get("transportation") or 0)
                suggested_total = material_value + transport_value

                a, b, c, d = st.columns(4)
                a.metric("Supplier", selected_party.get("name") or "—")
                b.metric("Item", selected_item.get("name") or "—")
                c.metric("Weight", f'{float(selected_receipt.get("weight_kg") or 0):,.2f} KG')
                d.metric("Stock Value", f'₹{suggested_total:,.2f}')

                with st.form("purchase_from_stock_form", clear_on_submit=True):
                    p1, p2, p3 = st.columns(3)
                    bill_no = p1.text_input("Supplier Bill No.", value=str(selected_receipt.get("reference_no") or ""), key="purchase_bill_no_integrated")
                    bill_date = p2.date_input("Bill Date", value=date.fromisoformat(str(selected_receipt.get("movement_date"))), key="purchase_bill_date_integrated")
                    supplier = p3.text_input("Supplier", value=str(selected_party.get("name") or ""), key="purchase_supplier_integrated")

                    p4, p5, p6 = st.columns(3)
                    gstin = p4.text_input("Supplier GSTIN", value=str(selected_party.get("gstin") or ""), key="purchase_gstin_integrated")
                    taxable_value = p5.number_input("Taxable Value", min_value=0.0, value=material_value + transport_value, step=0.01, key="purchase_taxable_integrated")
                    gst_amount = p6.number_input("GST Amount", min_value=0.0, step=0.01, key="purchase_gst_integrated")
                    bill_total = st.number_input("Bill Total", min_value=0.0, value=material_value + transport_value, step=0.01, key="purchase_total_integrated")

                    purchase_account_id = find_account_id(chart_accounts, ["purchase", "inventory", "stock"], ["EXPENSE", "ASSET"])
                    payable_account_id = find_account_id(chart_accounts, ["payable", "creditor", "supplier"], ["LIABILITY"])
                    account_map = {f'{a.get("account_code", "")} - {a.get("account_name", "")}': a.get("id") for a in chart_accounts if a.get("id")}
                    purchase_account_label = st.selectbox("Purchase / Inventory Ledger", list(account_map.keys()), index=max(0, next((i for i,k in enumerate(account_map) if account_map[k] == purchase_account_id), 0)), key="purchase_debit_account") if account_map else None
                    payable_account_label = st.selectbox("Supplier Payable Ledger", list(account_map.keys()), index=max(0, next((i for i,k in enumerate(account_map) if account_map[k] == payable_account_id), 0)), key="purchase_credit_account") if account_map else None

                    save_purchase = st.form_submit_button("✅ Confirm Purchase & Post Accounts", type="primary", use_container_width=True)

                if save_purchase:
                    if not bill_no.strip() or not supplier.strip():
                        st.error("Supplier Bill No. and Supplier are required.")
                    elif bill_total <= 0:
                        st.error("Bill total must be greater than zero.")
                    elif not purchase_account_label or not payable_account_label:
                        st.error("Create Purchase/Inventory and Supplier Payable ledgers in Chart of Accounts first.")
                    else:
                        try:
                            purchase_response = supabase.table("accounts_purchases").insert({
                                "bill_no": bill_no.strip(),
                                "bill_date": bill_date.isoformat(),
                                "supplier": supplier.strip(),
                                "gstin": gstin.strip() or None,
                                "taxable_value": taxable_value,
                                "gst_amount": gst_amount,
                                "bill_total": bill_total,
                                "entered_by": str(user.id),
                                "stock_movement_id": selected_receipt["id"],
                                "party_id": selected_receipt.get("party_id")
                            }).execute()
                            purchase_id = purchase_response.data[0]["id"]

                            debit_id = account_map[purchase_account_label]
                            credit_id = account_map[payable_account_label]
                            lines = [
                                {"account_id": debit_id, "party_id": selected_receipt.get("party_id"), "debit": taxable_value, "credit": 0, "narration": f"Purchase {bill_no.strip()}"},
                                {"account_id": credit_id, "party_id": selected_receipt.get("party_id"), "debit": 0, "credit": bill_total, "narration": f"Purchase {bill_no.strip()}"}
                            ]
                            if gst_amount > 0:
                                input_gst_id = find_account_id(chart_accounts, ["input gst", "input tax", "gst input"], ["ASSET"])
                                if input_gst_id:
                                    lines[0]["debit"] = max(taxable_value - gst_amount, 0)
                                    lines.insert(1, {"account_id": input_gst_id, "party_id": selected_receipt.get("party_id"), "debit": gst_amount, "credit": 0, "narration": f"Input GST {bill_no.strip()}"})
                            journal_number = create_journal_entry(bill_date, "PURCHASE", "PURCHASE", purchase_id, f"Purchase {bill_no.strip()}", lines, user.id)
                            supabase.table("stock_movements").update({"purchase_status": "POSTED", "purchase_id": purchase_id}).eq("id", selected_receipt["id"]).execute()
                            st.success(f"Purchase confirmed. Journal {journal_number} posted and Stock Receipt linked.")
                            st.rerun()
                        except Exception as e:
                            st.error("Unable to confirm purchase.")
                            st.code(str(e))
            else:
                st.info("No pending Stock Receipts. Receive stock in Stock Control first; eligible receipts will appear here automatically.")

            st.divider()
            st.markdown("### 📋 Purchase History")
            try:
                purchases = supabase.table("accounts_purchases").select("*").order("bill_date", desc=True).limit(100).execute().data or []
                if purchases:
                    purchase_search = st.text_input("🔎 Search Purchases", key="purchase_register_search", placeholder="Bill no., supplier, GSTIN...")
                    filtered_purchases = filter_display_rows(purchases, purchase_search)
                    st.dataframe(filtered_purchases, use_container_width=True, hide_index=True)
                    add_excel_download(filtered_purchases, "SP_Enterprise_Purchases.xlsx", "📊 Download Purchases (Excel)", "export_purchases", "Purchases")
                    render_delete_control(
                        "accounts_purchases",
                        purchases,
                        lambda r: f'{r.get("bill_no", "Purchase")} | {r.get("bill_date", "")} | {r.get("supplier", "")}',
                        "delete_purchase",
                        transaction=True
                    )
                else:
                    st.info("No purchase records yet.")
            except Exception as e:
                st.error(f"Unable to load purchases: {e}")


            # ============================================================
            # EXPENSES
            # ============================================================

            with reg2:

                st.subheader("💸 Expense Register")
                st.caption("Record operating expenses once and post the corresponding double-entry automatically.")

                expense_accounts = {
                    f'{a.get("account_code", "")} - {a.get("account_name", "")}': a.get("id")
                    for a in chart_accounts
                    if str(a.get("account_type", "")).upper() == "EXPENSE" and a.get("id")
                }
                settlement_accounts = {
                    f'{a.get("account_code", "")} - {a.get("account_name", "")}': a.get("id")
                    for a in chart_accounts
                    if str(a.get("account_type", "")).upper() in {"ASSET", "LIABILITY"} and a.get("id")
                }

                if not expense_accounts:
                    st.warning("No EXPENSE ledgers are available. Create the required ledgers in Chart of Accounts first.")
                else:
                    expense_labels = list(expense_accounts.keys())
                    with st.form("expense_register_form", clear_on_submit=True):
                        e1, e2 = st.columns(2)
                        expense_date = e1.date_input("Expense Date", key="expense_date")
                        expense_account_label = e2.selectbox("Expense Account", expense_labels, key="expense_account")
                        expense_account_id = expense_accounts[expense_account_label]

                        e3, e4 = st.columns(2)
                        description = e3.text_input("Description", key="expense_description")
                        payment_mode = e4.selectbox("Payment Mode", ["CASH", "BANK", "UPI", "CHEQUE", "CREDIT", "OTHER"], key="expense_payment_mode")

                        if settlement_accounts:
                            payment_account_label = st.selectbox("Paid From / Payable Account", list(settlement_accounts.keys()), key="expense_payment_account")
                            payment_account_id = settlement_accounts[payment_account_label]
                        else:
                            payment_account_id = None
                            st.warning("Create a Cash/Bank asset or payable liability account first.")

                        e5, e6, e7 = st.columns(3)
                        taxable_value = e5.number_input("Taxable Value", min_value=0.0, step=0.01, key="expense_taxable")
                        gst_amount = e6.number_input("GST Amount", min_value=0.0, step=0.01, key="expense_gst")
                        total_amount = e7.number_input("Total Amount", min_value=0.0, step=0.01, key="expense_total")
                        reference_no = st.text_input("Reference No.", key="expense_reference")
                        save_expense = st.form_submit_button("💾 Save Expense", type="primary", use_container_width=True)

                    if save_expense:
                        if not description.strip():
                            st.error("Please enter an expense description.")
                        elif total_amount <= 0:
                            st.error("Total amount must be greater than zero.")
                        elif payment_account_id is None:
                            st.error("Please select a Paid From / Payable Account.")
                        else:
                            try:
                                expense_response = (supabase.table("accounts_expenses").insert({
                                    "expense_date": expense_date.isoformat(),
                                    "expense_account_id": expense_account_id,
                                    "description": description.strip(),
                                    "taxable_value": taxable_value,
                                    "gst_amount": gst_amount,
                                    "total_amount": total_amount,
                                    "payment_mode": payment_mode,
                                    "reference_no": reference_no.strip() or None,
                                    "entered_by": str(user.id)
                                }).execute())
                                expense_id = expense_response.data[0]["id"]
                                journal_number = create_journal_entry(
                                    expense_date, "EXPENSE", "EXPENSE", expense_id, description.strip(),
                                    [{"account_id": expense_account_id, "party_id": None, "debit": total_amount, "credit": 0, "narration": description.strip()},
                                     {"account_id": payment_account_id, "party_id": None, "debit": 0, "credit": total_amount, "narration": description.strip()}],
                                    user.id
                                )
                                st.success(f"Expense recorded and Journal {journal_number} posted.")
                                st.rerun()
                            except Exception as e:
                                st.error("Unable to save expense and post journal.")
                                st.code(str(e))

                st.divider()
                st.markdown("### 📋 Expense History")
                try:
                    expenses = supabase.table("accounts_expenses").select("*").order("expense_date", desc=True).limit(100).execute().data or []
                    if expenses:
                        expense_search = st.text_input("🔎 Search Expenses", key="expense_register_search", placeholder="Description, reference, payment mode...")
                        filtered_expenses = filter_display_rows(expenses, expense_search)
                        st.dataframe(filtered_expenses, use_container_width=True, hide_index=True)
                        add_excel_download(filtered_expenses, "SP_Enterprise_Expenses.xlsx", "📊 Download Expenses (Excel)", "export_expenses", "Expenses")
                        render_delete_control(
                            "accounts_expenses",
                            expenses,
                            lambda r: f'{r.get("expense_date", "")} | {r.get("description", "Expense")} | ₹{float(r.get("total_amount") or 0):,.2f}',
                            "delete_expense",
                            transaction=True
                        )
                    else:
                        st.info("No expense records yet.")
                except Exception as e:
                    st.error(f"Unable to load expenses: {e}")


        # ============================================================
        # RECEIPTS
        # ============================================================

        with reg3:
            st.subheader("💰 Receipt Register")
            st.caption("Apply customer receipts against outstanding sales and post the corresponding journal automatically.")

            party_options = {f'{p.get("name", "")} [{p.get("party_type", "")}]': p for p in parties if p.get("id")}
            receivable_id = find_account_id(chart_accounts, ["receivable", "debtor", "customer"], ["ASSET"])
            selected_party_id = None
            if party_options:
                party_label = st.selectbox("Customer / Party", list(party_options.keys()), key="receipt_party")
                selected_party_id = party_options[party_label]["id"]
                try:
                    outstanding_sales = supabase.table("sales_invoices").select("id,invoice_number,balance_amount,payment_status").eq("customer_id", selected_party_id).gt("balance_amount", 0).neq("payment_status", "CANCELLED").order("invoice_date", desc=True).execute().data or []
                    receipt_outstanding = sum(float(x.get("balance_amount") or 0) for x in outstanding_sales)
                    if outstanding_sales:
                        st.info("Outstanding: " + " | ".join(f'{x.get("invoice_number")}: ₹{float(x.get("balance_amount") or 0):,.2f}' for x in outstanding_sales))
                    else:
                        receipt_outstanding = 0.0
                except Exception:
                    pass

            with st.form("receipt_register_form", clear_on_submit=True):
                r1, r2 = st.columns(2)
                receipt_no = r1.text_input("Receipt No.", key="receipt_no")
                receipt_date = r2.date_input("Receipt Date", key="receipt_date")
                r3, r4 = st.columns(2)
                amount = r3.number_input("Amount Received", min_value=0.0, value=float(receipt_outstanding if "receipt_outstanding" in locals() else 0.0), step=0.01, key="receipt_amount")
                payment_mode = r4.selectbox("Payment Mode", ["CASH", "BANK", "UPI", "CHEQUE", "OTHER"], key="receipt_payment_mode")
                narration = st.text_input("Narration", key="receipt_narration")
                reference_no = st.text_input("Reference No.", key="receipt_reference")
                bank_account_id = None
                bank_chart_id = None
                if bank_options:
                    bank_label = st.selectbox("Cash / Bank Account", ["None"] + list(bank_options.keys()), key="receipt_bank")
                    if bank_label != "None":
                        bank_account_id = bank_options[bank_label]
                        bank_record = next((b for b in cash_bank_accounts if b.get("id") == bank_account_id), None)
                        bank_chart_id = (bank_record or {}).get("chart_account_id")
                save_receipt = st.form_submit_button("💾 Save Receipt & Post Journal", type="primary", use_container_width=True)

            if save_receipt:
                if not receipt_no.strip() or amount <= 0:
                    st.error("Receipt No. and a positive amount are required.")
                elif not selected_party_id or not bank_chart_id or not receivable_id:
                    st.error("Select a customer and ensure a Cash/Bank ledger plus Customer Receivables ledger exist in Chart of Accounts.")
                else:
                    try:
                        response = supabase.table("accounts_receipts").insert({"receipt_no": receipt_no.strip(), "receipt_date": receipt_date.isoformat(), "party_id": selected_party_id, "amount": amount, "payment_mode": payment_mode, "bank_account_id": bank_account_id, "reference_no": reference_no.strip() or None, "narration": narration.strip() or None, "entered_by": str(user.id)}).execute()
                        receipt_id = response.data[0]["id"]
                        journal_number = create_journal_entry(receipt_date, "RECEIPT", "RECEIPT", receipt_id, narration.strip() or f"Receipt {receipt_no.strip()}", [{"account_id": bank_chart_id, "party_id": selected_party_id, "debit": amount, "credit": 0, "narration": narration.strip() or "Customer receipt"}, {"account_id": receivable_id, "party_id": selected_party_id, "debit": 0, "credit": amount, "narration": narration.strip() or "Customer receipt"}], user.id)
                        remaining = float(amount)
                        for invoice in outstanding_sales:
                            if remaining <= 0:
                                break
                            balance = float(invoice.get("balance_amount") or 0)
                            applied = min(remaining, balance)
                            new_balance = round(balance - applied, 2)
                            current_received = float((supabase.table("sales_invoices").select("amount_received").eq("id", invoice["id"]).limit(1).execute().data or [{"amount_received": 0}])[0].get("amount_received") or 0)
                            supabase.table("sales_invoices").update({
                                "amount_received": current_received + applied,
                                "balance_amount": new_balance,
                                "payment_status": "PAID" if new_balance <= 0.01 else "PARTIAL"
                            }).eq("id", invoice["id"]).execute()
                            remaining -= applied
                        st.success(f"Receipt saved. Journal {journal_number} posted and outstanding invoices updated.")
                        st.rerun()
                    except Exception as e:
                        st.error("Unable to save receipt and post journal.")
                        st.code(str(e))

            st.divider()
            receipts = supabase.table("accounts_receipts").select("*").order("receipt_date", desc=True).limit(100).execute().data or []
            if receipts:
                receipt_search = st.text_input("🔎 Search Receipts", key="receipt_register_search", placeholder="Receipt no., reference, narration...")
                filtered_receipts = filter_display_rows(receipts, receipt_search)
                st.dataframe(filtered_receipts, use_container_width=True, hide_index=True)
                add_excel_download(filtered_receipts, "SP_Enterprise_Receipts.xlsx", "📊 Download Receipts (Excel)", "export_receipts", "Receipts")
            else:
                st.info("No receipt records yet.")
            render_delete_control(
                "accounts_receipts",
                receipts,
                lambda r: f'{r.get("receipt_no", "Receipt")} | {r.get("receipt_date", "")} | ₹{float(r.get("amount") or 0):,.2f}',
                "delete_receipt",
                transaction=True
            )

        # ============================================================
        # PAYMENTS
        # ============================================================

        with reg4:
            st.subheader("💳 Payment Register")
            st.caption("Apply supplier payments to the same supplier master used by Stock and Purchases.")

            supplier_options = {f'{p.get("name", "")} [{p.get("party_type", "")}]': p for p in parties if p.get("id")}
            payable_id = find_account_id(chart_accounts, ["payable", "creditor", "supplier"], ["LIABILITY"])
            selected_supplier_id = None
            payment_outstanding = 0.0
            supplier_purchases = []
            supplier_payments = []
            if supplier_options:
                supplier_label = st.selectbox("Supplier / Party", list(supplier_options.keys()), key="payment_party")
                selected_supplier_id = supplier_options[supplier_label]["id"]
                try:
                    supplier_purchases = supabase.table("accounts_purchases").select("bill_total").eq("party_id", selected_supplier_id).execute().data or []
                    supplier_payments = supabase.table("accounts_payments").select("amount").eq("party_id", selected_supplier_id).execute().data or []
                    payment_outstanding = max(0.0, sum(float(x.get("bill_total") or 0) for x in supplier_purchases) - sum(float(x.get("amount") or 0) for x in supplier_payments))
                    st.info(f"Supplier outstanding payable: ₹{payment_outstanding:,.2f}")
                except Exception:
                    payment_outstanding = 0.0

            with st.form("payment_register_form", clear_on_submit=True):
                p1, p2 = st.columns(2)
                payment_no = p1.text_input("Payment No.", key="payment_no")
                payment_date = p2.date_input("Payment Date", key="payment_date")
                p3, p4 = st.columns(2)
                amount = p3.number_input("Amount Paid", min_value=0.0, value=float(payment_outstanding), step=0.01, key="payment_amount")
                payment_mode = p4.selectbox("Payment Mode", ["CASH", "BANK", "UPI", "CHEQUE", "OTHER"], key="payment_payment_mode")
                narration = st.text_input("Narration", key="payment_narration")
                reference_no = st.text_input("Reference No.", key="payment_reference")
                bank_account_id = None
                bank_chart_id = None
                if bank_options:
                    bank_label = st.selectbox("Cash / Bank Account", ["None"] + list(bank_options.keys()), key="payment_bank")
                    if bank_label != "None":
                        bank_account_id = bank_options[bank_label]
                        bank_record = next((b for b in cash_bank_accounts if b.get("id") == bank_account_id), None)
                        bank_chart_id = (bank_record or {}).get("chart_account_id")
                save_payment = st.form_submit_button("💾 Save Payment & Post Journal", type="primary", use_container_width=True)

            if save_payment:
                if not payment_no.strip() or amount <= 0:
                    st.error("Payment No. and a positive amount are required.")
                elif not selected_supplier_id or not bank_chart_id or not payable_id:
                    st.error("Select a supplier and ensure a Cash/Bank ledger plus Supplier Payables ledger exist in Chart of Accounts.")
                else:
                    try:
                        response = supabase.table("accounts_payments").insert({"payment_no": payment_no.strip(), "payment_date": payment_date.isoformat(), "party_id": selected_supplier_id, "amount": amount, "payment_mode": payment_mode, "bank_account_id": bank_account_id, "reference_no": reference_no.strip() or None, "narration": narration.strip() or None, "entered_by": str(user.id)}).execute()
                        payment_id = response.data[0]["id"]
                        journal_number = create_journal_entry(payment_date, "PAYMENT", "PAYMENT", payment_id, narration.strip() or f"Payment {payment_no.strip()}", [{"account_id": payable_id, "party_id": selected_supplier_id, "debit": amount, "credit": 0, "narration": narration.strip() or "Supplier payment"}, {"account_id": bank_chart_id, "party_id": selected_supplier_id, "debit": 0, "credit": amount, "narration": narration.strip() or "Supplier payment"}], user.id)
                        st.success(f"Payment saved. Journal {journal_number} posted.")
                        st.rerun()
                    except Exception as e:
                        st.error("Unable to save payment and post journal.")
                        st.code(str(e))

            st.divider()
            payments = supabase.table("accounts_payments").select("*").order("payment_date", desc=True).limit(100).execute().data or []
            if payments:
                payment_search = st.text_input("🔎 Search Payments", key="payment_register_search", placeholder="Payment no., reference, narration...")
                filtered_payments = filter_display_rows(payments, payment_search)
                st.dataframe(filtered_payments, use_container_width=True, hide_index=True)
                add_excel_download(filtered_payments, "SP_Enterprise_Payments.xlsx", "📊 Download Payments (Excel)", "export_payments", "Payments")
            else:
                st.info("No payment records yet.")
            render_delete_control(
                "accounts_payments",
                payments,
                lambda r: f'{r.get("payment_no", "Payment")} | {r.get("payment_date", "")} | ₹{float(r.get("amount") or 0):,.2f}',
                "delete_payment",
                transaction=True
            )


        # ============================================================
        # CASH / BANK
        # ============================================================

        with reg5:

            st.subheader("🏦 Cash / Bank Accounts")

            with st.form(
                "cash_bank_form",
                clear_on_submit=True
            ):

                b1, b2 = st.columns(2)

                account_name = b1.text_input(
                    "Account Name",
                    key="cash_bank_name"
                )

                cash_bank_chart_options = {
                    f'{a.get("unit_code", "")} - {a.get("account_name", "")}':
                        a.get("id")
                    for a in accounts
                    if a.get("id")
                    and str(a.get("account_type", "")).upper() == "ASSET"
                }

                if cash_bank_chart_options:

                    cash_bank_chart_label = st.selectbox(
                        "Linked Chart of Accounts Ledger",
                        list(cash_bank_chart_options.keys()),
                        key="cash_bank_chart_account"
                    )

                    cash_bank_chart_account_id = (
                        cash_bank_chart_options[
                            cash_bank_chart_label
                        ]
                    )

                else:

                    cash_bank_chart_account_id = None

                    st.warning(
                        "Create an ASSET account in Chart of Accounts "
                        "before adding a Cash / Bank account."
                    )
                
                account_type = b2.selectbox(
                    "Account Type",
                    [
                        "CASH",
                        "BANK",
                        "UPI",
                        "OTHER"
                    ],
                    key="cash_bank_type"
                )

                b3, b4 = st.columns(2)

                bank_name = b3.text_input(
                    "Bank Name",
                    key="cash_bank_bank_name"
                )

                account_number = b4.text_input(
                    "Account Number",
                    key="cash_bank_account_number"
                )

                b5, b6 = st.columns(2)

                ifsc_code = b5.text_input(
                    "IFSC Code",
                    key="cash_bank_ifsc"
                )

                opening_balance = b6.number_input(
                    "Opening Balance",
                    min_value=0.0,
                    step=0.01,
                    key="cash_bank_opening"
                )

                save_bank = st.form_submit_button(
                    "💾 Add Cash / Bank Account",
                    use_container_width=True
                )

            if save_bank:

                if not account_name.strip():

                    st.error(
                        "Please enter an account name."
                    )

                else:

                    try:

                        supabase.table(
                            "cash_bank_accounts"
                        ).insert({
                            "account_name":
                                account_name.strip(),

                            "account_type":
                                account_type,

                            "bank_name":
                                bank_name.strip() or None,

                            "account_number":
                                account_number.strip() or None,

                            "ifsc_code":
                                ifsc_code.strip() or None,

                            "opening_balance":
                                opening_balance,

                            "chart_account_id":
                                cash_bank_chart_account_id,

                            "active":
                                True

                        }).execute()

                        st.success(
                            f"{account_name} added successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Unable to create account: {e}"
                        )

            st.divider()

            try:

                bank_accounts = (
                    supabase
                    .table("cash_bank_accounts")
                    .select("*")
                    .order("account_name")
                    .execute()
                    .data
                    or []
                )

                if bank_accounts:

                    display_accounts = []

                    for account in bank_accounts:

                        display_accounts.append({
                            "Account Name":
                                account.get("account_name"),

                            "Type":
                                account.get("account_type"),

                            "Bank":
                                account.get("bank_name"),

                            "Account Number":
                                account.get("account_number"),

                            "IFSC":
                                account.get("ifsc_code"),

                            "Opening Balance":
                                account.get("opening_balance"),

                            "Active":
                                account.get("active")
                        })

                    cash_bank_search = st.text_input("🔎 Search Cash / Bank Accounts", key="cash_bank_search", placeholder="Account name, bank, number...")
                    filtered_cash_bank = filter_display_rows(display_accounts, cash_bank_search)
                    st.dataframe(
                        filtered_cash_bank,
                        use_container_width=True,
                        hide_index=True
                    )
                    add_excel_download(filtered_cash_bank, "SP_Enterprise_Cash_Bank_Accounts.xlsx", "📊 Download Cash / Bank Accounts (Excel)", "export_cash_bank_accounts", "Cash Bank Accounts")
                    render_delete_control(
                        "cash_bank_accounts",
                        bank_accounts,
                        lambda r: f'{r.get("account_name", "Account")} | {r.get("account_type", "")}',
                        "delete_cash_bank"
                    )

                else:

                    st.info(
                        "No Cash / Bank accounts created yet."
                    )

            except Exception as e:

                st.error(
                    f"Unable to load Cash / Bank accounts: {e}"
                )



    # ================================================================
    # TAB 4 - JOURNAL ENTRIES
    # ================================================================

    with account_tab4:

        st.subheader("📒 Journal Entries")

        st.caption(
            "Record balanced double-entry journal transactions "
            "for S.P. Enterprise."
        )

        # ------------------------------------------------------------
        # LOAD CHART OF ACCOUNTS
        # ------------------------------------------------------------

        try:

            journal_accounts_response = (
                supabase
                .table("chart_of_accounts")
                .select(
                    "id, account_code, account_name, account_type"
                )
                .eq("active", True)
                .order("account_code")
                .execute()
            )

            journal_accounts = (
                journal_accounts_response.data or []
            )

        except Exception as e:

            journal_accounts = []

            st.error(
                "Unable to load Chart of Accounts for Journal Entries."
            )

            st.code(str(e))


        journal_account_options = {

            f'{account.get("account_code", "")} - '
            f'{account.get("account_name", "")} '
            f'({account.get("account_type", "")})':
                account.get("id")

            for account in journal_accounts

            if account.get("id")
        }


        if not journal_account_options:

            st.warning(
                "No active Chart of Accounts found. "
                "Create accounts before recording journal entries."
            )

        else:

            # ========================================================
            # NEW JOURNAL ENTRY
            # ========================================================

            with st.expander(
                "➕ Create Journal Entry",
                expanded=True
            ):

                j1, j2, j3 = st.columns(3)

                journal_date = j1.date_input(
                    "Entry Date",
                    value=date.today(),
                    key="journal_entry_date"
                )

                voucher_type = j2.selectbox(
                    "Voucher Type",
                    [
                        "JOURNAL",
                        "ADJUSTMENT",
                        "OPENING",
                        "TRANSFER",
                        "OTHER"
                    ],
                    key="journal_voucher_type"
                )

                reference_type = j3.selectbox(
                    "Reference Type",
                    [
                        "MANUAL",
                        "EXPENSE",
                        "PURCHASE",
                        "SALES",
                        "RECEIPT",
                        "PAYMENT",
                        "OTHER"
                    ],
                    key="journal_reference_type"
                )

                reference_no = st.text_input(
                    "Reference No.",
                    key="journal_reference_no"
                )

                journal_narration = st.text_area(
                    "Narration",
                    placeholder="Enter the reason / description for this journal entry.",
                    key="journal_narration"
                )

                st.divider()

                st.markdown("### Journal Lines")

                # ----------------------------------------------------
                # LINE 1
                # ----------------------------------------------------

                l1, l2, l3 = st.columns([5, 2, 2])

                line1_account_label = l1.selectbox(
                    "Account - Debit",
                    list(journal_account_options.keys()),
                    key="journal_debit_account"
                )

                line1_debit = l2.number_input(
                    "Debit (₹)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="journal_debit_amount"
                )

                line1_credit = l3.number_input(
                    "Credit (₹)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="journal_credit_amount"
                )

                # ----------------------------------------------------
                # LINE 2
                # ----------------------------------------------------

                l4, l5, l6 = st.columns([5, 2, 2])

                line2_account_label = l4.selectbox(
                    "Account - Credit",
                    list(journal_account_options.keys()),
                    key="journal_credit_account"
                )

                line2_debit = l5.number_input(
                    "Debit (₹)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="journal_line2_debit"
                )

                line2_credit = l6.number_input(
                    "Credit (₹)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="journal_line2_credit"
                )

                # ----------------------------------------------------
                # CALCULATE TOTALS
                # ----------------------------------------------------

                total_debit = (
                    line1_debit
                    + line2_debit
                )

                total_credit = (
                    line1_credit
                    + line2_credit
                )

                difference = (
                    total_debit
                    - total_credit
                )

                st.divider()

                t1, t2, t3 = st.columns(3)

                t1.metric(
                    "Total Debit",
                    f"₹{total_debit:,.2f}"
                )

                t2.metric(
                    "Total Credit",
                    f"₹{total_credit:,.2f}"
                )

                t3.metric(
                    "Difference",
                    f"₹{difference:,.2f}"
                )

                # ----------------------------------------------------
                # BALANCE STATUS
                # ----------------------------------------------------

                if (
                    total_debit > 0
                    and abs(difference) < 0.01
                ):

                    st.success(
                        "✓ Journal entry is balanced."
                    )

                elif total_debit == 0 and total_credit == 0:

                    st.info(
                        "Enter debit and credit amounts."
                    )

                else:

                    st.warning(
                        "⚠ Journal entry is not balanced. "
                        "Total Debit must equal Total Credit."
                    )

                # ----------------------------------------------------
                # SAVE JOURNAL
                # ----------------------------------------------------

                save_journal = st.button(
                    "💾 Save Journal Entry",
                    type="primary",
                    use_container_width=True,
                    key="save_manual_journal"
                )

                if save_journal:

                    # ------------------------------------------------
                    # VALIDATION
                    # ------------------------------------------------

                    if not journal_narration.strip():

                        st.error(
                            "Journal narration is required."
                        )

                    elif total_debit <= 0:

                        st.error(
                            "Journal amount must be greater than zero."
                        )

                    elif abs(difference) >= 0.01:

                        st.error(
                            "Journal entry cannot be saved because "
                            "Debit and Credit are not equal."
                        )

                    elif (
                        line1_debit > 0
                        and line1_credit > 0
                    ):

                        st.error(
                            "A journal line cannot contain both "
                            "Debit and Credit."
                        )

                    elif (
                        line2_debit > 0
                        and line2_credit > 0
                    ):

                        st.error(
                            "A journal line cannot contain both "
                            "Debit and Credit."
                        )

                    else:

                        try:

                            # ----------------------------------------
                            # GENERATE JOURNAL NUMBER
                            # ----------------------------------------

                            journal_number = (
                                "JV-"
                                + journal_date.strftime("%Y%m%d")
                                + "-"
                                + uuid.uuid4().hex[:6].upper()
                            )

                            # ----------------------------------------
                            # CREATE JOURNAL HEADER
                            # ----------------------------------------

                            journal_header = {

                                "entry_no":
                                    journal_number,

                                "entry_date":
                                    journal_date.isoformat(),

                                "voucher_type":
                                    voucher_type,

                                "reference_type":
                                    reference_type,

                                "reference_id":
                                    None,

                                "narration":
                                    journal_narration.strip(),

                                "entered_by":
                                    str(user.id)
                            }

                            journal_response = (
                                supabase
                                .table("journal_entries")
                                .insert(journal_header)
                                .execute()
                            )

                            created_journal = (
                                journal_response.data[0]
                            )

                            journal_entry_id = (
                                created_journal["id"]
                            )

                            # ----------------------------------------
                            # CREATE JOURNAL LINES
                            # ----------------------------------------

                            debit_account_id = (
                                journal_account_options[
                                    line1_account_label
                                ]
                            )

                            credit_account_id = (
                                journal_account_options[
                                    line2_account_label
                                ]
                            )

                            journal_lines = [

                                {
                                    "journal_entry_id":
                                        journal_entry_id,

                                    "account_id":
                                        debit_account_id,

                                    "party_id":
                                        None,

                                    "debit":
                                        line1_debit,

                                    "credit":
                                        0,

                                    "narration":
                                        journal_narration.strip()
                                },

                                {
                                    "journal_entry_id":
                                        journal_entry_id,

                                    "account_id":
                                        credit_account_id,

                                    "party_id":
                                        None,

                                    "debit":
                                        0,

                                    "credit":
                                        line2_credit,

                                    "narration":
                                        journal_narration.strip()
                                }
                            ]

                            (
                                supabase
                                .table("journal_lines")
                                .insert(journal_lines)
                                .execute()
                            )

                            st.success(
                                f"Journal Entry "
                                f"{journal_number} "
                                f"saved successfully."
                            )

                            st.rerun()

                        except Exception as e:

                            st.error(
                                "Unable to save Journal Entry."
                            )

                            st.code(str(e))


            # ========================================================
            # JOURNAL REGISTER
            # ========================================================

            st.divider()

            st.subheader("📋 Journal Register")

            try:

                journal_entries_response = (
                    supabase
                    .table("journal_entries")
                    .select("*")
                    .order("entry_date", desc=True)
                    .limit(100)
                    .execute()
                )

                journal_entries = (
                    journal_entries_response.data or []
                )

            except Exception as e:

                journal_entries = []

                st.error(
                    "Unable to load Journal Register."
                )

                st.code(str(e))


            if journal_entries:

                display_journals = []

                for journal in journal_entries:

                    display_journals.append({

                        "Entry No.":
                            journal.get("entry_no"),

                        "Date":
                            journal.get("entry_date"),

                        "Voucher Type":
                            journal.get("voucher_type"),

                        "Reference Type":
                            journal.get("reference_type"),

                        "Reference ID":
                            journal.get("reference_id"),

                        "Narration":
                            journal.get("narration"),

                        "Entered By":
                            journal.get("entered_by"),

                        "Created At":
                            journal.get("created_at")
                    })

                journal_search = st.text_input("🔎 Search Journal Register", key="journal_register_search", placeholder="Journal no., reference, narration, voucher type...")
                filtered_journals = filter_display_rows(display_journals, journal_search)
                st.dataframe(
                    filtered_journals,
                    use_container_width=True,
                    hide_index=True
                )
                add_excel_download(filtered_journals, "SP_Enterprise_Journal_Register.xlsx", "📊 Download Journal Register (Excel)", "export_journal_register", "Journal Register")
                render_delete_control(
                    "journal_entries",
                    journal_entries,
                    lambda r: f'{r.get("entry_no", "Journal")} | {r.get("entry_date", "")} | {r.get("voucher_type", "")}',
                    "delete_journal_entry",
                    transaction=True
                )

            else:

                st.info(
                    "No journal entries recorded yet."
                )




# ---------------------------------------------------------------------
# DOCUMENTS
# ---------------------------------------------------------------------

if page == "Documents":

    st.markdown('<div class="module-title">Document Register</div>', unsafe_allow_html=True)
    st.markdown('<div class="module-subtitle">Central index for statutory, banking, property and operational records</div>', unsafe_allow_html=True)

    document_types = ["GST", "ITR", "Trade Licence", "Professional Tax", "Lease", "Electricity", "Bank", "Loan", "Insurance", "Other"]

    with st.expander("➕ Add Document", expanded=True):
        with st.form("document_form", clear_on_submit=True):
            d1, d2, d3 = st.columns(3)
            document_type = d1.selectbox("Document Type", document_types)
            document_number = d2.text_input("Document / Reference No.")
            document_name = d3.text_input("Document Name")
            d4, d5, d6 = st.columns(3)
            issue_date = d4.date_input("Issue Date", value=date.today())
            expiry_date = d5.date_input("Expiry / Renewal Date", value=date.today())
            status = d6.selectbox("Status", ["ACTIVE", "PENDING", "EXPIRED", "RENEWAL DUE"])
            document_url = st.text_input("Document Link / Storage Path", placeholder="Optional secure file link or storage path")
            notes = st.text_area("Notes")
            save_document = st.form_submit_button("💾 Save Document", type="primary", use_container_width=True)

        if save_document:
            if not document_name.strip():
                st.error("Document Name is required.")
            else:
                try:
                    supabase.table("business_documents").insert({
                        "document_type": document_type,
                        "document_number": document_number.strip() or None,
                        "document_name": document_name.strip(),
                        "issue_date": issue_date.isoformat(),
                        "expiry_date": expiry_date.isoformat(),
                        "status": status,
                        "document_url": document_url.strip() or None,
                        "notes": notes.strip() or None,
                        "entered_by": str(user.id)
                    }).execute()
                    st.success("Document added successfully.")
                    st.rerun()
                except Exception as e:
                    st.error("Unable to save document.")
                    st.code(str(e))

    st.divider()
    try:
        documents = supabase.table("business_documents").select("*").order("expiry_date").limit(500).execute().data or []
    except Exception as e:
        documents = []
        st.error("Unable to load Document Register.")
        st.code(str(e))

    today = date.today()
    expiring = []
    for doc in documents:
        try:
            exp = date.fromisoformat(str(doc.get("expiry_date"))) if doc.get("expiry_date") else None
            if exp and exp < today:
                doc["status"] = "EXPIRED"
            elif exp and (exp - today).days <= 30:
                expiring.append(doc)
        except Exception:
            pass

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Documents", len(documents))
    m2.metric("Expired", sum(1 for d in documents if d.get("status") == "EXPIRED"))
    m3.metric("Due within 30 days", len(expiring))

    if expiring:
        st.warning(f"{len(expiring)} document(s) require attention within 30 days.")

    if documents:
        display_documents = []
        for d in documents:
            display_documents.append({
                "Type": d.get("document_type"),
                "Document": d.get("document_name"),
                "Reference": d.get("document_number"),
                "Issue Date": d.get("issue_date"),
                "Expiry": d.get("expiry_date"),
                "Status": d.get("status"),
                "Link": d.get("document_url"),
                "Notes": d.get("notes")
            })
        document_search = st.text_input("🔎 Search Documents", key="documents_search", placeholder="Document name, number, type, status...")
        filtered_documents = filter_display_rows(display_documents, document_search)
        st.dataframe(filtered_documents, use_container_width=True, hide_index=True)
        add_excel_download(filtered_documents, "SP_Enterprise_Documents.xlsx", "📊 Download Documents (Excel)", "export_documents", "Documents")

        with st.expander("🗑️ Delete a test document"):
            options = {f'{d.get("document_name")} | {d.get("document_number") or "No Ref"}': d.get("id") for d in documents if d.get("id")}
            if options:
                selected = st.selectbox("Document", list(options.keys()), key="delete_document")
                if st.button("Delete selected document", type="secondary", key="delete_document_button"):
                    try:
                        delete_record("business_documents", options[selected])
                        st.success("Document deleted. A deletion snapshot is retained for the audit window.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to delete document: {e}")
    else:
        st.info("No documents recorded yet.")




if has_feature("MODIFY_STOCK"):
    with st.expander("🧾 Modification Audit", expanded=False):
        try:
            mod_audit = supabase.table("modification_audit").select("*").order("modified_at", desc=True).limit(100).execute().data or []
            if mod_audit:
                audit_search = st.text_input("🔎 Search Modification Audit", key="modification_audit_search", placeholder="Record ID, table, user...")
                filtered_audit = filter_display_rows(mod_audit, audit_search)
                st.dataframe(filtered_audit, use_container_width=True, hide_index=True)
                add_excel_download(filtered_audit, "SP_Enterprise_Modification_Audit.xlsx", "📊 Download Modification Audit (Excel)", "export_modification_audit", "Modification Audit")
            else:
                st.info("No stock modifications recorded yet.")
        except Exception as e:
            st.warning(f"Unable to load Modification Audit: {e}")


# ---------------------------------------------------------------------
# APPLICATION FOOTER — VISUAL ONLY
# ---------------------------------------------------------------------
if "user" in st.session_state:
    st.markdown(
        """
        <div class="sp-footer">
            S.P. ENTERPRISE CONTROL SYSTEM &nbsp;•&nbsp;
            Operational &nbsp;•&nbsp; Inventory &nbsp;•&nbsp; Accounts &nbsp;•&nbsp; Jobwork
            &nbsp;•&nbsp; 2026
        </div>
        """,
        unsafe_allow_html=True
    )
