# cleaning the data before putting it into TagAnt

import os
import subprocess
import re
from docx import Document

def convert_doc_docx(input_folder, output_folder):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Loop through all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith(".doc"):
            doc_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename.replace(".doc", ".docx"))

            # Use LibreOffice to convert .doc to .docx
            subprocess.run(['libreoffice', '--headless', '--convert-to', 'docx', doc_path, '--outdir', output_folder])

def clean_data(input_folder, output_folder):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Step 1: Convert DOCX files to TXT and process them
    for filename in os.listdir(input_folder):
        if filename.endswith(".docx"):
            docx_path = os.path.join(input_folder, filename)
            txt_file = os.path.splitext(filename)[0] + ".txt"
            txt_path = os.path.join(output_folder, txt_file)

            # Convert DOCX to TXT
            doc = Document(docx_path)
            # Extract text from paragraphs
            text_content = [paragraph.text for paragraph in doc.paragraphs]
            # Combine paragraphs into a single string with formatted punctuation
            full_text = "\n".join(text_content).replace('/', ',').replace(',,', ',')
            # Write the text to a TXT file
            with open(txt_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(full_text)

            # Step 2: Clean the content of the newly created TXT file
            with open(txt_path, 'r', encoding='utf-8') as infile:
                content = infile.read()

            # Remove text based on conditions
            content = re.sub(
                r'\(.*?\)\s*'     # parentheses + space
                r'|[•·]',       # stray punctuation
                '',
                content,
                flags=re.DOTALL
            )

            BXlist = ["21"]

            if any(filename.startswith(num) for num in BXlist):
                # Extract all sequences that start with A: and end with X:
                filtered_sequences = (re.findall(r"B:\s*(.*?)\s*[A-Z]:", content, flags=re.DOTALL))
            else:
                # Extract all sequences that start with B: and end with X:
                filtered_sequences = (re.findall(r"A:\s*(.*?)\s*[A-Z]:", content, flags=re.DOTALL))

            # Join into one string (not line-based anymore, unless you want separators)
            modified_content = "\n".join(filtered_sequences)
            modified_content = modified_content.replace(":", "")
            modified_content = re.sub(r"\bA\s+", '', modified_content)

            # Write the cleaned content back to the output file
            with open(txt_path, 'w', encoding='utf-8') as outfile:
                outfile.write(modified_content)

    print("Successfully cleaned data")

clean_data("datos/original", "datos/text")


def remove_text(input_folder, num_words_to_remove):
    import os
    
    # Ensure the input folder exists
    os.makedirs(input_folder, exist_ok=True)
    
    for filename in os.listdir(input_folder):
        if filename.endswith(".txt"):
            txt_path = os.path.join(input_folder, filename)

            with open(txt_path, 'r', encoding='utf-8') as infile:
                content = infile.read()

            word_count = 0
            result_lines = []
            
            for line in content.splitlines(keepends=True):  # keep \n at end
                words = line.split()
                
                if word_count < num_words_to_remove:
                    # skip words until we’ve removed enough
                    remaining = []
                    for w in words:
                        if word_count < num_words_to_remove:
                            word_count += 1
                            continue
                        remaining.append(w)
                    if remaining:
                        result_lines.append(" ".join(remaining) + ("\n" if line.endswith("\n") else ""))
                else:
                    result_lines.append(line)
            
            final_content = "".join(result_lines)

            with open(txt_path, 'w', encoding='utf-8') as outfile:
                outfile.write(final_content)

    print(f"Successfully deleted {num_words_to_remove} words from each file")

remove_text("datos/text", 350)