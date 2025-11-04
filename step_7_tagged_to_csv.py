# run before everything else
import os
import pandas as pd
import re

# main data csv maker
def create_data(input_path, output_filename):
    def remove_SPACE():
        # Check if the directory exists
        if os.path.isdir(input_path):
            # List all files in the directory
            files = os.listdir(input_path)

            # Loop through each file
            for file_name in files:
                if file_name.endswith('.txt'):
                    file_path = os.path.join(input_path, file_name)

                    # Read the content of the file with the detected encoding
                    with open(file_path, 'r', encoding="utf-8") as file:
                        content = file.read()

                    # Replace _SPACE_ with an empty string
                    modified_content = content.replace('_SPACE_', '')

                    # Write the modified content back to the file
                    with open(file_path, 'w', encoding="utf-8") as file:
                        file.write(modified_content)

    def analyze(input_folder_path):

        # no mas, tan
        intensifier_list = ["absolutamente", "bastante", "casi", "completamente", "demasiado", "estrictamente",
                "especialmente", "extremadamente", "harto", "increíblemente", "mucho",
                "muy", "plenamente", "realmente", "sumamente", "súper", "totalmente", "verdaderamente",
                "bien", "super", "supel", "re"]

        apocope_dict = {'gran': 'grande',
                        'buen': 'bueno',
                        'cien': 'ciento',
                        'cualquier': 'cualquiero',
                        'cualesquier': 'cualesquiero',
                        'algún': 'alguno',
                        'mal': 'malo',
                        'ningún': 'ninguno',
                        'primer': 'primero',
                        'tercer': 'tercero',
                        'un': 'uno'}

        forms_of_estar = ["estar", "estal",
                          "estoy", "estás", "está", "estamos", "estáis", "están",
                          "estaba", "estabas", "estábamos", "estabais", "estaban",
                          "estuve", "estuviste", "estuvo", "estuvimos", "estuvisteis", "estuvieron",
                          "estaré", "estarás", "estará", "estaremos", "estaréis", "estarán",
                          "estaría", "estarías", "estaría", "estaríamos", "estaríais", "estarían",
                          "esté", "estés", "estemos", "estéis", "estén",
                          "estuviera", "estuvieras", "estuviéramos", "estuvierais", "estuvieran",
                          "estuviese", "estuvieses", "estuviésemos", "estuvieseis", "estuviesen",
                          "estuviere", "estuvieres", "estuviéremos", "estuviereis", "estuvieren",
                          "estad"]

        forms_of_ser = ["ser", "sel",
                        "soy", "eres", "es", "somos", "sois", "son",
                        "era", "eras", "éramos", "erais", "eran",
                        "fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron",
                        "seré", "serás", "será", "seremos", "seréis", "serán",
                        "sería", "serías", "sería", "seríamos", "seríais", "serían",
                        "sea", "seas", "seás", "seamos", "seáis", "sean",
                        "fuera", "fueras", "fuéramos", "fuerais", "fueran",
                        "fuese", "fueses", "fuésemos", "fueseis", "fuesen",
                        "fuere", "fueres", "fuéremos", "fuereis", "fueren",
                        "sé", "sed"]

        forms_of_parecer = ["parecer", "parecel",
                            "parezco", "pareces", "parecés", "parece", "parecemos", "parecéis", "parecen",
                            "parecía", "parecías", "parecíamos", "parecíais", "parecían",
                            "parecí", "pareciste", "pareció", "parecimos", "parecisteis", "parecieron",
                            "pareceré", "parecerás", "parecerá", "pareceremos", "pareceréis", "parecerán",
                            "parecería", "parecerías", "parecería", "pareceríamos", "pareceríais", "parecerían",
                            "parezca", "parezcas", "parezcás", "parezcamos", "parezcáis", "parezcan",
                            "pareciera", "parecieras", "pareciéramos", "parecierais", "parecieran",
                            "pareciese", "parecieses", "pareciésemos", "parecieseis", "pareciesen",
                            "pareciere", "parecieres", "pareciéremos", "pareciereis", "parecieren",
                            "paracé", "pareced"]

        copulas = forms_of_estar + forms_of_ser + forms_of_parecer

        # Create a list to store data frames
        data_frames = []

        # Iterate over marked files in the input folder
        for filename in os.listdir(input_folder_path):
            # SPEAKER
            pattern = re.compile(r'\.txt')
            match = re.search(r'\d{2}', filename)
            first_two_digits = match.group(0)
            speaker = pattern.sub('', "CART" + first_two_digits)
            print("Started analyzing:", speaker)

            # Construct the absolute path to the marked file
            marked_file_path = os.path.join(input_folder_path, filename)

            # Initialize a list to store row data
            rows = []

            # Read the marked text from the file
            with open(marked_file_path, "r", encoding="utf-8") as file:
                # Process marked text line by line
                for line in file:
                    # Split the line into segments based on custom sentence-ending punctuation
                    segments = re.split(r'(?<=[,.!?]_PUNCT_[,.!?])', line)

                    # Initialize variables inside the inner loop
                    intensifier = None
                    adjective = None
                    lex_adjective = None
                    attributive = None
                    noun = None
                    double_intensified = None

                    # Process each segment
                    for segment in segments:
                        # Split the segment into words
                        words = segment.split()

                        # Process each word in the segment
                        for i, word in enumerate(words):
                            if "_ADJ_" in word and any(word.endswith(c) for c in 'oaeslndr') and not(word.endswith('mente')) and re.match(r'^[a-zA-Z_áéíóúüñÁÉÍÓÚÜÑ]+$', word):
                                # ADJECTIVO
                                adjective = re.search(r'^(.*)_ADJ_', word).group(1)
                                lex_adjective = re.search(r'_ADJ_(.+)', word).group(1)
                                # apocope corrections
                                if lex_adjective in apocope_dict:
                                    lex_adjective = apocope_dict[lex_adjective]
                                if lex_adjective.endswith("s"):
                                    lex_adjective = lex_adjective[:-1]
                                if lex_adjective.endswith("a"):
                                    lex_adjective = lex_adjective[:-1] + "o"
                                ####print(adjective)
                                ####print(lex_adjective)
                                # ATRIBUTIVO, NOMINAL
                                # noun adj
                                if i > 0 and "_NOUN_" in words[i-1] and not any(inter in words[i-1] for inter in intensifier_list):
                                    attributive = "attributive"
                                    noun = re.search(r'^(.*?)_', words[i-1]).group(1)
                                # adj noun
                                elif i < len(words) - 1 and "_NOUN_" in words[i+1]:
                                    attributive = "attributive"
                                    noun = re.search(r'^(.*?)_', words[i+1]).group(1)
                                # noun int adj
                                elif i > 1 and "_NOUN_" in words[i-2] and any(inter in words[i-1] for inter in intensifier_list):
                                    attributive = "attributive"
                                    noun = re.search(r'^(.*?)_', words[i-2]).group(1)
                                # cop int adj
                                elif i > 1 and any(form in words[i-2] for form in copulas):
                                    attributive = "predicative"
                                    noun = "/"
                                # cop adj
                                elif i > 0 and any(form in words[i-1] for form in copulas):
                                    attributive = "predicative"
                                    noun = "/"
                                else:
                                    attributive = "ambiguous"
                                    noun = "/"
                                if not re.match(r'^[a-zA-Z_áéíóúüñÁÉÍÓÚÜÑ/]+$', noun):
                                    attributive = "ambiguous"
                                    noun = "/"
                                ####print(noun)
                                # INTENSIFICADOR
                                if i > 0:
                                    prev_word_match = re.search(r'^(.*?)_', words[i-1])
                                    if prev_word_match:
                                        prev_word = prev_word_match.group(1)
                                        if prev_word in intensifier_list:
                                            intensifier = prev_word
                                        else:
                                            intensifier = '/'
                                    else:
                                        intensifier = '/'
                                else:
                                    intensifier = '/'
                                if adjective.endswith("ísimo") or adjective.endswith("ísima"):
                                    intensifier = '-ísimo'
                                if adjective.startswith("archi"):
                                    intensifier = 'archi-'
                                if intensifier == 'super' or intensifier == 'supel':
                                    intensifier = 'súper'
                                if adjective.startswith("re"):
                                    print(adjective)
                                ####print(intensifier)
                                # DOBLE_INT
                                if intensifier != '/' and i > 1:
                                    prev_prev_word_match = re.search(r'^(.*?)_', words[i-2])
                                    if prev_prev_word_match:
                                        prev_prev_word = prev_prev_word_match.group(1)
                                        if prev_prev_word in intensifier_list:
                                            double_intensified = prev_prev_word
                                        else:
                                            double_intensified = '/'
                                    else:
                                        double_intensified = '/'
                                else:
                                    double_intensified = '/'
                                # FRASE_COMPLETA
                                phrase_tagged = ' '.join(words)
                                # FRASE REAL
                                phrase = ' '.join(re.sub(r'_.*', '', word) for word in words)

                                row_data = {
                                    'Speaker': speaker,
                                    'Phr_tagged': phrase_tagged,
                                    'Phr': phrase,
                                    'Int': intensifier,
                                    'Double': double_intensified,
                                    'Adj': adjective,
                                    'Lex_Adj': lex_adjective,
                                    'Adj_type': attributive,
                                    'Noun': noun,
                                }
                                rows.append(row_data)

                    # Check if rows list is not empty
            if rows:
                # Create a DataFrame for the current file and append it to the list
                df = pd.DataFrame(rows)
                data_frames.append(df)
                print(f"Appended DataFrame for file: {filename}")
            else:
                print(f"No valid rows found in file: {filename}")

        # Concatenate all data frames in the list
        if data_frames:
            data = pd.concat(data_frames, ignore_index=True)
            # Save the DataFrame to a CSV file
            data.to_csv(input_path + "\\temp.csv", index=False)
            print("Successfully concatenated data frames")
        else:
            print("No data frames to concatenate")

            # Create a DataFrame for the current file and append it to the list
            data_frames.append(pd.DataFrame(rows))

        # Concatenate all data frames in the list
        data = pd.concat(data_frames, ignore_index=True)

        # Save the DataFrame to a CSV file
        data.to_csv(output_filename, index=False)

    def closest_verb_non_infinitive(row):
        phrase = row['Phr_tagged']
        intensifier_pos = phrase.find(row['Adj'])

        # Initialize minimum distances and closest matches
        min_distance_verb = float('inf')
        min_distance_aux = float('inf')
        closest_verb = None  # To store the closest verb
        closest_aux = None   # To store the closest auxiliary

        # Regular expression to find verb and auxiliary patterns
        pattern = r'\b(\w+)_(VERB|AUX)_(\w+)\b'  # Capture the first word

        # Use re.finditer to find all matches of the pattern
        for match in re.finditer(pattern, phrase):
            # Find the start and end of the match
            start_pos = match.start()
            end_pos = match.end()

            # Calculate distance as the distance to the center of the match
            match_center = (start_pos + end_pos) // 2
            distance = abs(match_center - intensifier_pos)

            # Check if the match is VERB or AUX and update accordingly
            if 'VERB' in match.group():
                if distance < min_distance_verb:
                    min_distance_verb = distance
                    closest_verb = match.group(1)  # Store the first word
            elif 'AUX' in match.group():
                if distance < min_distance_aux:
                    min_distance_aux = distance
                    closest_aux = match.group(1)  # Store the first word

        # Determine which is closer to the intensifier
        if closest_verb and closest_aux:
            if min_distance_verb < min_distance_aux:
                return closest_verb
            else:
                return closest_aux
        elif closest_verb:
            return closest_verb
        elif closest_aux:
            return closest_aux
        else:
            return '/'  # Return '/' if no relevant forms are found

    def closest_verb_infinitive(row):
        phrase = row['Phr_tagged']
        intensifier_pos = phrase.find(row['Adj'])

        # Initialize minimum distances and closest matches
        min_distance_verb = float('inf')
        min_distance_aux = float('inf')
        closest_verb = None  # To store the closest verb
        closest_aux = None   # To store the closest auxiliary

        # Regular expression to find verb and auxiliary patterns
        pattern = r'\b(\w+)_(VERB|AUX)_(\w+)\b'  # Capture both words

        # Use re.finditer to find all matches of the pattern
        for match in re.finditer(pattern, phrase):
            # Find the start and end of the match
            start_pos = match.start()
            end_pos = match.end()

            # Calculate distance as the distance to the center of the match
            match_center = (start_pos + end_pos) // 2
            distance = abs(match_center - intensifier_pos)

            # Check if the match is VERB or AUX and update accordingly
            if 'VERB' in match.group():
                if distance < min_distance_verb:
                    min_distance_verb = distance
                    closest_verb = match.group(3)  # Store the second word (infinitive)
            elif 'AUX' in match.group():
                if distance < min_distance_aux:
                    min_distance_aux = distance
                    closest_aux = match.group(3)  # Store the second word (infinitive)

        # Determine which is closer to the intensifier
        if closest_verb and closest_aux:
            if min_distance_verb < min_distance_aux:
                return closest_verb
            else:
                return closest_aux
        elif closest_verb:
            return closest_verb
        elif closest_aux:
            return closest_aux
        else:
            return '/'  # Return '/' if no relevant forms are found

    remove_SPACE()

    # Call the function with the marked input folder path
    analyze(input_path)

    # Read the original CSV file into a DataFrame
    df = pd.read_csv(output_filename)

    # Apply the function to create the new column
    df['Verb'] = df.apply(closest_verb_non_infinitive, axis=1)
    df['Inf_Verb'] = df.apply(closest_verb_infinitive, axis=1)

    # Save the modified DataFrame back to a CSV and XLSX
    df.to_csv(output_filename, index=False)

    # Check if the file exists before trying to delete it
    os.remove(input_path + "\\temp.csv")

    print("Successfully created data")

