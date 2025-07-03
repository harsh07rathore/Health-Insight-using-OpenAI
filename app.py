from flask import Flask, render_template, request
from run_notebook import run_notebook
import os
import json
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
NOTEBOOK_PATH = 'main.ipynb'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/", methods=["GET", "POST"])
def index():
    
    df_html = None
    findings = None
    result_json_str = None
    openai_insights_str = None
    similarity_result_str = None

    if request.method == "POST":
        if 'pdf' not in request.files:
            findings = ["Error: No file uploaded. Please select a PDF file."]
        else:
            pdf = request.files["pdf"]
            if pdf.filename == '':
                findings = ["Error: No file selected. Please choose a PDF file."]
            elif pdf and pdf.filename.endswith(".pdf"):
                pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf.filename)
                pdf.save(pdf_path)

                abs_pdf_path = os.path.abspath(pdf_path)

                with open(NOTEBOOK_PATH, 'r', encoding='utf-8') as f:
                    nb_data = f.read()

                patterns_to_replace = [
                    '"pdf_path = \\"UPLOAD_PDF_PATH_PLACEHOLDER\\""',
                    '"pdf_path = \\"20231021_PreetpalBloodReport_Detailed_0202WJ007460202_228745k.pdf\\""',
                    '"# This will be replaced by the Flask app with the uploaded PDF path\\n",\n    "pdf_path = \\"20231021_PreetpalBloodReport_Detailed_0202WJ007460202_228745k.pdf\\""'
                ]
                
                patched = nb_data
                replacement_made = False
                
                for pattern in patterns_to_replace:
                    if pattern in nb_data:
                        escaped_path = abs_pdf_path.replace('\\', '\\\\').replace('"', '\\"')
                        patched = nb_data.replace(pattern, f'"pdf_path = r\\"{escaped_path}\\""')
                        replacement_made = True
                        print(f"Successfully replaced PDF path using pattern: {pattern[:50]}...")
                        break

                if not replacement_made:
                    import re
                    pdf_path_pattern = r'"pdf_path = \\"[^"]*\\""'
                    if re.search(pdf_path_pattern, nb_data):
                        escaped_path = abs_pdf_path.replace('\\', '\\\\').replace('"', '\\"')
                        patched = re.sub(pdf_path_pattern, f'"pdf_path = r\\"{escaped_path}\\""', nb_data)
                        replacement_made = True
                        print(f"Successfully replaced PDF path using regex pattern")
                    else:
                        print(f"Error: Could not find PDF path assignment in notebook")
                        raise Exception("Could not find PDF path assignment in notebook to replace")
                
                temp_nb = "main_temp.ipynb"
                with open(temp_nb, 'w', encoding='utf-8') as f:
                    f.write(patched)

                try:
                    namespace = run_notebook(temp_nb)
                    if os.path.exists(temp_nb):
                        os.remove(temp_nb)

                    df = namespace.get("df_results")
                    first = namespace.get("first_order_findings")
                    full_json = namespace.get("result_json")
                    openai_insights = namespace.get("OpenAI_insights")
                    similarity_result = namespace.get("similarity_result") 

                    if df is not None:
                        df_html = df.to_html(classes="table", index=False)
                    if isinstance(first, list):
                        findings = first
                    if isinstance(full_json, dict):
                        result_json_str = json.dumps(full_json, indent=2)
                    if openai_insights is not None:  
                        openai_insights_str = json.dumps(openai_insights, indent=2)
                    if similarity_result is not None:
                        similarity_result_str = str(similarity_result)
                        
                except Exception as e:
                    print(f"Error running notebook: {e}")
                    if os.path.exists(temp_nb):
                        os.remove(temp_nb)
                    findings = [f"Error processing PDF: {str(e)}"]
            else:
                findings = ["Error: Please upload a valid PDF file only."]

    return render_template(
        "index.html",
        table=df_html,
        findings=findings,
        result_json=result_json_str,
        openai_insights=openai_insights_str,
        similarity_result=similarity_result_str
        
    )

if __name__ == "__main__":
    app.run(debug=True, port=5004)
