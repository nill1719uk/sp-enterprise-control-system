import hashlib
from datetime import date, datetime, timezone, timedelta
import streamlit as st
from supabase import create_client
import uuid

st.set_page_config(
    page_title="S.P. Enterprise Control System",
    page_icon="📊",
    layout="wide"
)

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
# DELETION AUDIT / RETENTION
# ================================================================

def cleanup_deletion_audit():
    """Keep deletion snapshots for 3 days, then remove them."""
    try:
        supabase.table("deletion_audit").delete().lt(
            "expires_at",
            datetime.now(timezone.utc).isoformat()
        ).execute()
    except Exception:
        pass


def audit_delete(table_name, record_id, deleted_by, snapshot):
    """Delete a record and retain its snapshot for three days."""
    response = (
        supabase
        .table(table_name)
        .delete()
        .eq("id", record_id)
        .execute()
    )

    if not response.data:
        raise Exception("Record could not be deleted.")

    now = datetime.now(timezone.utc)
    supabase.table("deletion_audit").insert({
        "table_name": table_name,
        "record_id": str(record_id),
        "record_snapshot": snapshot,
        "deleted_by": str(deleted_by),
        "deleted_at": now.isoformat(),
        "expires_at": (now + timedelta(days=3)).isoformat()
    }).execute()


