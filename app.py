import hashlib
from datetime import date
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="S.P. Enterprise Control System", page_icon="📊", layout="wide")

@st.cache_resource
def db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])

try:
    supabase = db()
except Exception:
    st.error("Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to Streamlit secrets.")
    st.stop()

def fp(*parts):
    raw = "||".join("" if x is None else str(x).strip().upper() for x in parts)
    return hashlib.sha256(raw.encode()).hexdigest()

def stock_balance(item_id):
    rows = supabase.table("stock_movements").select("direction,quantity").eq("item_id", item_id).execute().data
    incoming = sum(float(x["quantity"]) for x in rows if x["direction"] == "IN")
    outgoing = sum(float(x["quantity"]) for x in rows if x["direction"] == "OUT")
    return incoming, outgoing, incoming - outgoing

if "user" not in st.session_state:
    st.title("S.P. Enterprise")
    st.subheader("Cloud Accounts & Stock Control")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        try:
            r = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = r.user
            st.rerun()
        except Exception:
            st.error("Login failed. Check the credentials.")
    st.stop()

user = st.session_state.user

with st.sidebar:
    st.title("S.P. Enterprise")
    st.caption(user.email)
    page = st.radio("Module", ["Dashboard", "Stock Control", "Accounts", "Documents"])
    if st.button("Sign out"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

if page == "Dashboard":
    st.title("📊 Control Dashboard")
    items = supabase.table("stock_items").select("*").eq("active", True).execute().data
    a,b,c = st.columns(3)
    a.metric("Active Stock Items", len(items))
    try:
        r = supabase.table("stock_movements").select("id", count="exact").execute()
        b.metric("Stock Movements", r.count or 0)
    except Exception:
        b.metric("Stock Movements", "—")
    c.metric("System", "Cloud")
    st.info("Management dashboard: stock, receivables, payables, cash/bank, loans and GST will be added in the Accounts phase.")

elif page == "Stock Control":
    st.title("📦 Stock Control")
    st.caption("Every physical movement must be recorded. Exact duplicates are blocked at database level.")

    items = supabase.table("stock_items").select("*").eq("active", True).order("name").execute().data
    tab1, tab2, tab3 = st.tabs(["Record Movement", "Current Stock", "Movement Register"])

    with tab1:
        if not items:
            st.warning("Add stock items first in Current Stock.")
        else:
            lookup = {f'{x["name"]} ({x["unit"]})': x for x in items}
            with st.form("movement", clear_on_submit=True):
                c1,c2,c3 = st.columns(3)
                d = c1.date_input("Movement date", date.today())
                label = c2.selectbox("Item", list(lookup))
                direction = c3.selectbox("Movement", ["IN","OUT"])
                c1,c2,c3 = st.columns(3)
                qty = c1.number_input("Quantity", min_value=0.001, step=1.0)
                ref = c2.text_input("Invoice / Challan / Gate Pass No.")
                party = c3.text_input("Supplier / Customer / Destination")
                c1,c2,c3 = st.columns(3)
                vehicle = c1.text_input("Vehicle No.")
                handler = c2.text_input("Handled by / Driver")
                notes = c3.text_input("Notes")
                save = st.form_submit_button("Save Movement", type="primary")
                if save:
                    item = lookup[label]
                    if direction == "OUT" and qty > stock_balance(item["id"])[2]:
                        st.error(f"Blocked: recorded balance is only {stock_balance(item['id'])[2]:g} {item['unit']}.")
                    else:
                        data = {
                            "movement_date": str(d), "item_id": item["id"], "direction": direction,
                            "quantity": qty, "reference_no": ref.strip() or None,
                            "party": party.strip() or None, "vehicle_no": vehicle.strip() or None,
                            "handled_by": handler.strip() or None, "notes": notes.strip() or None,
                            "entered_by": str(user.id),
                            "duplicate_fingerprint": fp(d, item["id"], direction, qty, ref, party, vehicle)
                        }
                        try:
                            supabase.table("stock_movements").insert(data).execute()
                            st.success("Movement recorded.")
                        except Exception as e:
                            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                                st.error("Blocked: this movement appears to have already been entered.")
                            else:
                                st.error(str(e))

    with tab2:
        rows = []
        for x in items:
            i,o,b = stock_balance(x["id"])
            rows.append({"Item":x["name"],"Unit":x["unit"],"Total In":i,"Total Out":o,
                         "Current Balance":b,"Minimum Level":x["minimum_level"],
                         "Status":"⚠️ LOW" if b <= float(x["minimum_level"]) else "OK"})
        st.dataframe(rows, use_container_width=True, hide_index=True)
        with st.expander("Add stock item"):
            with st.form("new_item"):
                name = st.text_input("Item name")
                unit = st.selectbox("Unit", ["PCS","KG","TON","MTR","BOX","BAG","OTHER"])
                minimum = st.number_input("Minimum stock level", min_value=0.0, step=1.0)
                if st.form_submit_button("Add item"):
                    try:
                        supabase.table("stock_items").insert({"name":name.strip(),"unit":unit,"minimum_level":minimum,"active":True}).execute()
                        st.success("Item added.")
                        st.rerun()
                    except Exception as e: st.error(str(e))

    with tab3:
        rows = supabase.table("stock_movements").select(
            "movement_date,direction,quantity,reference_no,party,vehicle_no,handled_by,notes,stock_items(name,unit)"
        ).order("movement_date", desc=True).limit(1000).execute().data
        out=[]
        for r in rows:
            item=r.get("stock_items") or {}
            out.append({"Date":r["movement_date"],"Movement":r["direction"],"Item":item.get("name"),
                        "Qty":r["quantity"],"Unit":item.get("unit"),"Reference":r.get("reference_no"),
                        "Party/Destination":r.get("party"),"Vehicle":r.get("vehicle_no"),
                        "Handled By":r.get("handled_by"),"Notes":r.get("notes")})
        st.dataframe(out, use_container_width=True, hide_index=True)

elif page == "Accounts":
    st.title("💰 Accounts")
    st.write("Planned registers: Sales, Purchases, Expenses, Receipts, Payments, Bank/Cash, Loans & EMI, GST and Documents.")
    st.warning("Next build phase will connect these registers to the same cloud database and duplicate-control system.")

elif page == "Documents":
    st.title("📁 Document Register")
    st.write("Index GST, ITR, trade licence, professional tax, lease, electricity, bank, loan and other business documents.")
    st.caption("Sensitive documents should be restricted by user role.")
