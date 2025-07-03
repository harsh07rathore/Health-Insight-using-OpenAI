import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import asyncio
import nest_asyncio
import threading

nest_asyncio.apply()

def run_notebook(notebook_path):
    with open(notebook_path, encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    def execute_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
            ep.preprocess(nb, {'metadata': {'path': '.'}})
        except Exception as e:
            print(f"Error during notebook execution: {e}")
            raise
        finally:
            loop.close()

    thread = threading.Thread(target=execute_in_thread)
    thread.start()
    thread.join()

    namespace = {}
    for cell in nb.cells:
        if cell.cell_type == 'code':
            try:
                exec(cell.source, namespace)
            except Exception as e:
                print(f"Error executing cell: {e}")
                continue
    similarity_result = namespace.get("similarity_result", None)
    namespace["similarity_result"] = similarity_result

    return namespace
