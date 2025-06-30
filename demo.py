import streamlit as st
from parsers.python_parser import extract_functions
from llm_engine.run_local_llm import generate_brd, generate_process_flow
import ast
import zipfile
import io
from fpdf import FPDF
import datetime

st.set_page_config(page_title="BARE - Business Analyst Reverse Engineering", layout="wide")
st.title("BARE - Business Analyst Reverse Engineering")
st.markdown("AI-powered Reverse Requirements Bot to extract Business Requirements from Legacy Code")
st.markdown("---")

st.sidebar.header("Configuration")
model = st.sidebar.selectbox("Choose LLM Model", options=["mistral", "starcoder", "wizardcoder", "codellama:13b"])
processing_mode = st.sidebar.radio("Processing Mode", ["Individual Functions (Recommended)", "Batch Processing"])
export_pdf = st.sidebar.checkbox("Export PDF after BRD generation", value=True)

st.header("1️⃣ Upload Python Code Files or ZIP Archives")
uploaded_files = st.file_uploader("Select files to analyze", type=[".py", ".zip"], accept_multiple_files=True)

all_functions = []
file_function_map = {}
all_code_strings = []

if uploaded_files:
    with st.expander("📄 Uploaded Files Summary", expanded=True):
        for uploaded_file in uploaded_files:
            st.write(f"- {uploaded_file.name}")

    for uploaded_file in uploaded_files:
        if uploaded_file.name.endswith('.zip'):
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
            try:
                code_string = uploaded_file.read().decode("utf-8")
                all_code_strings.append(code_string)
                functions = extract_functions(code_string)
                file_function_map[uploaded_file.name] = functions
                for func in functions:
                    func['file'] = uploaded_file.name
                    all_functions.append(func)
            except Exception as e:
                st.error(f"Could not process {uploaded_file.name}: {str(e)}")

    st.header("2️⃣ Extraction Summary")
    st.success(f"✅ Total Functions Detected: {len(all_functions)}")
    
    if file_function_map:
        for filename, functions in file_function_map.items():
            st.write(f"📁 {filename}: {len(functions)} functions")
            if functions:
                with st.expander(f"Functions in {filename}"):
                    for func in functions:
                        st.code(f"Function: {func['name']}", language="text")
    else:
        st.warning("No functions were extracted from the uploaded files.")

    st.header("3️⃣ Interlinked Functions Analysis")
    interlinks = []
    func_name_to_file = {func['name']: func['file'] for func in all_functions}
    
    for func in all_functions:
        try:
            tree = ast.parse(func['source'])
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    called_func = node.func.id
                    if called_func in func_name_to_file and func_name_to_file[called_func] != func['file']:
                        interlinks.append((func['name'], func['file'], called_func, func_name_to_file[called_func]))
        except Exception as e:
            st.warning(f"Could not analyze function {func['name']}: {str(e)}")
            continue
    
    if interlinks:
        st.info(f"Found {len(interlinks)} interlinked function calls:")
        for src_func, src_file, tgt_func, tgt_file in interlinks:
            st.write(f"🔗 `{src_func}` in `{src_file}` calls `{tgt_func}` in `{tgt_file}`")
    else:
        st.info("No interlinked functions detected across files.")

    st.header("4️⃣ Generate Business Requirements Document (BRD)")

    if st.button("🚀 Start BRD Generation", key="btn_brd_start"):
        if not all_code_strings:
            st.error("No code was extracted from uploaded files. Please check your files and try again.")
            st.stop()
        
        all_outputs = []
        
        # Generate FULL PROJECT BRD FIRST
        st.subheader("🔄 Generating Full Project Business Requirements...")
        full_code = "\n\n# === FILE SEPARATOR ===\n\n".join(all_code_strings)
        
        if len(full_code.strip()) == 0:
            st.error("No code content found to analyze.")
            st.stop()
        
        try:
            with st.spinner("Generating full project BRD..."):
                st.write(f"Debug: Code length = {len(full_code)} characters")
                full_output = generate_brd(full_code, model)
                
                if full_output and not full_output.startswith("Error:"):
                    all_outputs.append(("Full Project Analysis", full_output))
                    st.success("✅ Full project BRD generated successfully!")
                else:
                    st.error(f"Failed to generate full project BRD: {full_output}")
                    
        except Exception as e:
            st.error(f"Error generating full project BRD: {str(e)}")

        # Generate per-function BRDs if requested and functions exist
        if all_functions and processing_mode == "Individual Functions (Recommended)":
            st.subheader("🔄 Generating Individual Function BRDs...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, func in enumerate(all_functions):
                progress = (i + 1) / len(all_functions)
                progress_bar.progress(progress)
                status_text.text(f"Processing function {i + 1}/{len(all_functions)}: {func['name']}")
                
                try:
                    with st.spinner(f"Generating BRD for function: {func['name']}"):
                        func_code = f"# Function from file: {func['file']}\n\n{func['source']}"
                        output = generate_brd(func_code, model)
                        
                        if output and not output.startswith("Error:"):
                            all_outputs.append((f"Function: {func['name']} ({func['file']})", output))
                        else:
                            st.warning(f"Could not generate BRD for function {func['name']}: {output}")
                            
                except Exception as e:
                    st.warning(f"Error processing function {func['name']}: {str(e)}")
            
            progress_bar.empty()
            status_text.empty()

        # Display results
        if all_outputs:
            st.success(f"✅ Generated {len(all_outputs)} Business Requirements!")
            
            # Create tabs for each output
            if len(all_outputs) > 1:
                tabs = st.tabs([output[0] for output in all_outputs])
                for i, (title, content) in enumerate(all_outputs):
                    with tabs[i]:
                        st.markdown(content)
            else:
                st.markdown("### " + all_outputs[0][0])
                st.markdown(all_outputs[0][1])
                
        else:
            st.error("No business requirements could be generated. Please check your LLM connection and try again.")

        # PDF Export
        if export_pdf and all_outputs:
            st.header("5️⃣ Download BRD as PDF")
            
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "Business Requirements Document", 0, 1, "C")
                pdf.ln(10)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 10, f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R")
                pdf.ln(10)
                
                for i, (title, content) in enumerate(all_outputs):
                    if i > 0:
                        pdf.add_page()
                    
                    pdf.set_font("Arial", "B", 14)
                    # Handle title encoding
                    safe_title = title.encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(0, 10, safe_title, 0, 1, "L")
                    pdf.ln(5)
                    
                    pdf.set_font("Arial", "", 10)
                    # Handle content encoding and split into chunks
                    safe_content = content.encode('latin-1', 'replace').decode('latin-1')
                    
                    # Split content into smaller chunks to avoid PDF issues
                    lines = safe_content.split('\n')
                    for line in lines:
                        if len(line) > 180:  # Split very long lines
                            words = line.split(' ')
                            current_line = ""
                            for word in words:
                                if len(current_line + word) < 180:
                                    current_line += word + " "
                                else:
                                    if current_line:
                                        pdf.cell(0, 6, current_line.strip(), 0, 1, "L")
                                    current_line = word + " "
                            if current_line:
                                pdf.cell(0, 6, current_line.strip(), 0, 1, "L")
                        else:
                            pdf.cell(0, 6, line, 0, 1, "L")
                    
                    pdf.ln(5)
                
                pdf_bytes = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="📥 Download PDF", 
                    data=pdf_bytes, 
                    file_name=f"business_requirements_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 
                    mime="application/pdf"
                )
                
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")

    st.header("6️⃣ Generate Business Process Flow Diagram")
    if st.button("📊 Generate Process Flow Diagram", key="btn_process_flow"):
        if not all_code_strings:
            st.error("No code available for process flow analysis.")
            st.stop()
        
        full_code = "\n\n# === FILE SEPARATOR ===\n\n".join(all_code_strings)
        
        try:
            with st.spinner("Extracting business process flow from code..."):
                process_flow = generate_process_flow(full_code, model)
                
                if process_flow and not process_flow.startswith("Error:"):
                    st.success("✅ Process Flow Extracted!")
                    st.markdown("### Process Steps:")
                    st.markdown(process_flow)
                    
                    # Generate Mermaid diagram
                    st.markdown("### Visual Flowchart:")
                    try:
                        mermaid_code = "graph TD\n"
                        step_counter = 0
                        
                        lines = process_flow.splitlines()
                        valid_steps = []
                        
                        for line in lines:
                            if line.strip() and ("step" in line.lower() or line.startswith(str(step_counter + 1))):
                                # Extract step description
                                if ":" in line:
                                    step_desc = line.split(":", 1)[1].strip()
                                else:
                                    step_desc = line.strip()
                                
                                # Clean step description
                                step_desc = step_desc.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
                                if len(step_desc) > 50:
                                    step_desc = step_desc[:47] + "..."
                                
                                valid_steps.append(step_desc)
                                step_counter += 1
                        
                        # Build mermaid diagram
                        for i, step in enumerate(valid_steps):
                            safe_step = step.replace('"', "'").replace('\n', ' ')
                            mermaid_code += f'    Step{i}["{safe_step}"]\n'
                            
                            if i > 0:
                                mermaid_code += f"    Step{i-1} --> Step{i}\n"
                        
                        st.code(mermaid_code, language="mermaid")
                        
                    except Exception as e:
                        st.warning(f"Could not generate flowchart diagram: {str(e)}")
                        
                else:
                    st.error(f"Failed to generate process flow: {process_flow}")
                    
        except Exception as e:
            st.error(f"Error generating process flow: {str(e)}")

else:
    st.info("👆 Please upload Python files or ZIP archives to begin analysis.")
    st.markdown("""
    ### How to use BARE:
    1. **Upload Files**: Choose Python (.py) files or ZIP archives containing Python code
    2. **Configure**: Select your preferred LLM model and processing mode
    3. **Generate BRD**: Click to generate comprehensive Business Requirements Documents
    4. **Process Flow**: Generate visual business process flow diagrams
    5. **Export**: Download results as PDF for stakeholders
    
    ### Supported Models:
    - Mistral
    - StarCoder
    - WizardCoder
    - CodeLlama 13B
    """)