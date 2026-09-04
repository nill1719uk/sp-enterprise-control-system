import hashlib
from datetime import date, datetime, timezone
import streamlit as st
from supabase import create_client
import uuid

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
    st.title("S.P. Enterprise")
    st.caption(user.email)

    page = st.radio(
        "Module",
        ["Dashboard", "Stock Control", "Accounts", "Documents"]
    )

    if st.button("Sign out"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()


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

            movement_mode = st.radio(
                "Transaction Type",
                [
                    "📥 Receive Stock",
                    "📤 New Dispatch"
                ],
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
                            "duplicate_fingerprint": fingerprint
                        }

                        try:

                            (
                                supabase
                                .table("stock_movements")
                                .insert(data)
                                .execute()
                            )

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
            # NEW DISPATCH
            # =========================================================

            else:

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
                                fingerprint
                        }

                        try:

                            dispatch_response = (
                                supabase
                                .table("stock_movements")
                                .insert(data)
                                .execute()
                            )

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

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True
        )

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

        st.dataframe(
            party_rows,
            use_container_width=True,
            hide_index=True
        )

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

            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True
            )


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
                business_parties(name)
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

        st.dataframe(
            out,
            use_container_width=True,
            hide_index=True
        )

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

        st.dataframe(
            register_rows,
            use_container_width=True,
            hide_index=True
        )

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
            st.dataframe(pending_display, use_container_width=True, hide_index=True)

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
                    st.dataframe(purchases, use_container_width=True, hide_index=True)
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
                        st.dataframe(expenses, use_container_width=True, hide_index=True)
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
            st.dataframe(receipts, use_container_width=True, hide_index=True) if receipts else st.info("No receipt records yet.")
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
            st.dataframe(payments, use_container_width=True, hide_index=True) if payments else st.info("No payment records yet.")
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

                    st.dataframe(
                        display_accounts,
                        use_container_width=True,
                        hide_index=True
                    )
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

                st.dataframe(
                    display_journals,
                    use_container_width=True,
                    hide_index=True
                )
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
        st.dataframe(display_documents, use_container_width=True, hide_index=True)

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

