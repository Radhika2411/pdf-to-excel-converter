import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="ICICI Statement Structured", layout="wide")
st.title("🏦 Structured ICICI PDF to Excel")
st.write("Extracts exactly 5 columns: Date, Particulars, Deposits, Withdrawals, Balance.")

uploaded_file = st.file_uploader("Upload your ICICI PDF Statement", type="pdf")

def parse_icici(pdf_file):
    # Pattern to find Date (DD-MM-YYYY)
    date_pattern = re.compile(r'^(\d{2}-\d{2}-\d{4})')
    # Pattern to find amounts like 1,234.56 or 1234.56
    amount_pattern = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})')
    
    transactions = []
    current_tx = None
    last_balance = 0.0

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            for line in text.split('\n'):
                line = line.strip()
                # Skip headers, footers, and junk
                if not line or "Page" in line or "DATE" in line.upper():
                    continue

                date_match = date_pattern.search(line)
                if date_match:
                    # Save completed transaction
                    if current_tx:
                        transactions.append(current_tx)
                    
                    date = date_match.group(1)
                    rest = line[len(date):].strip()
                    
                    # Find all numbers at the end of the line
                    found_amounts = amount_pattern.findall(rest)
                    
                    # Clean the Particulars text by removing the amounts found
                    particulars = rest
                    for amt in found_amounts:
                        particulars = particulars.replace(amt, "").strip()

                    # Logic to sort Amounts into Deposit/Withdrawal/Balance
                    dep, wdl, bal_str = "", "", "0.00"
                    
                    if len(found_amounts) >= 2:
                        # Usually: [Amount] [Balance]
                        curr_amt = float(found_amounts[-2].replace(',', ''))
                        curr_bal = float(found_amounts[-1].replace(',', ''))
                        
                        if curr_bal >= last_balance:
                            dep = found_amounts[-2]
                        else:
                            wdl = found_amounts[-2]
                        
                        bal_str = found_amounts[-1]
                        last_balance = curr_bal
                    elif len(found_amounts) == 1:
                        # Case like B/F (Balance Forward)
                        bal_str = found_amounts[0]
                        last_balance = float(bal_str.replace(',', ''))

                    current_tx = {
                        "DATE": date,
                        "PARTICULARS": particulars,
                        "DEPOSITS": dep,
                        "WITHDRAWALS": wdl,
                        "BALANCE": bal_str
                    }
                
                elif current_tx:
                    # If line has no date, it's a continuation of the previous Particulars
                    # Only append if it's not a stray page number
                    if not amount_pattern.search(line):
                        current_tx["PARTICULARS"] += " " + line

        if current_tx:
            transactions.append(current_tx)
            
    return transactions

if uploaded_file:
    with st.spinner("Processing 58 pages..."):
        data = parse_icici(uploaded_file)
        if data:
            df = pd.DataFrame(data)
            # Ensure columns are in the exact order you requested
            df = df[["DATE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]]
            
            st.success(f"Extracted {len(df)} transactions!")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Structured Excel File",
                data=output.getvalue(),
                file_name="ICICI_Structured_Statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
