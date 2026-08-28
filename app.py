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
