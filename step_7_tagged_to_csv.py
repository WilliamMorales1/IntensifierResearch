import os
import pandas as pd
import re
from datetime import date

intensifier_list = ["absolutamente", "bastante", "casi", "completamente", "demasiado", "estrictamente",
            "especialmente", "extremadamente", "harto", "increíblemente", "mucho",
            "muy", "plenamente", "realmente", "sumamente", "súper", "totalmente", "verdaderamente",
            "bien", "super", "supel", "re", "archi"]

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


def remove_SPACE(input_path):
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

def is_well_formed(word):
    if any(word.endswith(c) for c in 'oaeslndr') and re.match(r'^[a-zA-Z_áéíóúüñÁÉÍÓÚÜÑí]+$', word):
        return True
    else:
        return False

def is_adj(word):
    adj_match = re.search(r'^(.*)_ADJ_', word)
    lex_adj_match = re.search(r'_ADJ_(.+)', word)
    if adj_match and lex_adj_match and is_well_formed(word) and not(word.endswith('mente')):
        return True
    return False

def get_adj(word):
    adj_match = re.search(r'^(.*)_ADJ_', word)
    adv_match = re.search(r'_ADJ_(.+)', word)

    adjective = adj_match.group(1) # type: ignore
    lex_adjective = adv_match.group(1) # type: ignore
    
    # apocope corrections
    if lex_adjective in apocope_dict:
        lex_adjective = apocope_dict[lex_adjective]
    if lex_adjective.endswith("s") and lex_adjective != "lejos":
        lex_adjective = lex_adjective[:-1]
    if lex_adjective.endswith("a"):
        lex_adjective = lex_adjective[:-1] + "o"
    
    # write re adjectives that could be with the re- intensifier
    if adjective.startswith("re"):
        with open("re-words.txt", "a", encoding="utf-8") as f:
            f.write(adjective + "\n")

    return adjective.lower(), lex_adjective.lower()

def is_adv(word):
    adv_match = re.search(r'^(.*)_ADV_', word)
    if adv_match and is_well_formed(word) and word not in intensifier_list:
        return True
    return False

def get_adv(word):
    adv_match = re.search(r'^(.*)_ADV_', word)
    adverb = adv_match.group(1) # type: ignore
    if adverb.startswith("re"):
        with open("re-words.txt", "a", encoding="utf-8") as f:
            f.write(adverb + "\n")
    return adverb.lower()

def is_int(word):
    int_match = re.search(r'^(.*?)_', word)
    if int_match and int_match.group(1) in intensifier_list:
        return True
    return False

def get_int(word):
    int_match = re.search(r'^(.*?)_', word)
    intensifier = int_match.group(1) # type: ignore
    if intensifier == 'super' or intensifier == 'supel':
        intensifier = 'súper'
    return intensifier.lower()

def process_segment(segment, speaker):
    rows = []
    
    intensifier = None
    adjective = None
    lex_adjective = None
    attributive = None
    noun = None
    double = None

    # Split the segment into words
    words = segment.split()

    # Process each word in the segment
    for i, word in enumerate(words):
        # bueno
        if is_adj(word):
            adjective, lex_adjective = get_adj(word)
            
            # noun adj
            if i > 0 and "_NOUN_" in words[i-1] and not any(inter in words[i-1] for inter in intensifier_list):
                attributive = "attributive"
                noun = re.search(r'^(.*?)_', words[i-1]).group(1) # type: ignore
            # adj noun
            elif i < len(words) - 1 and "_NOUN_" in words[i+1]:
                attributive = "attributive"
                noun = re.search(r'^(.*?)_', words[i+1]).group(1) # type: ignore
            # noun int adj
            elif i > 1 and "_NOUN_" in words[i-2] and any(inter in words[i-1] for inter in intensifier_list):
                attributive = "attributive"
                noun = re.search(r'^(.*?)_', words[i-2]).group(1) # type: ignore
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

            # muy bueno
            if i > 0 and is_int(words[i-1]):
                intensifier = get_int(words[i-1])
                # no muy bueno
                if i > 1 and words[i-2] == "no_ADV_no":
                    continue
                # muy muy bueno
                elif i > 1 and is_int(words[i-2]):
                    double = get_int(words[i-2])
                else:
                    double = '/'
            else:
                intensifier = '/'
                double = '/'

            if lex_adjective.endswith("ísimo"):
                intensifier = '-ísimo'
                adjective = adjective.replace('quísim', 'c')
                lex_adjective = lex_adjective.replace('quísim', 'c')
                adjective = adjective.replace('guísim', 'g')
                lex_adjective = lex_adjective.replace('guísim', 'g')
                adjective = adjective.replace('ísim', '')
                lex_adjective = lex_adjective.replace('ísim', '')
            
            if lex_adjective.startswith("archi"):
                intensifier = 'archi-'
                adjective = adjective.replace('archi', '')
                lex_adjective = lex_adjective.replace('archi', '')

            # FRASE
            phrase_tagged = ' '.join(words)
            phrase = ' '.join(re.sub(r'_.*', '', word) for word in words)

            row_data = {
                'Speaker': speaker,
                'Phr_tagged': phrase_tagged,
                'Phr': phrase,
                'Double': double,
                'Int': intensifier,
                'Adv': '/',
                'Adj': adjective,
                'Lex_Adj': lex_adjective,
                'Adj_type': attributive,
                'Noun': noun.lower(),
            }
            rows.append(row_data)

        # IF NON-INT ADV
        if is_adv(word):
            adverb = get_adv(word)
            
            # muy lejos
            if i > 0 and is_int(words[i-1]):
                intensifier = get_int(words[i-1])
                # no muy lejos
                if i > 1 and words[i-2] == "no_ADV_no":
                    continue
                # muy muy lejos
                elif i > 1 and is_int(words[i-2]):
                    double = get_int(words[i-2])
                else:
                    double = '/'
            else:
                intensifier = '/'
                double = '/'
            
            # FRASE REAL
            phrase_tagged = ' '.join(words)
            phrase = ' '.join(re.sub(r'_.*', '', word) for word in words)

            row_data = {
                'Speaker': speaker,
                'Phr_tagged': phrase_tagged,
                'Phr': phrase,
                'Double': double,
                'Int': intensifier,
                'Adv': adverb,
                'Adj': '/',
                'Lex_Adj': '/',
                'Adj_type': '/',
                'Noun': '/',
            }
            rows.append(row_data)
    return rows


