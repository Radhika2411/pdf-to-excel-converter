import streamlit as st
import pdfplumber
import pandas as pd
import io

st.set_page_config(page_title="Universal Bank Statement Converter", layout="wide")
st.title("🏦 Universal Bank to Excel Converter")
st.write("Extracts Date, Particulars, Deposits, Withdrawals, and Balance from any bank PDF.")

uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type="pdf")

if uploaded_file is not None:
    with st.spinner('Processing transactions...'):
        all_data = []
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # Use 'text' strategy because bank statements often lack vertical lines
                table = page.extract_table({
                    "vertical_strategy": "text", 
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 3,
                })
                
                if table:
                    df = pd.DataFrame(table)
                    # 1. Remove rows that are entirely empty
                    df = df.dropna(how='all')
                    all_data.append(df)

        if all_data:
            # Combine all pages
            final_df = pd.concat(all_data, ignore_index=True)
            
            # 2. Cleanup: Remove rows that repeat the headers (like "DATE", "PARTICULARS")
            # We look for rows where the first column is 'DATE' and remove them
            final_df = final_df[final_df[0].str.upper() != 'DATE']
            
            st.success("Successfully Extracted!")
            st.dataframe(final_df) # Show the full table preview

            # 3. Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False, header=False) # Header=False because PDF rows already include them
            
            st.download_button(
                label="📥 Download Excel File",
                data=output.getvalue(),
                file_name="bank_statement_cleaned.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Could not find a table structure. This PDF might be a scanned image.")