from datetime import date
current_date = date.today().isoformat()

int_data = "intensifier_data_CART_" + current_date + ".csv"

create_data("text/tagged", int_data)

cart_data = int_data

cart_df = pd.read_csv(cart_data)

# make numbered based on speaker col
def add_number(df, output_file):
    def numero(row, count_dict={}):
        # Split the original label to get the speaker number
        speaker_number = row['Speaker']

        # Update the count for this speaker number
        count_dict[speaker_number] = count_dict.get(speaker_number, 0) + 1

        # Generate the new label
        new_label = f'{speaker_number}_{count_dict[speaker_number]:02d}'
        return new_label
    df['Number'] = df.apply(numero, axis=1)
    df.to_csv(output_file)

add_number(cart_df, cart_data)

# add syl col
def count_syllables(word):
    # Remove silent 'u' in gue/gui/que/qui unless it has a diaeresis (ü)
    word = re.sub(r'gue|gui|que|qui', lambda m: m.group(0).replace('u', ''), word)

    # Count vowel groups (as a simple approximation of syllables)
    syllables = re.findall(r'[aeiouáéíóúü]+', word)
    
    return len(syllables)

def addSyllableCol(df):
    # Create a new column for the number of syllables in the text
    # Does not account for diphthongs or triphthongs
    df['Syllable'] = df['Adj'].apply(count_syllables)
    return df

