import streamlit as st
import pdfplumber
import pandas as pd
import io

st.set_page_config(page_title="PDF to Excel Converter", layout="wide")

st.title("📄 Free PDF to Excel Transaction Converter")
st.write("Upload your bank statement or invoice to extract tables into Excel.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    with st.spinner('Extracting data...'):
        all_tables = []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # Extracting table data from each page
                table = page.extract_table()
                if table:
                    # Creating a DataFrame; assuming first row is header
                    df = pd.DataFrame(table[1:], columns=table[0])
                    all_tables.append(df)
        
        if all_tables:
            final_df = pd.concat(all_tables, ignore_index=True)
            
            st.success("Extraction Complete!")
            st.subheader("Data Preview")
            st.dataframe(final_df.head(10)) # Show first 10 rows
            
            # Prepare Excel for download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Excel File",
                data=output.getvalue(),
                file_name="extracted_transactions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No tables found in this PDF. Try a different document.")
