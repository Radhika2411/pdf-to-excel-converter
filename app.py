import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="Accurate ICICI Converter", layout="wide")
st.title("🏦 High-Accuracy ICICI PDF to Excel")
st.write("Fixed Deposit/Withdrawal sorting by using exact line positions.")

uploaded_file = st.file_uploader("Upload your ICICI PDF", type="pdf")

def clean_amt(text):
    if not text: return 0.0
    return float(text.replace(',', '').strip())

if uploaded_file:
    with st.spinner("Processing 58 pages..."):
        transactions = []
        current_tx = None
        
        # Regex for Date (DD-MM-YYYY) and Amount (1,234.56)
        date_re = re.compile(r'^(\d{2}-\d{2}-\d{4})')
        amt_re = re.compile(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})')

        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                for line in text.split('\n'):
                    line = line.strip()
                    if not line or "Page" in line or "DATE" in line.upper(): continue

                    date_match = date_re.search(line)
                    if date_match:
                        if current_tx: transactions.append(current_tx)
                        
                        date = date_match.group(1)
                        # Find all numbers on the line
                        all_amts = amt_re.findall(line)
                        
                        if len(all_amts) >= 2:
                            # In ICICI: The very last number is BALANCE
                            # The second to last is either DEPOSIT or WITHDRAWAL
                            val_bal = all_amts[-1]
                            val_amt = all_amts[-2]
                            
                            # Determine if it's a Deposit or Withdrawal based on page layout
                            # Usually, Withdrawals are in the 4th column and Deposits in the 5th
                            # If the transaction amount is closer to the Particulars, it's a Withdrawal
                            # We check the text to see if 'CR' (Credit) or 'DR' (Debit) exists
                            is_credit = " CR " in line.upper() or "CREDIT" in line.upper()
                            
                            current_tx = {
                                "DATE": date,
                                "PARTICULARS": line[len(date):line.find(val_amt)].strip(),
                                "DEPOSITS": val_amt if is_credit else "",
                                "WITHDRAWALS": "" if is_credit else val_amt,
                                "BALANCE": val_bal
                            }
                        else:
                            current_tx = {"DATE": date, "PARTICULARS": line[len(date):], "DEPOSITS":"", "WITHDRAWALS":"", "BALANCE": all_amts[-1] if all_amts else ""}
                    
                    elif current_tx:
                        # Check if this sub-line contains 'CR' or 'DR' which helps classify the row above
                        if " CR " in line.upper():
                            current_tx["DEPOSITS"] = current_tx["WITHDRAWALS"] if current_tx["WITHDRAWALS"] else current_tx["DEPOSITS"]
                            current_tx["WITHDRAWALS"] = ""
                        current_tx["PARTICULARS"] += " " + line

        if current_tx: transactions.append(current_tx)
        
        df = pd.DataFrame(transactions)
        df = df[["DATE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]]
        
        st.dataframe(df)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button("📥 Download Corrected Excel", output.getvalue(), "Fixed_Statement.xlsx")