def analyze(input_path, output_filename):
    # no mas, tan
    # Create a list to store data frames
    data_frames = []

    # remove old re-words.txt
    if os.path.exists("re-words.txt"):
        os.remove("re-words.txt")

    # Iterate over marked files in the input folder
    for filename in os.listdir(input_path):
        # SPEAKER
        speaker = filename[:-4]
        print("Started analyzing:", speaker)

        # Construct the absolute path to the marked file
        marked_file_path = os.path.join(input_path, filename)

        # Initialize a list to store row data
        rows = []

        # Read the marked text from the file
        with open(marked_file_path, "r", encoding="utf-8") as file:
            # Read entire file and replace all newlines
            content = file.read().replace('\n', ' ')

            # Split the content into segments based on custom sentence-ending punctuation
            segments = re.split(r'(?<=[,.!?]_PUNCT_[,.!?])', content)

            # Process each segment
            for segment in segments:
                seg_rows = process_segment(segment, speaker)
                rows.extend(seg_rows)
        
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
    
    # Check if the file exists before trying to delete it
    os.remove(input_path + "\\temp.csv")
    
    print("Successfully created data")
    print("re- words saved to re-words.txt")

    # Save the DataFrame to a CSV file
    data.to_csv(output_filename, index=False)
    return data


def closest_verb_non_infinitive(row):
    phrase = row['Phr_tagged']
    intensifier_pos = phrase.find(row['Adj'])
    
    if intensifier_pos == -1:
        return '/'
    
    # Find the sentence containing the intensifier
    # Split by periods and track positions
    period_before = phrase.rfind('.', 0, intensifier_pos)
    sentence_start = 0 if period_before == -1 else period_before + 1  # +1 to skip the period
    sentence_end = phrase.find('.', intensifier_pos)
    if sentence_end == -1:
        sentence_end = len(phrase)
    
    sentence = phrase[sentence_start:sentence_end]
    # Adjust intensifier position relative to the sentence
    intensifier_pos_in_sentence = intensifier_pos - sentence_start
    
    # Initialize minimum distances and closest matches
    min_distance_verb = float('inf')
    min_distance_aux = float('inf')
    closest_verb = None
    closest_aux = None
    
    # Regular expression to find verb and auxiliary patterns
    pattern = r'\b(\w+)_(VERB|AUX)_(\w+)\b'
    
    for match in re.finditer(pattern, sentence):
        start_pos = match.start()
        end_pos = match.end()
        match_center = (start_pos + end_pos) // 2
        distance = abs(match_center - intensifier_pos_in_sentence)
        
        if 'VERB' in match.group():
            if distance < min_distance_verb:
                min_distance_verb = distance
                closest_verb = match.group(1)
        elif 'AUX' in match.group():
            if distance < min_distance_aux:
                min_distance_aux = distance
                closest_aux = match.group(1)
    
    # Determine which is closer
    if closest_verb and closest_aux:
        return closest_verb if min_distance_verb < min_distance_aux else closest_aux
    elif closest_verb:
        return closest_verb
    elif closest_aux:
        return closest_aux
    else:
        return '/'