def delete_related_then_audit(table_name, record_id, deleted_by, related=None):
    """Delete a parent and related rows, retaining deletion snapshots."""
    related = related or []

    parent = (
        supabase
        .table(table_name)
        .select("*")
        .eq("id", record_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not parent:
        raise Exception("Record was not found.")

    snapshots = [(table_name, parent[0])]

    for rel in related:
        rel_rows = (
            supabase
            .table(rel["table"])
            .select("*")
            .eq(rel["column"], record_id)
            .execute()
            .data
            or []
        )
        snapshots.extend((rel["table"], row) for row in rel_rows)

        if rel_rows:
            (
                supabase
                .table(rel["table"])
                .delete()
                .eq(rel["column"], record_id)
                .execute()
            )

    deleted = (
        supabase
        .table(table_name)
        .delete()
        .eq("id", record_id)
        .execute()
    )

    if not deleted.data:
        raise Exception("Record could not be deleted.")

    now = datetime.now(timezone.utc)
    audit_rows = [
        {
            "table_name": deleted_table,
            "record_id": str(snapshot.get("id")),
            "record_snapshot": snapshot,
            "deleted_by": str(deleted_by),
            "deleted_at": now.isoformat(),
            "expires_at": (now + timedelta(days=3)).isoformat()
        }
        for deleted_table, snapshot in snapshots
    ]

    if audit_rows:
        supabase.table("deletion_audit").insert(audit_rows).execute()


def delete_journal_with_lines(journal_id, deleted_by):
    delete_related_then_audit(
        "journal_entries",
        journal_id,
        deleted_by,
        related=[
            {
                "table": "journal_lines",
                "column": "journal_entry_id"
            }
        ]
    )


cleanup_deletion_audit()


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
    st.title("📊 Control Dashboard")

    items = (
        supabase.table("stock_items")
        .select("*")
        .eq("active", True)
        .execute()
        .data
    )

    parties = (
        supabase.table("business_parties")
        .select("id")
        .eq("active", True)
        .execute()
        .data
    )

    a, b, c = st.columns(3)
    a.metric("Active Stock Items", len(items))
    b.metric("Active Parties", len(parties))

    try:
        r = (
            supabase.table("stock_movements")
            .select("id", count="exact")
            .execute()
        )
        c.metric("Stock Movements", r.count or 0)
    except Exception:
        c.metric("Stock Movements", "—")

    st.success(
        "S.P. Enterprise Control System is now in the final integrated build. "
        "Stock Control, Accounts and Documents are available."
    )

    st.caption(
        "Sales can post stock movements and double-entry accounting when the "
        "required ledger accounts are selected. Expense entries post through "
        "the journal engine."
    )

    st.divider()
    st.subheader("🗑️ Recent Deletion Audit")

    try:
        deletion_rows = (
            supabase
            .table("deletion_audit")
            .select("table_name,record_id,deleted_by,deleted_at,expires_at")
            .order("deleted_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )

        if deletion_rows:
            st.dataframe(
                deletion_rows,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No deletion records are currently retained.")
    except Exception:
        st.info(
            "Deletion audit is unavailable until the deletion-audit SQL "
            "table is created in Supabase."
        )


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

                            (
                                supabase
                                .table("stock_movements")
                                .insert(data)
                                .execute()
                            )

                            st.success(
                                "🚚 Dispatch recorded successfully."
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


            st.divider()
            with st.expander("🗑️ Delete Stock Transaction"):
                try:
                    recent_movements = (
                        supabase
                        .table("stock_movements")
                        .select("*")
                        .order("movement_date", desc=True)
                        .limit(200)
                        .execute()
                        .data
                        or []
                    )
                except Exception:
                    recent_movements = []

                if recent_movements:
                    tab1_delete_options = {
                        f'{r.get("movement_date")} | {r.get("direction")} | '
                        f'{r.get("reference_no") or "No Ref"} | {r.get("id")}': r
                        for r in recent_movements if r.get("id")
                    }
                    selected_tab1_delete_label = st.selectbox(
                        "Select transaction to delete",
                        list(tab1_delete_options.keys()),
                        key="delete_stock_transaction_tab1"
                    )
                    confirm_tab1_delete = st.checkbox(
                        "Confirm deletion of this stock transaction.",
                        key="confirm_delete_stock_transaction_tab1"
                    )
                    if st.button(
                        "🗑️ Delete Stock Transaction",
                        key="delete_stock_transaction_tab1_button",
                        use_container_width=True
                    ):
                        if not confirm_tab1_delete:
                            st.error("Please confirm the deletion first.")
                        else:
                            selected_tab1 = tab1_delete_options[
                                selected_tab1_delete_label
                            ]
                            try:
                                audit_delete(
                                    "stock_movements",
                                    selected_tab1["id"],
                                    user.id,
                                    selected_tab1
                                )
                                st.success("Stock transaction deleted.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Unable to delete stock transaction: {e}")
                else:
                    st.info("No stock transactions available to delete.")

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


        st.divider()
        st.subheader("🗑️ Delete Stock Item")

        if items:
            stock_delete_options = {
                f'{x.get("name", "")} ({x.get("unit", "")})': x
                for x in items if x.get("id")
            }
            selected_stock_delete_label = st.selectbox(
                "Select stock item to delete",
                list(stock_delete_options.keys()),
                key="delete_stock_item"
            )
            confirm_stock_delete = st.checkbox(
                "Delete this stock item and its linked stock movements.",
                key="confirm_delete_stock_item"
            )
            if st.button(
                "🗑️ Delete Stock Item",
                key="delete_stock_item_button",
                use_container_width=True
            ):
                if not confirm_stock_delete:
                    st.error("Please confirm the deletion first.")
                else:
                    selected_stock = stock_delete_options[
                        selected_stock_delete_label
                    ]
                    try:
                        delete_related_then_audit(
                            "stock_items",
                            selected_stock["id"],
                            user.id,
                            related=[{
                                "table": "stock_movements",
                                "column": "item_id"
                            }]
                        )
                        st.success("Stock item and linked movements deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to delete stock item: {e}")


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


        st.divider()
        st.subheader("🗑️ Delete Company / Party")

        if parties:
            party_delete_options = {
                f'{p.get("name", "")} [{p.get("party_type", "")}]': p
                for p in parties if p.get("id")
            }
            selected_party_delete_label = st.selectbox(
                "Select company / party to delete",
                list(party_delete_options.keys()),
                key="delete_party"
            )
            confirm_party_delete = st.checkbox(
                "Delete this party and its linked stock movements.",
                key="confirm_delete_party"
            )
            if st.button(
                "🗑️ Delete Company / Party",
                key="delete_party_button",
                use_container_width=True
            ):
                if not confirm_party_delete:
                    st.error("Please confirm the deletion first.")
                else:
                    selected_party = party_delete_options[
                        selected_party_delete_label
                    ]
                    try:
                        delete_related_then_audit(
                            "business_parties",
                            selected_party["id"],
                            user.id,
                            related=[{
                                "table": "stock_movements",
                                "column": "party_id"
                            }]
                        )
                        st.success("Company / Party deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to delete company / party: {e}")


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


        st.divider()
        st.subheader("🗑️ Delete Party Movement")

        if ledger_rows:
            party_movement_delete_options = {
                f'{r.get("movement_date")} | {r.get("direction")} | '
                f'{r.get("reference_no") or "No Ref"} | {r.get("stock_items", {}).get("name", "")}': r
                for r in ledger_rows if r.get("id")
            }
            selected_party_movement_label = st.selectbox(
                "Select movement to delete",
                list(party_movement_delete_options.keys()),
                key="delete_party_movement"
            )
            confirm_party_movement_delete = st.checkbox(
                "Confirm deletion of this party stock movement.",
                key="confirm_delete_party_movement"
            )
            if st.button(
                "🗑️ Delete Party Movement",
                key="delete_party_movement_button",
                use_container_width=True
            ):
                if not confirm_party_movement_delete:
                    st.error("Please confirm the deletion first.")
                else:
                    selected_party_movement = party_movement_delete_options[
                        selected_party_movement_label
                    ]
                    try:
                        audit_delete(
                            "stock_movements",
                            selected_party_movement["id"],
                            user.id,
                            selected_party_movement
                        )
                        st.success("Party movement deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to delete party movement: {e}")

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


        st.divider()
        st.subheader("🗑️ Delete Stock Movement")

        if rows:
            movement_delete_options = {
                f'{r.get("movement_date")} | {r.get("direction")} | '
                f'{r.get("reference_no") or "No Ref"} | {r.get("id")}': r
                for r in rows if r.get("id")
            }
            selected_movement_label = st.selectbox(
                "Select movement to delete",
                list(movement_delete_options.keys()),
                key="delete_stock_movement"
            )
            confirm_movement_delete = st.checkbox(
                "I understand this will change the stock balance.",
                key="confirm_delete_stock_movement"
            )
            if st.button(
                "🗑️ Delete Stock Movement",
                key="delete_stock_movement_button",
                use_container_width=True
            ):
                if not confirm_movement_delete:
                    st.error("Please confirm the deletion first.")
                else:
                    selected_movement = movement_delete_options[
                        selected_movement_label
                    ]
                    try:
                        audit_delete(
                            "stock_movements",
                            selected_movement["id"],
                            user.id,
                            selected_movement
                        )
                        st.success("Stock movement deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to delete stock movement: {e}")


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

        st.divider()
        st.subheader("🗑️ Delete Account")

        if accounts:
            delete_account_options = {
                f'{a.get("account_code", "")} - {a.get("account_name", "")}': a
                for a in accounts if a.get("id")
            }
            selected_delete_account_label = st.selectbox(
                "Select account to delete",
                list(delete_account_options.keys()),
                key="delete_coa_account"
            )
            confirm_account_delete = st.checkbox(
                "Confirm permanent deletion of this ledger account.",
                key="confirm_delete_coa_account"
            )
            if st.button(
                "🗑️ Delete Account",
                key="delete_coa_account_button",
                use_container_width=True
            ):
                if not confirm_account_delete:
                    st.error("Please confirm the deletion first.")
                else:
                    selected_account_delete = delete_account_options[
                        selected_delete_account_label
                    ]
                    try:
                        audit_delete(
                            "chart_of_accounts",
                            selected_account_delete["id"],
                            user.id,
                            selected_account_delete
                        )
                        st.success("Account deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(
                            "Unable to delete account. If it is already used "
                            "in transactions, deactivate it instead. Details: "
                            + str(e)
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

        st.divider()

        # ------------------------------------------------------------
        # SALES ACCOUNTING CONFIGURATION
        # ------------------------------------------------------------

        try:
            sales_chart_accounts = (
                supabase
                .table("chart_of_accounts")
                .select("id, account_code, account_name, account_type")
                .eq("active", True)
                .order("account_code")
                .execute()
                .data
                or []
            )
        except Exception:
            sales_chart_accounts = []

        sales_income_options = {
            f'{a.get("account_code", "")} - {a.get("account_name", "")}': a.get("id")
            for a in sales_chart_accounts
            if a.get("id") and str(a.get("account_type", "")).upper() == "INCOME"
        }

        sales_asset_options = {
            f'{a.get("account_code", "")} - {a.get("account_name", "")}': a.get("id")
            for a in sales_chart_accounts
            if a.get("id") and str(a.get("account_type", "")).upper() == "ASSET"
        }

        sales_gst_options = {
            f'{a.get("account_code", "")} - {a.get("account_name", "")}': a.get("id")
            for a in sales_chart_accounts
            if a.get("id") and str(a.get("account_type", "")).upper() == "LIABILITY"
        }

        # ------------------------------------------------------------
        st.subheader("🗑️ Delete Sales Invoice")

        if sales_invoices:
            sales_delete_options = {
                f'{x.get("invoice_number", "")} | {x.get("customer_name", "")} | '
                f'₹{float(x.get("total_amount") or 0):,.2f}': x
                for x in sales_invoices if x.get("id")
            }

            selected_sales_delete_label = st.selectbox(
                "Select invoice to delete",
                list(sales_delete_options.keys()),
                key="delete_sales_invoice"
            )

            confirm_sales_delete = st.checkbox(
                "Delete the invoice, line items, linked stock movement, "
                "and linked journal where applicable.",
                key="confirm_delete_sales_invoice"
            )

            if st.button(
                "🗑️ Delete Sales Invoice",
                key="delete_sales_invoice_button",
                use_container_width=True
            ):
                if not confirm_sales_delete:
                    st.error("Please confirm the deletion first.")
                else:
                    selected_sales = sales_delete_options[
                        selected_sales_delete_label
                    ]
                    try:
                        journal_ref = selected_sales.get("journal_entry_id")
                        if journal_ref:
                            delete_journal_with_lines(journal_ref, user.id)

                        stock_refs = (
                            supabase
                            .table("stock_movements")
                            .select("*")
                            .eq("reference_no", selected_sales.get("invoice_number"))
                            .eq("direction", "OUT")
                            .eq("notes", f"Sales Invoice {selected_sales.get('invoice_number')}")
                            .execute()
                            .data
                            or []
                        )
                        for stock_ref in stock_refs:
                            audit_delete(
                                "stock_movements",
                                stock_ref["id"],
                                user.id,
                                stock_ref
                            )

                        delete_related_then_audit(
                            "sales_invoices",
                            selected_sales["id"],
                            user.id,
                            related=[{
                                "table": "sales_invoice_items",
                                "column": "sales_invoice_id"
                            }]
                        )
                        st.success("Sales invoice deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unable to delete sales invoice: {e}")

        # CREATE SALES INVOICE
        # ------------------------------------------------------------

        with st.expander("➕ Create Sales Invoice"):

            st.subheader("New Sales Invoice")

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
                    .table("parties")
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

                sales_weight_kg = st.number_input(
                    "Dispatch Weight (KG)",
                    min_value=0.0,
                    step=0.01,
                    value=(
                        float(sales_quantity)
                        if str(selected_item.get("unit", "")).upper() == "KG"
                        else 0.0
                    ),
                    key="sales_weight_kg"
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
                # ACCOUNTING POSTING
                # ----------------------------------------------------

                st.divider()
                st.subheader("🔗 Accounting Posting")

                if not sales_income_options or not sales_asset_options:
                    st.warning(
                        "Create at least one active INCOME ledger and one active "
                        "ASSET ledger in Chart of Accounts to post this sale."
                    )
                    sales_revenue_account_id = None
                    sales_receivable_account_id = None
                    sales_settlement_account_id = None
                    sales_cgst_account_id = None
                    sales_sgst_account_id = None
                    sales_igst_account_id = None
                else:
                    ac1, ac2 = st.columns(2)

                    sales_revenue_label = ac1.selectbox(
                        "Sales Revenue Account",
                        list(sales_income_options.keys()),
                        key="sales_revenue_account"
                    )

                    sales_revenue_account_id = sales_income_options[
                        sales_revenue_label
                    ]

                    sales_receivable_label = ac2.selectbox(
                        "Customer Receivable Account",
                        list(sales_asset_options.keys()),
                        key="sales_receivable_account"
                    )

                    sales_receivable_account_id = sales_asset_options[
                        sales_receivable_label
                    ]

                    sales_settlement_label = st.selectbox(
                        "Cash / Bank Settlement Account",
                        list(sales_asset_options.keys()),
                        key="sales_settlement_account"
                    )

                    sales_settlement_account_id = sales_asset_options[
                        sales_settlement_label
                    ]

                    sales_cgst_account_id = None
                    sales_sgst_account_id = None
                    sales_igst_account_id = None

                    if tax_type == "CGST + SGST" and gst_rate > 0:
                        if not sales_gst_options:
                            st.warning(
                                "No LIABILITY ledger is available for output GST."
                            )
                        else:
                            g1, g2 = st.columns(2)
                            sales_cgst_label = g1.selectbox(
                                "Output CGST Account",
                                list(sales_gst_options.keys()),
                                key="sales_cgst_account"
                            )
                            sales_sgst_label = g2.selectbox(
                                "Output SGST Account",
                                list(sales_gst_options.keys()),
                                key="sales_sgst_account"
                            )
                            sales_cgst_account_id = sales_gst_options[
                                sales_cgst_label
                            ]
                            sales_sgst_account_id = sales_gst_options[
                                sales_sgst_label
                            ]

                    elif tax_type == "IGST" and gst_rate > 0:
                        if not sales_gst_options:
                            st.warning(
                                "No LIABILITY ledger is available for output GST."
                            )
                        else:
                            sales_igst_label = st.selectbox(
                                "Output IGST Account",
                                list(sales_gst_options.keys()),
                                key="sales_igst_account"
                            )
                            sales_igst_account_id = sales_gst_options[
                                sales_igst_label
                            ]

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

                        latest_stock = stock_balance(selected_item["id"])
                        latest_available_qty = latest_stock[2]
                        latest_available_weight = latest_stock[5]

                        if sales_quantity > latest_available_qty:
                            st.error(
                                f"Sale blocked: only {latest_available_qty:g} "
                                f"{selected_item['unit']} is available."
                            )
                        elif sales_weight_kg <= 0:
                            st.error(
                                "Dispatch Weight (KG) is required to connect the sale to stock."
                            )
                        elif sales_weight_kg > latest_available_weight:
                            st.error(
                                f"Sale blocked: only {latest_available_weight:,.2f} KG "
                                "is available."
                            )
                        elif sales_revenue_account_id is None or sales_receivable_account_id is None:
                            st.error(
                                "Select the required Sales Revenue and Asset accounts "
                                "before saving."
                            )
                        elif (
                            tax_type == "CGST + SGST"
                            and gst_rate > 0
                            and (sales_cgst_account_id is None or sales_sgst_account_id is None)
                        ):
                            st.error("Select Output CGST and Output SGST accounts.")
                        elif (
                            tax_type == "IGST"
                            and gst_rate > 0
                            and sales_igst_account_id is None
                        ):
                            st.error("Select an Output IGST account.")
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

                            st.success(
                                f"Sales Invoice "
                                f"{invoice_number.strip()} "
                                f"created successfully."
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

            with st.form(
                "purchase_register_form",
                clear_on_submit=True
            ):

                p1, p2, p3 = st.columns(3)

                bill_no = p1.text_input(
                    "Bill No.",
                    key="purchase_bill_no"
                )

                bill_date = p2.date_input(
                    "Bill Date",
                    key="purchase_bill_date"
                )

                supplier = p3.text_input(
                    "Supplier",
                    key="purchase_supplier"
                )

                p4, p5, p6 = st.columns(3)

                gstin = p4.text_input(
                    "Supplier GSTIN",
                    key="purchase_gstin"
                )

                taxable_value = p5.number_input(
                    "Taxable Value",
                    min_value=0.0,
                    step=0.01,
                    key="purchase_taxable"
                )

                gst_amount = p6.number_input(
                    "GST Amount",
                    min_value=0.0,
                    step=0.01,
                    key="purchase_gst"
                )

                bill_total = st.number_input(
                    "Bill Total",
                    min_value=0.0,
                    step=0.01,
                    key="purchase_total"
                )

                save_purchase = st.form_submit_button(
                    "💾 Save Purchase",
                    use_container_width=True
                )

            if save_purchase:

                if not bill_no.strip():

                    st.error("Please enter the Bill No.")

                elif not supplier.strip():

                    st.error("Please enter the Supplier.")

                elif bill_total <= 0:

                    st.error("Bill total must be greater than zero.")

                else:

                    try:

                        supabase.table(
                            "accounts_purchases"
                        ).insert({
                            "bill_no": bill_no.strip(),
                            "bill_date": bill_date.isoformat(),
                            "supplier": supplier.strip(),
                            "gstin": gstin.strip() or None,
                            "taxable_value": taxable_value,
                            "gst_amount": gst_amount,
                            "bill_total": bill_total,
                            "entered_by": str(user.id)
                        }).execute()

                        st.success(
                            f"Purchase bill {bill_no} saved successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Unable to save purchase: {e}"
                        )

            st.divider()

            try:

                purchases = (
                    supabase
                    .table("accounts_purchases")
                    .select("*")
                    .order("bill_date", desc=True)
                    .limit(100)
                    .execute()
                    .data
                    or []
                )

                if purchases:

                    st.dataframe(
                        purchases,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info("No purchase records yet.")

            except Exception as e:

                st.error(
                    f"Unable to load purchases: {e}"
                )


            # ============================================================
            st.subheader("🗑️ Delete Purchase")

            if purchases:
                purchase_delete_options = {
                    f'{x.get("bill_no", "")} | {x.get("supplier", "")} | '
                    f'₹{float(x.get("bill_total") or 0):,.2f}': x
                    for x in purchases if x.get("id")
                }
                selected_purchase_delete_label = st.selectbox(
                    "Select purchase to delete",
                    list(purchase_delete_options.keys()),
                    key="delete_purchase"
                )
                confirm_purchase_delete = st.checkbox(
                    "Confirm deletion of this purchase record.",
                    key="confirm_delete_purchase"
                )
                if st.button(
                    "🗑️ Delete Purchase",
                    key="delete_purchase_button",
                    use_container_width=True
                ):
                    if not confirm_purchase_delete:
                        st.error("Please confirm the deletion first.")
                    else:
                        selected_purchase = purchase_delete_options[
                            selected_purchase_delete_label
                        ]
                        try:
                            audit_delete(
                                "accounts_purchases",
                                selected_purchase["id"],
                                user.id,
                                selected_purchase
                            )
                            st.success("Purchase deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Unable to delete purchase: {e}")

        # EXPENSES
        # ============================================================

        with reg2:

            st.subheader("💸 Expense Register")

            if not account_options:

                st.warning(
                    "No active Chart of Accounts found. "
                    "Create accounts first."
                )

            else:

                with st.form(
                    "expense_register_form",
                    clear_on_submit=True
                ):

                    # --------------------------------------------------------
                    # BASIC EXPENSE DETAILS
                    # --------------------------------------------------------
                     
                    e1, e2 = st.columns(2)

                    expense_date = e1.date_input(
                        "Expense Date",
                        key="expense_date"
                    )

                    expense_account_label = e2.selectbox(
                        "Expense Account",
                        list(account_options.keys()),
                        key="expense_account"
                    )

                    expense_account_id = account_options[
                        expense_account_label
                    ]

                    # --------------------------------------------------------
                    # DESCRIPTION / PAYMENT MODE
                    # --------------------------------------------------------

                    e3, e4 = st.columns(2)

                    description = e3.text_input(
                        "Description",
                        key="expense_description"
                    )

                    payment_mode = e4.selectbox(
                        "Payment Mode",
                        [
                            "CASH",
                            "BANK",
                            "UPI",
                            "CHEQUE",
                            "CREDIT",
                            "OTHER"
                        ],
                        key="expense_payment_mode"
                    )

                    # --------------------------------------------------------
                    # PAYMENT / CREDIT ACCOUNT
                    # --------------------------------------------------------

                    payment_account_options = {
                        label: account_id
                        for label, account_id in account_options.items()
                    }

                    if payment_account_options:

                        payment_account_label = st.selectbox(
                            "Paid From / Payable Account",
                            list(payment_account_options.keys()),
                            key="expense_payment_account"
                        )

                        payment_account_id = payment_account_options[
                            payment_account_label
                        ]

                    else:

                        payment_account_id = None

                        st.warning(
                            "No Chart of Accounts ledger is available."
                        )

                    # --------------------------------------------------------
                    # AMOUNTS
                    # --------------------------------------------------------

                    e5, e6, e7 = st.columns(3)

                    taxable_value = e5.number_input(
                        "Taxable Value",
                        min_value=0.0,
                        step=0.01,
                        key="expense_taxable"
                    )

                    gst_amount = e6.number_input(
                        "GST Amount",
                        min_value=0.0,
                        step=0.01,
                        key="expense_gst"
                    )

                    total_amount = e7.number_input(
                        "Total Amount",
                        min_value=0.0,
                        step=0.01,
                        key="expense_total"
                    )

                    # --------------------------------------------------------
                    # REFERENCE
                    # --------------------------------------------------------

                    reference_no = st.text_input(
                        "Reference No.",
                        key="expense_reference"
                    )

                    # --------------------------------------------------------
                    # SAVE BUTTON
                    # --------------------------------------------------------

                    save_expense = st.form_submit_button(
                        "💾 Save Expense",
                        use_container_width=True
                    )

    # ============================================================
        # SAVE EXPENSE + POST JOURNAL
        # ============================================================

        if save_expense:

            if not description.strip():

                st.error(
                    "Please enter an expense description."
                )

            elif total_amount <= 0:

                st.error(
                    "Total amount must be greater than zero."
                )

            elif payment_account_id is None:

                st.error(
                    "Please select a Paid From / Payable Account."
                )

            else:

                try:

                    # ------------------------------------------------
                    # SAVE EXPENSE REGISTER
                    # ------------------------------------------------

                    expense_response = (
                        supabase
                        .table("accounts_expenses")
                        .insert({
                            "expense_date":
                                expense_date.isoformat(),

                            "expense_account_id":
                                expense_account_id,

                            "description":
                                description.strip(),

                            "taxable_value":
                                taxable_value,

                            "gst_amount":
                                gst_amount,

                            "total_amount":
                                total_amount,

                            "payment_mode":
                                payment_mode,

                            "reference_no":
                                reference_no.strip() or None,

                            "entered_by":
                                str(user.id)
                        })
                        .execute()
                    )

                    if not expense_response.data:

                        raise Exception(
                            "Expense record could not be created."
                        )

                    created_expense = (
                        expense_response.data[0]
                    )

                    expense_id = created_expense["id"]

                    # ------------------------------------------------
                    # CREATE JOURNAL LINES
                    # ------------------------------------------------

                    journal_lines = [

                        {
                            "account_id":
                                expense_account_id,

                            "party_id":
                                None,

                            "debit":
                                total_amount,

                            "credit":
                                0,

                            "narration":
                                description.strip()
                        },

                        {
                            "account_id":
                                payment_account_id,

                            "party_id":
                                None,

                            "debit":
                                0,

                            "credit":
                                total_amount,

                            "narration":
                                description.strip()
                        }

                    ]

                    # ------------------------------------------------
                    # POST JOURNAL
                    # ------------------------------------------------

                    journal_number = create_journal_entry(
                        entry_date=expense_date,
                        voucher_type="EXPENSE",
                        reference_type="EXPENSE",
                        reference_id=expense_id,
                        narration=description.strip(),
                        lines=journal_lines,
                        entered_by=user.id
                    )

                    st.success(
                        f"Expense recorded successfully. "
                        f"Journal {journal_number} posted."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Unable to save expense and post journal."
                    )

                    st.code(str(e))

        # ============================================================
            # EXPENSE REGISTER
            # ============================================================

            st.divider()

            try:

                expenses = (
                    supabase
                    .table("accounts_expenses")
                    .select("*")
                    .order("expense_date", desc=True)
                    .limit(100)
                    .execute()
                    .data
                    or []
                )

                if expenses:

                    st.dataframe(
                        expenses,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info(
                        "No expense records yet."
                    )

            except Exception as e:

                st.error(
                    f"Unable to load expenses: {e}"
                )


            # ============================================================
            st.subheader("🗑️ Delete Expense")

            if expenses:
                expense_delete_options = {
                    f'{x.get("expense_date")} | {x.get("description", "")} | '
                    f'₹{float(x.get("total_amount") or 0):,.2f}': x
                    for x in expenses if x.get("id")
                }
                selected_expense_delete_label = st.selectbox(
                    "Select expense to delete",
                    list(expense_delete_options.keys()),
                    key="delete_expense"
                )
                confirm_expense_delete = st.checkbox(
                    "Confirm deletion of this expense and its linked journal.",
                    key="confirm_delete_expense"
                )
                if st.button(
                    "🗑️ Delete Expense",
                    key="delete_expense_button",
                    use_container_width=True
                ):
                    if not confirm_expense_delete:
                        st.error("Please confirm the deletion first.")
                    else:
                        selected_expense = expense_delete_options[
                            selected_expense_delete_label
                        ]
                        try:
                            linked_journals = (
                                supabase
                                .table("journal_entries")
                                .select("id")
                                .eq("reference_id", selected_expense["id"])
                                .execute()
                                .data
                                or []
                            )
                            for journal in linked_journals:
                                delete_journal_with_lines(journal["id"], user.id)
                            audit_delete(
                                "accounts_expenses",
                                selected_expense["id"],
                                user.id,
                                selected_expense
                            )
                            st.success("Expense and linked journal deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Unable to delete expense: {e}")

        # RECEIPTS
        # ============================================================

        with reg3:

            st.subheader("💰 Receipt Register")

            with st.form(
                "receipt_register_form",
                clear_on_submit=True
            ):

                r1, r2 = st.columns(2)

                receipt_no = r1.text_input(
                    "Receipt No.",
                    key="receipt_no"
                )

                receipt_date = r2.date_input(
                    "Receipt Date",
                    key="receipt_date"
                )

                r3, r4 = st.columns(2)

                amount = r3.number_input(
                    "Amount Received",
                    min_value=0.0,
                    step=0.01,
                    key="receipt_amount"
                )

                payment_mode = r4.selectbox(
                    "Payment Mode",
                    [
                        "CASH",
                        "BANK",
                        "UPI",
                        "CHEQUE",
                        "OTHER"
                    ],
                    key="receipt_payment_mode"
                )

                narration = st.text_input(
                    "Narration",
                    key="receipt_narration"
                )

                reference_no = st.text_input(
                    "Reference No.",
                    key="receipt_reference"
                )

                bank_account_id = None

                if bank_options:

                    bank_label = st.selectbox(
                        "Cash / Bank Account",
                        ["None"] + list(bank_options.keys()),
                        key="receipt_bank"
                    )

                    if bank_label != "None":

                        bank_account_id = bank_options[
                            bank_label
                        ]

                save_receipt = st.form_submit_button(
                    "💾 Save Receipt",
                    use_container_width=True
                )

            if save_receipt:

                if not receipt_no.strip():

                    st.error("Please enter the Receipt No.")

                elif amount <= 0:

                    st.error(
                        "Receipt amount must be greater than zero."
                    )

                else:

                    try:

                        supabase.table(
                            "accounts_receipts"
                        ).insert({
                            "receipt_no":
                                receipt_no.strip(),

                            "receipt_date":
                                receipt_date.isoformat(),

                            "amount":
                                amount,

                            "payment_mode":
                                payment_mode,

                            "bank_account_id":
                                bank_account_id,

                            "reference_no":
                                reference_no.strip() or None,

                            "narration":
                                narration.strip() or None,

                            "entered_by":
                                str(user.id)
                        }).execute()

                        st.success(
                            "Receipt saved successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Unable to save receipt: {e}"
                        )

            st.divider()

            try:

                receipts = (
                    supabase
                    .table("accounts_receipts")
                    .select("*")
                    .order("receipt_date", desc=True)
                    .limit(100)
                    .execute()
                    .data
                    or []
                )

                if receipts:

                    st.dataframe(
                        receipts,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info("No receipt records yet.")

            except Exception as e:

                st.error(
                    f"Unable to load receipts: {e}"
                )


            st.subheader("🗑️ Delete Receipt")

            if receipts:
                receipt_delete_options = {
                    f'{x.get("receipt_no", "")} | {x.get("receipt_date")} | '
                    f'₹{float(x.get("amount") or 0):,.2f}': x
                    for x in receipts if x.get("id")
                }
                selected_receipt_delete_label = st.selectbox(
                    "Select receipt to delete",
                    list(receipt_delete_options.keys()),
                    key="delete_receipt"
                )
                confirm_receipt_delete = st.checkbox(
                    "Confirm deletion of this receipt record.",
                    key="confirm_delete_receipt"
                )
                if st.button(
                    "🗑️ Delete Receipt",
                    key="delete_receipt_button",
                    use_container_width=True
                ):
                    if not confirm_receipt_delete:
                        st.error("Please confirm the deletion first.")
                    else:
                        selected_receipt = receipt_delete_options[
                            selected_receipt_delete_label
                        ]
                        try:
                            audit_delete(
                                "accounts_receipts",
                                selected_receipt["id"],
                                user.id,
                                selected_receipt
                            )
                            st.success("Receipt deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Unable to delete receipt: {e}")


        # ============================================================
        # PAYMENTS
        # ============================================================

        with reg4:

            st.subheader("💳 Payment Register")

            with st.form(
                "payment_register_form",
                clear_on_submit=True
            ):

                pay1, pay2 = st.columns(2)

                payment_no = pay1.text_input(
                    "Payment No.",
                    key="payment_no"
                )

                payment_date = pay2.date_input(
                    "Payment Date",
                    key="payment_date"
                )

                pay3, pay4 = st.columns(2)

                amount = pay3.number_input(
                    "Amount Paid",
                    min_value=0.0,
                    step=0.01,
                    key="payment_amount"
                )

                payment_mode = pay4.selectbox(
                    "Payment Mode",
                    [
                        "CASH",
                        "BANK",
                        "UPI",
                        "CHEQUE",
                        "OTHER"
                    ],
                    key="payment_payment_mode"
                )

                narration = st.text_input(
                    "Narration",
                    key="payment_narration"
                )

                reference_no = st.text_input(
                    "Reference No.",
                    key="payment_reference"
                )

                bank_account_id = None

                if bank_options:

                    bank_label = st.selectbox(
                        "Cash / Bank Account",
                        ["None"] + list(bank_options.keys()),
                        key="payment_bank"
                    )

                    if bank_label != "None":

                        bank_account_id = bank_options[
                            bank_label
                        ]

                save_payment = st.form_submit_button(
                    "💾 Save Payment",
                    use_container_width=True
                )

            if save_payment:

                if not payment_no.strip():

                    st.error("Please enter the Payment No.")

                elif amount <= 0:

                    st.error(
                        "Payment amount must be greater than zero."
                    )

                else:

                    try:

                        supabase.table(
                            "accounts_payments"
                        ).insert({
                            "payment_no":
                                payment_no.strip(),

                            "payment_date":
                                payment_date.isoformat(),

                            "amount":
                                amount,

                            "payment_mode":
                                payment_mode,

                            "bank_account_id":
                                bank_account_id,

                            "reference_no":
                                reference_no.strip() or None,

                            "narration":
                                narration.strip() or None,

                            "entered_by":
                                str(user.id)
                        }).execute()

                        st.success(
                            "Payment saved successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Unable to save payment: {e}"
                        )

            st.divider()

            try:

                payments = (
                    supabase
                    .table("accounts_payments")
                    .select("*")
                    .order("payment_date", desc=True)
                    .limit(100)
                    .execute()
                    .data
                    or []
                )

                if payments:

                    st.dataframe(
                        payments,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info("No payment records yet.")

            except Exception as e:

                st.error(
                    f"Unable to load payments: {e}"
                )


            st.subheader("🗑️ Delete Payment")

            if payments:
                payment_delete_options = {
                    f'{x.get("payment_no", "")} | {x.get("payment_date")} | '
                    f'₹{float(x.get("amount") or 0):,.2f}': x
                    for x in payments if x.get("id")
                }
                selected_payment_delete_label = st.selectbox(
                    "Select payment to delete",
                    list(payment_delete_options.keys()),
                    key="delete_payment"
                )
                confirm_payment_delete = st.checkbox(
                    "Confirm deletion of this payment record.",
                    key="confirm_delete_payment"
                )
                if st.button(
                    "🗑️ Delete Payment",
                    key="delete_payment_button",
                    use_container_width=True
                ):
                    if not confirm_payment_delete:
                        st.error("Please confirm the deletion first.")
                    else:
                        selected_payment = payment_delete_options[
                            selected_payment_delete_label
                        ]
                        try:
                            audit_delete(
                                "accounts_payments",
                                selected_payment["id"],
                                user.id,
                                selected_payment
                            )
                            st.success("Payment deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Unable to delete payment: {e}")


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

                else:

                    st.info(
                        "No Cash / Bank accounts created yet."
                    )

            except Exception as e:

                st.error(
                    f"Unable to load Cash / Bank accounts: {e}"
                )



            st.subheader("🗑️ Delete Cash / Bank Account")

            if bank_accounts:
                bank_delete_options = {
                    f'{x.get("account_name", "")} ({x.get("account_type", "")})': x
                    for x in bank_accounts if x.get("id")
                }
                selected_bank_delete_label = st.selectbox(
                    "Select Cash / Bank account to delete",
                    list(bank_delete_options.keys()),
                    key="delete_cash_bank"
                )
                confirm_bank_delete = st.checkbox(
                    "Confirm deletion of this Cash / Bank account.",
                    key="confirm_delete_cash_bank"
                )
                if st.button(
                    "🗑️ Delete Cash / Bank Account",
                    key="delete_cash_bank_button",
                    use_container_width=True
                ):
                    if not confirm_bank_delete:
                        st.error("Please confirm the deletion first.")
                    else:
                        selected_bank = bank_delete_options[
                            selected_bank_delete_label
                        ]
                        try:
                            audit_delete(
                                "cash_bank_accounts",
                                selected_bank["id"],
                                user.id,
                                selected_bank
                            )
                            st.success("Cash / Bank account deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Unable to delete Cash / Bank account: {e}")


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

                st.subheader("🗑️ Delete Journal Entry")

                journal_delete_options = {
                    f'{j.get("entry_no", "")} | {j.get("entry_date")} | '
                    f'{j.get("narration", "")}': j
                    for j in journal_entries if j.get("id")
                }

                selected_journal_delete_label = st.selectbox(
                    "Select journal entry to delete",
                    list(journal_delete_options.keys()),
                    key="delete_journal_entry"
                )

                confirm_journal_delete = st.checkbox(
                    "Confirm deletion of this journal entry and its lines.",
                    key="confirm_delete_journal_entry"
                )

                if st.button(
                    "🗑️ Delete Journal Entry",
                    key="delete_journal_entry_button",
                    use_container_width=True
                ):
                    if not confirm_journal_delete:
                        st.error("Please confirm the deletion first.")
                    else:
                        selected_journal = journal_delete_options[
                            selected_journal_delete_label
                        ]
                        try:
                            delete_journal_with_lines(
                                selected_journal["id"],
                                user.id
                            )
                            st.success("Journal entry and lines deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Unable to delete journal entry: {e}")


            else:

                st.info(
                    "No journal entries recorded yet."
                )




# ---------------------------------------------------------------------
# DOCUMENTS
# ---------------------------------------------------------------------

elif page == "Documents":

    st.title("📁 Document Register")

    st.write(
        "Maintain a central register for GST, ITR, trade licence, "
        "professional tax, lease, electricity, bank, loan, insurance "
        "and other business documents."
    )

    st.caption(
        "The register stores document metadata and an optional secure "
        "document link / storage path."
    )

    try:
        documents = (
            supabase
            .table("business_documents")
            .select("*")
            .order("expiry_date", desc=False)
            .execute()
            .data
            or []
        )
    except Exception:
        documents = []
        st.warning(
            "Document Register is not configured yet. Run the supplied "
            "Document Register SQL in Supabase first."
        )

    today = date.today()
    expired = sum(
        1 for d in documents
        if d.get("expiry_date")
        and str(d.get("expiry_date")) < today.isoformat()
    )
    due_30 = sum(
        1 for d in documents
        if d.get("expiry_date")
        and today.isoformat() <= str(d.get("expiry_date"))
        <= (today + timedelta(days=30)).isoformat()
    )

    d1, d2, d3 = st.columns(3)
    d1.metric("Total Documents", len(documents))
    d2.metric("Expired", expired)
    d3.metric("Due Within 30 Days", due_30)

    st.divider()

    with st.expander("➕ Add Business Document", expanded=True):

        with st.form("document_register_form", clear_on_submit=True):

            d1, d2, d3 = st.columns(3)

            document_type = d1.selectbox(
                "Document Type",
                [
                    "GST",
                    "ITR",
                    "TRADE_LICENCE",
                    "PROFESSIONAL_TAX",
                    "LEASE",
                    "ELECTRICITY",
                    "BANK",
                    "LOAN",
                    "INSURANCE",
                    "OTHER"
                ],
                key="document_type"
            )

            document_name = d2.text_input(
                "Document Name",
                placeholder="Example: GST Registration Certificate",
                key="document_name"
            )

            reference_no = d3.text_input(
                "Reference / Document No.",
                key="document_reference"
            )

            d4, d5, d6 = st.columns(3)

            issue_date = d4.date_input(
                "Issue Date",
                value=today,
                key="document_issue_date"
            )

            expiry_date = d5.date_input(
                "Expiry / Renewal Date",
                value=today,
                key="document_expiry_date"
            )

            status = d6.selectbox(
                "Status",
                ["ACTIVE", "EXPIRED", "PENDING", "RENEWED", "ARCHIVED"],
                key="document_status"
            )

            document_url = st.text_input(
                "Document Link / Storage Path (optional)",
                placeholder="Paste the secure document URL or storage path",
                key="document_url"
            )

            notes = st.text_area(
                "Notes",
                key="document_notes"
            )

            save_document = st.form_submit_button(
                "💾 Save Document",
                use_container_width=True
            )

        if save_document:
            if not document_name.strip():
                st.error("Document name is required.")
            else:
                try:
                    supabase.table("business_documents").insert({
                        "document_type": document_type,
                        "document_name": document_name.strip(),
                        "reference_no": reference_no.strip() or None,
                        "issue_date": issue_date.isoformat(),
                        "expiry_date": expiry_date.isoformat(),
                        "status": status,
                        "document_url": document_url.strip() or None,
                        "notes": notes.strip() or None,
                        "entered_by": str(user.id)
                    }).execute()
                    st.success("Document registered successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Unable to save document: {e}")

    st.divider()
    st.subheader("📋 Document Register")

    if documents:
        display_documents = []
        for document in documents:
            expiry = document.get("expiry_date")
            if expiry and str(expiry) < today.isoformat():
                display_status = "🔴 EXPIRED"
            elif (
                expiry
                and str(expiry)
                <= (today + timedelta(days=30)).isoformat()
            ):
                display_status = "🟠 DUE SOON"
            else:
                display_status = document.get("status") or "ACTIVE"

            display_documents.append({
                "Document Type": document.get("document_type"),
                "Document Name": document.get("document_name"),
                "Reference No.": document.get("reference_no"),
                "Issue Date": document.get("issue_date"),
                "Expiry / Renewal": expiry,
                "Status": display_status,
                "Document Link": document.get("document_url"),
                "Notes": document.get("notes")
            })

        st.dataframe(
            display_documents,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("🗑️ Delete Document")

        document_delete_options = {
            f'{d.get("document_name", "")} | {d.get("document_type", "")} | '
            f'{d.get("reference_no") or "No Ref"}': d
            for d in documents if d.get("id")
        }

        selected_document_delete_label = st.selectbox(
            "Select document to delete",
            list(document_delete_options.keys()),
            key="delete_document"
        )

        confirm_document_delete = st.checkbox(
            "Confirm deletion of this document record.",
            key="confirm_delete_document"
        )

        if st.button(
            "🗑️ Delete Document",
            key="delete_document_button",
            use_container_width=True
        ):
            if not confirm_document_delete:
                st.error("Please confirm the deletion first.")
            else:
                selected_document = document_delete_options[
                    selected_document_delete_label
                ]
                try:
                    audit_delete(
                        "business_documents",
                        selected_document["id"],
                        user.id,
                        selected_document
                    )
                    st.success("Document record deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Unable to delete document: {e}")

    else:
        st.info("No business documents registered yet.")

