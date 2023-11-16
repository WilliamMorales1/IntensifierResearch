# below is all the code i used to get the data
# all of it was ran in colab.research.google.com

# run the below commands to download spacy
# !pip install -U pip setuptools wheel
# !pip install -U spacy
# !python -m spacy download es_dep_news_trf

# converting from docx -> txt
# !pip install python-docx
from docx import Document
import os

def convert_docx_to_txt(docx_path, txt_path):
    # Open the DOCX file
    doc = Document(docx_path)

    # Extract text from paragraphs
    text_content = [paragraph.text for paragraph in doc.paragraphs]

    # Combine paragraphs into a single string
    full_text = "\n".join(text_content)

    # Write the text to a TXT file
    with open(txt_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(full_text)

def batch_convert_docx_to_txt(input_folder, output_folder):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Get a list of all DOCX files in the input folder
    docx_files = [file for file in os.listdir(input_folder) if file.endswith(".docx")]

    # Convert each DOCX file to TXT
    for docx_file in docx_files:
        # Generate corresponding output file name
        txt_file = os.path.splitext(docx_file)[0] + ".txt"

        # Full paths for input and output files
        docx_path = os.path.join(input_folder, docx_file)
        txt_path = os.path.join(output_folder, txt_file)

        # Convert DOCX to TXT
        convert_docx_to_txt(docx_path, txt_path)

if __name__ == "__main__":
    input_folder_path = "/content/IntesifierInput"  # Replace with the path to your input folder containing DOCX files
    output_folder_path = "/content/IntensifierOutput"  # Replace with the desired output folder for TXT files

    batch_convert_docx_to_txt(input_folder_path, output_folder_path)



# marking all of the things, I used spacy to code for adjectives
import spacy
import os

# Example usage
input_folder = "/content/IntTxt"  # Replace with the path to your input folder
output_folder = "/content/IntMarkedFullFinal"  # Replace with the path to your output folder

def mark_spanish_intensifiers(input_folder, output_folder):
    # Load the Spanish language model
    nlp = spacy.load("es_dep_news_trf")

    # Get the current working directory in Colab
    colab_dir = "/content"

    # Construct the absolute path to the input folder
    input_folder_path = os.path.join(colab_dir, input_folder)

    # Construct the absolute path to the output folder
    output_folder_path = os.path.join(colab_dir, output_folder)

    # Iterate over files in the input folder
    for filename in os.listdir(input_folder_path):
        if filename.endswith(".txt"):
            # Construct the absolute path to the input file
            input_file_path = os.path.join(input_folder_path, filename)

            # Construct the absolute path to the output file
            output_file_path = os.path.join(output_folder_path, f"Marked_{filename}")

            # Read the input text from the file
            with open(input_file_path, "r", encoding="utf-8") as file:
                text = file.read()

            # Process the text with spaCy
            doc = nlp(text)

            # Mark Spanish intensifiers and adjectives in the text, ignores everything in brackets
            marked_text = ""
            # List of spanish intensifiers used, can be updated and/or changed
            intensifiers = {"muy", "tan", "bastante", "más", "super", "plenamente", "bien", "mucho", "mucha", 
                            "muchos", "muchas", "verdaderamente", "demasiado", "extremadamente", "sumamente"}
            in_brackets = False
            for i, token in enumerate(doc):
                if token.text == "<":
                    in_brackets = True
                elif token.text == ">":
                    in_brackets = False
                elif not in_brackets:
                    if token.text.lower() in intensifiers and i < len(doc) - 1 and doc[i + 1].pos_ == "ADJ":
                        marked_text += f"[{token.text.upper()}] "
                    elif token.text.lower() in intensifiers and i < len(doc) - 1 and doc[i + 1].text.lower() in intensifiers:
                        marked_text += f"[{token.text.upper()}] "
                    elif token.pos_ == "ADJ" and i > 0 and not (doc[i - 1].text.lower() in intensifiers):
                        marked_text += f"[∅] {token.text.upper()} "
                    elif token.pos_ == "ADJ":
                        marked_text += token.text.upper() + " "
                    else:
                        marked_text += token.text + " "

            # Write the marked text to the output file
            with open(output_file_path, "w", encoding="utf-8") as file:
                file.write(marked_text)

# Call the function with the input and output folder paths
mark_spanish_intensifiers(input_folder, output_folder)
