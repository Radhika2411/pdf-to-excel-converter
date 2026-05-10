import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="ICICI Statement Converter", layout="wide")
st.title("🏦 ICICI Bank PDF to Excel Converter")

uploaded_file = st.file_uploader("Upload your ICICI PDF Statement", type="pdf")

def is_date(text):
    """Checks if a cell matches the DD-MM-YYYY format."""
    if not text or not isinstance(text, str): return False
    return bool(re.match(r'\d{2}-\d{2}-\d{4}', text.strip()))

if uploaded_file is not None:
    with st.spinner('Processing pages... please wait.'):
        raw_rows = []
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 3
                })
                
                if table:
                    for row in table:
                        # Clean extra spaces and newlines
                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        # Skip empty rows or page headers
                        if not any(clean_row) or clean_row[0].upper() == "DATE":
                            continue
                        raw_rows.append(clean_row)

        # --- SAFER MERGE LOGIC ---
        final_transactions = []
        current_tx = None

        for row in raw_rows:
            # Check only the FIRST cell for a date
            if is_date(row[0]):
                if current_tx:
                    final_transactions.append(current_tx)
                current_tx = list(row)
            elif current_tx:
                # Merge safely: loop only up to the shorter of the two rows
                for i in range(min(len(row), len(current_tx))):
                    if row[i]:
                        # Combine text with a space
                        current_tx[i] = f"{current_tx[i]} {row[i]}".strip()

        # Add the last transaction
        if current_tx:
            final_transactions.append(current_tx)

        if final_transactions:
            df = pd.DataFrame(final_transactions)
            # ICICI Headers
            cols = ["DATE", "MODE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]
            
            # Map column names safely even if table width varies
            df.columns = cols[:len(df.columns)]
            
            st.success(f"Success! Found {len(final_transactions)} transactions.")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Clean Excel File",
                data=output.getvalue(),
                file_name="ICICI_Cleaned_Statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No transactions found. Ensure the PDF isn't an image/scan.")

