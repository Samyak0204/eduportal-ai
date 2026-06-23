import zipfile
import xml.etree.ElementTree as ET

def read_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            # Namespace map
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Extract all text elements
            text_runs = []
            for para in root.findall('.//w:p', namespaces):
                para_text = []
                for run in para.findall('.//w:t', namespaces):
                    if run.text:
                        para_text.append(run.text)
                if para_text:
                    text_runs.append("".join(para_text))
            
            return "\n".join(text_runs)
    except Exception as e:
        return f"Error reading docx: {e}"

if __name__ == '__main__':
    text = read_docx('EduPortal_AI_Implementation_Plan.docx')
    with open('scratch/plan_extracted.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Extracted plan text successfully to scratch/plan_extracted.txt")
