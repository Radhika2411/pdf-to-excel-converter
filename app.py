import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="ICICI Statement Converter", layout="wide")
st.title("🏦 ICICI Bank PDF to Excel Converter")
st.write("Fixed 'Length Mismatch' error. Optimized for 58+ page statements.")

uploaded_file = st.file_uploader("Upload your ICICI PDF Statement", type="pdf")

def is_date(text):
    """Checks if a cell matches the DD-MM-YYYY format."""
    if not text or not isinstance(text, str): return False
    return bool(re.match(r'\d{2}-\d{2}-\d{4}', text.strip()))

if uploaded_file is not None:
    with st.spinner('Reading PDF... this may take a minute for large files.'):
        raw_rows = []
        # Standard ICICI Columns
        TARGET_COLS = ["DATE", "MODE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                table = page.extract_table({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 3
                })
                
                if table:
                    for row in table:
                        # Clean and normalize row length to exactly 6
                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                        
                        # Pad row with empty strings if it's too short
                        while len(clean_row) < 6:
                            clean_row.append("")
                        # Truncate if it's too long (rare ghost columns)
                        clean_row = clean_row[:6]

                        # Skip headers and completely empty rows
                        if not any(clean_row) or "DATE" in clean_row[0].upper():
                            continue
                        raw_rows.append(clean_row)

        # --- SMART MERGE LOGIC ---
        final_transactions = []
        current_tx = None

        for row in raw_rows:
            if is_date(row[0]):
                if current_tx:
                    final_transactions.append(current_tx)
                current_tx = list(row)
            elif current_tx:
                # Merge continuation lines into the Particulars column (index 2)
                # We combine all cells from the messy line into the 'Particulars' box
                extra_text = " ".join([item for item in row if item]).strip()
                if extra_text:
                    current_tx[2] = f"{current_tx[2]} {extra_text}".strip()

        if current_tx:
            final_transactions.append(current_tx)

        if final_transactions:
            # Create DataFrame with guaranteed 6-column structure
            df = pd.DataFrame(final_transactions, columns=TARGET_COLS)
            
            st.success(f"Success! Processed {len(final_transactions)} transactions.")
            st.dataframe(df)

            # Generate Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Clean Excel File",
                data=output.getvalue(),
                file_name="ICICI_Final_Statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No transactions detected. Is this a digital PDF (not a scan)?")