df = addSyllableCol(cart_df)

df.to_csv(cart_data, index=False)

## BELOW IS THE CODE FOR SPEAKER DATA TO THE CSV

import pandas as pd

def iterate_df_and_update(id_df, int_path):
    transformed_data = []
    int_df = pd.read_csv(int_path)

    # Iterate through each row in df
    for _, row in int_df.iterrows():
        Speaker = row['Speaker']
        id_row = id_df[id_df['Speaker'] == Speaker]

        if not id_row.empty:
            # Convert id_row to a dict, excluding the ID column
            id_data = id_row.iloc[0].to_dict()
            id_data.pop("Speaker", None)

            # Combine row data with id_data
            merged_row = {**row.to_dict(), **id_data}
            transformed_data.append(merged_row)

    transformed_df = pd.DataFrame(transformed_data)
    transformed_df.to_csv(int_path, index=False)
    print(f"Transformed data saved to {int_path}")

from datetime import date
current_date = date.today().isoformat()

speaker_data = "speaker_data_CART_" + current_date + ".xlsx"
speaker_df = pd.read_excel(speaker_data)
int_data = "intensifier_data_CART_" + current_date + ".csv"

iterate_df_and_update(speaker_df, int_data)

df = pd.read_csv(int_data)
for col in df.select_dtypes(include=[object]).columns:
    # replaces commas with empty string, can change to s.t. else if you want
    df[col] = df[col].str.replace(',', '', regex=False)
df.to_csv(int_data, index=False)
df.to_excel(int_data[:-4] + ".xlsx", index=False)