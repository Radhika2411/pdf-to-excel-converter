import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="ICICI Statement Converter", layout="wide")
st.title("🏦 ICICI Bank PDF to Excel Converter")
st.write("Specially optimized for multi-line UPI and NEFT transactions.")

uploaded_file = st.file_uploader("Upload your ICICI PDF Statement", type="pdf")

def is_date(text):
    """Checks if a string matches the DD-MM-YYYY format."""
    if not text: return False
    return bool(re.match(r'\d{2}-\d{2}-\d{4}', str(text)))

if uploaded_file is not None:
    with st.spinner('Processing 58 pages... please wait.'):
        raw_rows = []
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # ICICI statements usually don't have vertical lines. 
                # 'text' strategy helps identify columns by alignment.
                table = page.extract_table({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 3
                })
                
                if table:
                    for row in table:
                        # Clean each cell of extra newlines and whitespace
                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        # Ignore the repetitive header rows
                        if clean_row[0] == "DATE" or not any(clean_row):
                            continue
                        raw_rows.append(clean_row)

        # --- LOGIC TO MERGE MULTI-LINE TRANSACTIONS ---
        final_transactions = []
        current_tx = None

        for row in raw_rows:
            # If the first column is a date, it's a NEW transaction
            if is_date(row[0]):
                if current_tx:
                    final_transactions.append(current_tx)
                current_tx = row
            # If no date, it belongs to the PREVIOUS transaction
            elif current_tx:
                for i in range(len(row)):
                    if row[i]:
                        # Combine text with a space (fixing the broken UPI strings)
                        current_tx[i] = f"{current_tx[i]} {row[i]}".strip()

        if current_tx:
            final_transactions.append(current_tx)

        if final_transactions:
            # Structure into a proper table
            columns = ["DATE", "MODE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]
            # Ensure the data matches the column count (ICICI is usually 5-6 columns)
            df = pd.DataFrame(final_transactions)
            
            st.success(f"Extracted {len(final_transactions)} transactions!")
            st.dataframe(df)

            # Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, header=columns[:len(df.columns)])
            
            st.download_button(
                label="📥 Download Corrected Excel File",
                data=output.getvalue(),
                file_name="ICICI_Cleaned_Statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No transactions found. Please check if the PDF is a scanned image.")
