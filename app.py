import streamlit as st
from parsers.python_parser import extract_functions
from llm_engine.run_local_llm import generate_brd
import ast
import zipfile
import io
from fpdf import FPDF
import datetime

st.set_page_config(page_title="BARE - Business Analyst reverse engineering", layout="wide")
st.title("BARE - Business Analyst reverse engineering")
st.subheader("Reverse Requirements Bot (Code → BRD)")

uploaded_files = st.file_uploader("Upload Python code files or ZIP files", type=[".py", ".zip"], accept_multiple_files=True)

model = st.selectbox("Choose LLM Model", options=["mistral", "starcoder", "wizardcoder", "codellama:13b"])

all_functions = []
file_function_map = {}
all_code_strings = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.zip'):
            # Handle ZIP file
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.endswith('.py'):
                        try:
                            with zip_ref.open(file_info.filename) as file:
                                code_string = file.read().decode("utf-8")
                                all_code_strings.append(code_string)
                                functions = extract_functions(code_string)
                                file_function_map[file_info.filename] = functions
                                for func in functions:
                                    func['file'] = file_info.filename
                                    all_functions.append(func)
                        except Exception as e:
                            st.warning(f"Could not process {file_info.filename} from ZIP: {str(e)}")
        else:
            # Handle individual Python file
            code_string = uploaded_file.read().decode("utf-8")
            all_code_strings.append(code_string)
            functions = extract_functions(code_string)
            file_function_map[uploaded_file.name] = functions
            for func in functions:
                func['file'] = uploaded_file.name
                all_functions.append(func)

    # Show function count instead of all function code
    st.subheader("Extracted Functions Summary")
    st.write(f"Total functions found: {len(all_functions)}")
    
    # Show breakdown by file
    for filename, functions in file_function_map.items():
        st.write(f"📁 {filename}: {len(functions)} functions")

    # Analyze interconnections
    st.subheader("Interlinked Functions Across Files")
    interlinks = []
    # Build a map of function names to file
    func_name_to_file = {func['name']: func['file'] for func in all_functions}
    for func in all_functions:
        # Parse the function source to find function calls
        try:
            tree = ast.parse(func['source'])
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    called_func = node.func.id
                    if called_func in func_name_to_file and func_name_to_file[called_func] != func['file']:
                        interlinks.append((func['name'], func['file'], called_func, func_name_to_file[called_func]))
        except Exception:
            continue
    if interlinks:
        for src_func, src_file, tgt_func, tgt_file in interlinks:
            st.write(f"Function `{src_func}` in `{src_file}` calls `{tgt_func}` in `{tgt_file}`.")
    else:
        st.write("No interlinked functions detected across files.")

    if st.button("Generate Business Requirements"):
        st.subheader("Generated Business Requirements Document")
        
        # Add processing mode selection
        processing_mode = st.radio(
            "Processing Mode",
            ["Individual Functions (Recommended)", "Batch Processing"],
            help="Individual processing is more reliable but slower. Batch processing is faster but may timeout with large functions."
        )
        
        # Process functions individually by default to avoid timeouts
        if processing_mode == "Individual Functions (Recommended)":
            batch_size = 1
        else:
            batch_size = 2  # Reduced from 3 to 2 for batch processing
        
        total_batches = (len(all_functions) + batch_size - 1) // batch_size
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_outputs = []
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(all_functions))
            batch_functions = all_functions[start_idx:end_idx]
            
            # Update progress
            progress = (batch_num + 1) / total_batches
            progress_bar.progress(progress)
            
            if batch_size == 1:
                status_text.text(f"Processing function {batch_num + 1}/{total_batches}: {batch_functions[0]['name']}")
            else:
                status_text.text(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_functions)} functions)")
            
            # Combine function sources for this batch
            batch_code = "\n\n".join([func['source'] for func in batch_functions])
            
            try:
                if batch_size == 1:
                    spinner_text = f"Generating BRD for {batch_functions[0]['name']}..."
                else:
                    spinner_text = f"Generating BRD for batch {batch_num + 1}..."
                
                with st.spinner(spinner_text):
                    output = generate_brd(batch_code, model)
                    
                    # Check if output contains error
                    if output.startswith("Error:"):
                        st.error(f"Failed to process: {output}")
                        if batch_size > 1:
                            st.info("Trying individual function processing as fallback...")
                            # Try processing individual functions in this batch
                            for func in batch_functions:
                                try:
                                    individual_output = generate_brd(func['source'], model)
                                    if not individual_output.startswith("Error:"):
                                        all_outputs.append(individual_output)
                                    else:
                                        st.warning(f"Could not process function {func['name']}: {individual_output}")
                                except Exception as e:
                                    st.warning(f"Could not process function {func['name']}: {str(e)}")
                    else:
                        all_outputs.append(output)
                        
            except Exception as e:
                st.error(f"Error processing: {str(e)}")
                if batch_size > 1:
                    st.info("Trying individual function processing as fallback...")
                    # Try processing individual functions in this batch
                    for func in batch_functions:
                        try:
                            individual_output = generate_brd(func['source'], model)
                            if not individual_output.startswith("Error:"):
                                all_outputs.append(individual_output)
                            else:
                                st.warning(f"Could not process function {func['name']}: {str(e)}")
                        except Exception as e:
                            st.warning(f"Could not process function {func['name']}: {str(e)}")
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Display all outputs
        if all_functions:
            for i, output in enumerate(all_outputs):
                st.write(output)
                if i < len(all_outputs) - 1:
                    st.divider()
        else:
            # No functions found, generate BRD for the complete code
            if st.button("Generate Business Requirements for Complete Code"):
                st.subheader("Generated Business Requirements Document (Full Code)")
                full_code = "\n\n".join(all_code_strings)
                with st.spinner("Generating BRD for the complete code..."):
                    output = generate_brd(full_code, model)
                    st.write(output)
                # PDF download for full code BRD
                st.subheader("Download Business Requirements as PDF")
                if st.button("Generate & Download PDF (Full Code)"):
                    from reportlab.lib.pagesizes import letter
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.units import inch
                    pdf_buffer = io.BytesIO()
                    c = canvas.Canvas(pdf_buffer, pagesize=letter)
                    width, height = letter
                    c.setFont("Helvetica-Bold", 16)
                    c.drawCentredString(width / 2, height - 1 * inch, "Business Requirements Document (Full Code)")
                    c.setFont("Helvetica", 10)
                    c.drawRightString(width - 0.5 * inch, height - 1.25 * inch, f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    y = height - 1.5 * inch
                    c.setFont("Helvetica", 11)
                    for line in output.splitlines():
                        for wrapped_line in [line[i:i+100] for i in range(0, len(line), 100)]:
                            if y < 0.75 * inch:
                                c.showPage()
                                y = height - 1 * inch
                            c.drawString(0.75 * inch, y, wrapped_line)
                            y -= 0.22 * inch
                        y -= 0.1 * inch
                    c.save()
                    pdf_bytes = pdf_buffer.getvalue()
                    pdf_buffer.close()
                    st.download_button(
                        label="Download PDF (Full Code)",
                        data=pdf_bytes,
                        file_name="business_requirements_full_code.pdf",
                        mime="application/pdf"
                    )