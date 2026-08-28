import hashlib
from datetime import date
import streamlit as st
from supabase import create_client

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

    st.info(
        "Stock Control is the active build phase. "
        "Accounts and Documents will be connected later."
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
        "Record Movement",
        "Current Stock",
        "Parties",
        "Party Ledger",
        "Movement Register"
    ])


 # -----------------------------------------------------------------
 # TAB 1 - RECORD MOVEMENT / DISPATCH
 # -----------------------------------------------------------------

    with tab1:

        if not items:
            st.warning("Add stock items first in Current Stock.")

        elif not parties:
            st.warning(
                "Add at least one company/party first in the Parties tab."
            )

        else:

            # ---------------------------------------------------------
            # STEP 1 - SELECT TRANSACTION TYPE
            # ---------------------------------------------------------

            st.subheader("Record Stock Movement")

            direction = st.radio(
                "Transaction Type",
                ["IN", "OUT"],
                horizontal=True,
                key="movement_direction"
            )

            if direction == "OUT":
                st.caption(
                    "🚚 OUT / DISPATCH: Record material leaving the stock "
                    "for a customer or other destination."
                )
            else:
                st.caption(
                    "📥 IN / RECEIPT: Record material received from a "
                    "supplier or other source."
                )

            # ---------------------------------------------------------
            # FILTER PARTIES ACCORDING TO TRANSACTION TYPE
            # ---------------------------------------------------------

            if direction == "OUT":

                available_parties = [
                    p for p in parties
                    if p["party_type"] in ["CUSTOMER", "BOTH"]
                ]

            else:

                available_parties = [
                    p for p in parties
                    if p["party_type"] in ["SUPPLIER", "BOTH"]
                ]

            if not available_parties:

                if direction == "OUT":
                    st.warning(
                        "No customer is available. Add a CUSTOMER or "
                        "BOTH party in the Parties tab first."
                    )
                else:
                    st.warning(
                        "No supplier is available. Add a SUPPLIER or "
                        "BOTH party in the Parties tab first."
                    )

            else:

                filtered_party_lookup = {
                    f'{x["name"]} [{x["party_type"]}]': x
                    for x in available_parties
                }

                # -----------------------------------------------------
                # STEP 2 - TRANSACTION FORM
                # -----------------------------------------------------

                with st.form(
                    "movement",
                    clear_on_submit=True
                ):

                    st.subheader(
                        "🚚 Dispatch Details"
                        if direction == "OUT"
                        else "📥 Receipt Details"
                    )

                    # -------------------------------------------------
                    # BASIC DETAILS
                    # -------------------------------------------------

                    c1, c2, c3 = st.columns(3)

                    movement_date = c1.date_input(
                        "Movement date",
                        date.today()
                    )

                    item_label = c2.selectbox(
                        "Item",
                        list(lookup_items)
                    )

                    party_label = c3.selectbox(
                        "Company / Party",
                        list(filtered_party_lookup)
                    )

                    item = lookup_items[item_label]
                    party = filtered_party_lookup[party_label]

                    # -------------------------------------------------
                    # SHOW CURRENT STOCK BEFORE TRANSACTION
                    # -------------------------------------------------

                    (
                        incoming_qty,
                        outgoing_qty,
                        balance_qty,
                        incoming_weight,
                        outgoing_weight,
                        balance_weight
                    ) = stock_balance(item["id"])

                    if direction == "OUT":

                        st.markdown("### Available Stock")

                        s1, s2, s3 = st.columns(3)

                        s1.metric(
                            "Available Quantity",
                            f"{balance_qty:g} {item['unit']}"
                        )

                        s2.metric(
                            "Available Weight",
                            f"{balance_weight:,.2f} KG"
                        )

                        s3.metric(
                            "Minimum Level",
                            f"{float(item['minimum_level']):g}"
                        )

                    # -------------------------------------------------
                    # DOCUMENT / VEHICLE DETAILS
                    # -------------------------------------------------

                    c1, c2, c3 = st.columns(3)

                    reference_no = c1.text_input(
                        "Invoice / Challan / Gate Pass No. *"
                    )

                    vehicle_no = c2.text_input(
                        "Vehicle No."
                    )

                    handler = c3.text_input(
                        "Handled by / Driver"
                    )

                    # -------------------------------------------------
                    # PHYSICAL STOCK DETAILS
                    # -------------------------------------------------

                    c1, c2, c3 = st.columns(3)

                    quantity = c1.number_input(
                        "Quantity / PCS",
                        min_value=0.001,
                        step=1.0
                    )

                    bags = c2.number_input(
                        "No. of Bags",
                        min_value=0.0,
                        step=1.0
                    )

                    weight_kg = c3.number_input(
                        "Weight (KG)",
                        min_value=0.0,
                        step=1.0
                    )

                    # -------------------------------------------------
                    # COMMERCIAL DETAILS
                    # -------------------------------------------------

                    c1, c2, c3 = st.columns(3)

                    rate_per_kg = c1.number_input(
                        "Rate per KG (₹)",
                        min_value=0.0,
                        step=0.50
                    )

                    transportation = c2.number_input(
                        "Transportation (₹)",
                        min_value=0.0,
                        step=1.0
                    )

                    notes = c3.text_input(
                        "Notes"
                    )

                    # -------------------------------------------------
                    # BILLING CALCULATION
                    # -------------------------------------------------

                    billing_amount = weight_kg * rate_per_kg

                    st.markdown("### Transaction Summary")

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
                        "Material Value = Weight × Rate per KG. "
                        "Transportation is recorded separately. "
                        "Accounts/receivables will be connected later."
                    )

                    # -------------------------------------------------
                    # SAVE
                    # -------------------------------------------------

                    save = st.form_submit_button(
                        "Save Dispatch" if direction == "OUT"
                        else "Save Receipt",
                        type="primary"
                    )

                    if save:

                        # -------------------------------------------------
                        # VALIDATION 1 - REFERENCE
                        # -------------------------------------------------

                        if not reference_no.strip():

                            st.error(
                                "Invoice / Challan / Gate Pass No. "
                                "is required."
                            )

                        # -------------------------------------------------
                        # VALIDATION 2 - QUANTITY
                        # -------------------------------------------------

                        elif direction == "OUT" and quantity > balance_qty:

                            st.error(
                                f"Dispatch blocked: available stock is only "
                                f"{balance_qty:g} {item['unit']}, but you "
                                f"entered {quantity:g}."
                            )

                        # -------------------------------------------------
                        # VALIDATION 3 - WEIGHT
                        # -------------------------------------------------

                        elif direction == "OUT" and weight_kg > balance_weight:

                            st.error(
                                f"Dispatch blocked: available weight is only "
                                f"{balance_weight:,.2f} KG, but you entered "
                                f"{weight_kg:,.2f} KG."
                            )

                        # -------------------------------------------------
                        # VALIDATION 4 - POSITIVE VALUES
                        # -------------------------------------------------

                        elif quantity <= 0:

                            st.error(
                                "Quantity must be greater than zero."
                            )

                        elif direction == "OUT" and weight_kg <= 0:

                            st.error(
                                "Weight is required for an OUT / DISPATCH "
                                "transaction."
                            )

                        else:

                            # -------------------------------------------------
                            # DUPLICATE FINGERPRINT
                            # -------------------------------------------------

                            fingerprint = fp(
                                movement_date,
                                item["id"],
                                party["id"],
                                direction,
                                quantity,
                                bags,
                                weight_kg,
                                reference_no
                            )

                            # -------------------------------------------------
                            # DATABASE RECORD
                            # -------------------------------------------------

                            data = {
                                "movement_date":
                                    str(movement_date),

                                "item_id":
                                    item["id"],

                                "party_id":
                                    party["id"],

                                "direction":
                                    direction,

                                "quantity":
                                    quantity,

                                "bags":
                                    bags,

                                "weight_kg":
                                    weight_kg,

                                "rate_per_kg":
                                    rate_per_kg,

                                "transportation":
                                    transportation,

                                "billing_amount":
                                    billing_amount,

                                "reference_no":
                                    reference_no.strip(),

                                "vehicle_no":
                                    vehicle_no.strip() or None,

                                "handled_by":
                                    handler.strip() or None,

                                "notes":
                                    notes.strip() or None,

                                "entered_by":
                                    str(user.id),

                                "duplicate_fingerprint":
                                    fingerprint
                            }

                            # -------------------------------------------------
                            # SAVE TO SUPABASE
                            # -------------------------------------------------

                            try:

                                (
                                    supabase
                                    .table("stock_movements")
                                    .insert(data)
                                    .execute()
                                )

                                if direction == "OUT":

                                    st.success(
                                        "✅ Dispatch recorded successfully. "
                                        "Stock has been updated."
                                    )

                                else:

                                    st.success(
                                        "✅ Stock receipt recorded "
                                        "successfully."
                                    )

                                st.info(
                                    f"{item['name']} | "
                                    f"{quantity:g} {item['unit']} | "
                                    f"{weight_kg:,.2f} KG | "
                                    f"{party['name']}"
                                )

                            except Exception as e:

                                error_text = str(e).lower()

                                if (
                                    "duplicate" in error_text
                                    or "unique" in error_text
                                ):

                                    st.error(
                                        "Blocked: this transaction appears "
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


# ---------------------------------------------------------------------
# ACCOUNTS
# ---------------------------------------------------------------------

elif page == "Accounts":

    st.title("💰 Accounts")

    st.write(
        "Planned registers: Sales, Purchases, Expenses, Receipts, "
        "Payments, Bank/Cash, Loans & EMI, GST and Documents."
    )

    st.warning(
        "Accounts will be connected to the same Party and transaction "
        "database in the next build phase."
    )


# ---------------------------------------------------------------------
# DOCUMENTS
# ---------------------------------------------------------------------

elif page == "Documents":

    st.title("📁 Document Register")

    st.write(
        "Index GST, ITR, trade licence, professional tax, lease, "
        "electricity, bank, loan and other business documents."
    )

    st.caption(
        "Sensitive documents should be restricted by user role."
    )