def closest_verb_infinitive(row):
    phrase = row['Phr_tagged']
    intensifier_pos = phrase.find(row['Adj'])
    
    if intensifier_pos == -1:
        return '/'
    
    # Find the sentence containing the intensifier
    period_before = phrase.rfind('.', 0, intensifier_pos)
    sentence_start = 0 if period_before == -1 else period_before + 1
    sentence_end = phrase.find('.', intensifier_pos)
    if sentence_end == -1:
        sentence_end = len(phrase)
    
    sentence = phrase[sentence_start:sentence_end]
    # Adjust intensifier position relative to the sentence
    intensifier_pos_in_sentence = intensifier_pos - sentence_start
    
    # Initialize minimum distances and closest matches
    min_distance_verb = float('inf')
    min_distance_aux = float('inf')
    closest_verb = None
    closest_aux = None
    
    # Regular expression to find verb and auxiliary patterns
    pattern = r'\b(\w+)_(VERB|AUX)_(\w+)\b'
    
    for match in re.finditer(pattern, sentence):
        start_pos = match.start()
        end_pos = match.end()
        match_center = (start_pos + end_pos) // 2
        distance = abs(match_center - intensifier_pos_in_sentence)
        
        if 'VERB' in match.group():
            if distance < min_distance_verb:
                min_distance_verb = distance
                closest_verb = match.group(3)
        elif 'AUX' in match.group():
            if distance < min_distance_aux:
                min_distance_aux = distance
                closest_aux = match.group(3)
    
    # Determine which is closer
    if closest_verb and closest_aux:
        return closest_verb if min_distance_verb < min_distance_aux else closest_aux
    elif closest_verb:
        return closest_verb
    elif closest_aux:
        return closest_aux
    else:
        return '/'


# make numbered based on speaker col
def numero(row, count_dict={}):
    # Split the original label to get the speaker number
    speaker_number = row['Speaker']

    # Update the count for this speaker number
    count_dict[speaker_number] = count_dict.get(speaker_number, 0) + 1

    # Generate the new label
    new_label = f'{speaker_number}_{count_dict[speaker_number]:02d}'
    return new_label


# add syl col
def count_syllables(word):
    # Remove silent 'u' in gue/gui/que/qui unless it has a diaeresis (ü)
    word = re.sub(r'gue|gui|que|qui', lambda m: m.group(0).replace('u', ''), word)

    # Count vowel groups (as a simple approximation of syllables)
    syllables = re.findall(r'[aeiouáéíóúü]+', word)
    
    return len(syllables)


def merge_speaker_data(id_df, int_df):
    transformed_data = []

    # Iterate through each row in df
    for _, row in int_df.iterrows():
        Speaker = row['Speaker']
        id_row = id_df[id_df['Speaker'] == Speaker]

        if not id_row.empty:
            # Convert id_row to a dict, excluding the Speaker column
            row_data = row.to_dict()
            id_data = id_row.iloc[0].to_dict()
            id_data.pop("Speaker", None)

            # Combine row data with id_data
            merged_row = {**row_data}
            for key, value in id_data.items():
                if pd.notna(value):  # Only use id_data value if it's not null/NaN
                    merged_row[key] = value
            
            transformed_data.append(merged_row)

    transformed_df = pd.DataFrame(transformed_data)
    print(f"Speaker data merged into intensifer data")
    return transformed_df


if __name__ == "__main__":
    input = "tagged/ALL_tagged"
    output = "intensifier_data_" + date.today().isoformat() + ".csv"
    speaker_df = pd.read_excel("speaker_data/speaker_data_ALL_2026-3-12.xlsx")

    remove_SPACE(input) # writes without space back to files
    df = analyze(input, output)

    # Apply the function to create the new column
    df['Verb'] = df.apply(closest_verb_non_infinitive, axis=1)
    df['Inf_Verb'] = df.apply(closest_verb_infinitive, axis=1)
    df['Number'] = df.apply(numero, axis=1)
    df['Syllable'] = df['Adj'].apply(count_syllables)
    df = merge_speaker_data(speaker_df, df)

    for col in df.select_dtypes(include=[object]).columns:
        # replaces commas with empty string, can change to sum else if you want
        df[col] = df[col].str.replace(',', '', regex=False)
    
    df.to_excel(output[:-4] + ".xlsx", index=False)

    print("Make sure to manually check the -ísimo cases!")
