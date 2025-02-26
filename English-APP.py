import streamlit as st
import cv2
import pytesseract
import sqlite3
import pandas as pd
import os
from datetime import datetime

# 🛠 Windows needs to specify Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\85298\tesseract.exe'  # Change path for Windows users

# 💾 Connect to Database
def connect_db():
    conn = sqlite3.connect("medicine.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            location TEXT,
            category TEXT,
            expiry_date TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

# 📸 Preprocess Image
def preprocess_image(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

# 📸 OCR Recognition
def scan_medicine(img_path):
    processed_img = preprocess_image(img_path)
    text = pytesseract.image_to_string(processed_img, lang='chi_sim+eng', config='--psm 7 --oem 3').strip()
    return text if text else None

# ✅ Store Medicine
def store_medicine(name, location, category, expiry_date):
    conn, cursor = connect_db()
    try:
        cursor.execute("INSERT INTO medicine (name, location, category, expiry_date) VALUES (?, ?, ?, ?)", 
                       (name, location, category, expiry_date))
        conn.commit()
        st.success(f"✅ Medicine `{name}` has been stored in `{location}`!")
    except sqlite3.IntegrityError:
        st.warning(f"⚠️ Medicine `{name}` already exists. Storage failed.")
    conn.close()

# ✅ Query All Medicines
def query_medicine():
    conn, cursor = connect_db()
    cursor.execute("SELECT * FROM medicine")
    results = cursor.fetchall()
    conn.close()
    return results

# ✅ Delete Medicine
def delete_medicine(name):
    conn, cursor = connect_db()
    cursor.execute("DELETE FROM medicine WHERE name=?", (name,))
    conn.commit()
    conn.close()
    st.error(f"🗑 `{name}` has been deleted!")

# ✅ Take Out Medicine
def take_out_medicine():
    st.subheader("➖ Take Out Medicine")

    medicines = query_medicine()
    if not medicines:
        st.warning("📭 No medicines stored in the database.")
        return

    medicine_options = {row[1]: row[2] for row in medicines}  # {Medicine Name: Storage Location}
    selected_medicine = st.selectbox("🔍 Select the medicine to take out", list(medicine_options.keys()))

    if selected_medicine:
        location = medicine_options[selected_medicine]
        st.info(f"📍 **Go to `{location}` to take out `{selected_medicine}`**")

        full_take_out = st.radio("❓ Take out the entire medicine?", ["No, only partially", "Yes, remove completely"])
        
        if full_take_out == "Yes, remove completely":
            if st.button("🗑 Confirm Deletion"):
                delete_medicine(selected_medicine)
                st.success(f"✅ `{selected_medicine}` has been completely removed from the database.")
        else:
            st.success(f"✅ `{selected_medicine}` was partially taken out. Information is retained.")

# ✅ Export Data
def export_data():
    conn, cursor = connect_db()
    df = pd.read_sql_query("SELECT * FROM medicine", conn)
    conn.close()
    df.to_csv("medicine_backup.csv", index=False, encoding="utf-8-sig")
    st.success("✅ Data has been successfully exported to `medicine_backup.csv`")

# ✅ Import Data
def import_data(file):
    conn, cursor = connect_db()
    df = pd.read_csv(file)
    df.to_sql("medicine", conn, if_exists="append", index=False)
    conn.close()
    st.success("✅ Data has been successfully imported into the database!")

# ✅ Streamlit UI
st.set_page_config(page_title="Medicine Management System", page_icon="💊", layout="wide")
st.title("💊 **Medicine Management System**")

# 📌 Select Action
menu = st.sidebar.radio("🔹 Choose an option", ["📥 Store Medicine", "🔍 Query Medicines", "➖ Take Out Medicine", "🗑 Delete Medicine", "📤 Export Data", "📥 Import Data"])

# 📥 Store Medicine
if menu == "📥 Store Medicine":
    st.subheader("📥 Store Medicine Information")

    uploaded_file = st.file_uploader("📸 Upload medicine image for OCR recognition", type=["jpg", "png"])
    name = ""

    if uploaded_file:
        img_path = "temp.jpg"
        with open(img_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.image(img_path, caption="🧐 Recognizing...", use_column_width=True)
        name = scan_medicine(img_path)

        if name:
            st.success(f"🔍 Recognition Result: `{name}`")
        else:
            st.warning("⚠️ Recognition failed. Please enter manually.")

    name = st.text_input("Medicine Name", value=name)
    location = st.selectbox("Storage Location", ["A1", "B2", "C3"])
    category = st.selectbox("Category", ["Traditional Chinese Medicine", "Western Medicine", "Health Products"])
    expiry_date = st.date_input("Expiration Date")

    if st.button("✅ Store Medicine"):
        if name.strip():
            store_medicine(name, location, category, expiry_date)
        else:
            st.warning("⚠️ Medicine name cannot be empty.")

# ➖ Take Out Medicine
elif menu == "➖ Take Out Medicine":
    take_out_medicine()

# 🔍 Query Medicines
elif menu == "🔍 Query Medicines":
    st.subheader("🔍 Query All Medicines")
    medicines = query_medicine()
    if medicines:
        df = pd.DataFrame(medicines, columns=["ID", "Medicine Name", "Storage Location", "Category", "Expiration Date"])
        st.dataframe(df)
    else:
        st.warning("📭 No medicines stored.")

# 🗑 Delete Medicine
elif menu == "🗑 Delete Medicine":
    st.subheader("🗑 Delete Medicine")
    medicines = query_medicine()
    if medicines:
        options = [row[1] for row in medicines]
        name = st.selectbox("Select medicine to delete", options)
        if st.button("🗑 Confirm Delete"):
            delete_medicine(name)
    else:
        st.warning("📭 No medicines stored.")

# 📤 Export Data
elif menu == "📤 Export Data":
    st.subheader("📤 Export Medicine Data")
    if st.button("📤 Export CSV"):
        export_data()
        st.download_button("📥 Download CSV", data=open("medicine_backup.csv", "rb"), file_name="medicine_backup.csv")

# 📥 Import Data
elif menu == "📥 Import Data":
    st.subheader("📥 Import Medicine Data")
    uploaded_file = st.file_uploader("📤 Upload CSV File", type=["csv"])
    if uploaded_file and st.button("📥 Import Data"):
        import_data(uploaded_file)