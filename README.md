# IntensifierResearch

This is the code I used to analyze a number of Spanish transcripts for sociolinguistic research.

Stuff you'll need: [Python ](https://www.python.org/downloads/)(I recommend also downloading [VSCode](https://code.visualstudio.com/download) and adding the Python extension, although you could just use the cmd line) and [TagAnt](https://www.laurenceanthony.net/software/tagant/)

1. Dowload all the files on the GitHub by going to Code -> Dowload Zip. You put the files whereever you want.
2. Put the original .docx transcript files in a folder called "original".
3. Create an excel sheet that is called "speaker_data_CART_YYYY-MM-DD.xlsx" (with the exact same caps, punct, etc.) that you'll use to write out the information for each speaker you have. Go through each transcript and get that information (their gender, education level, age, etc.) with each row being a seperate speaker.
4. Then, go through each transcript and remove everything up until the first line of actual dialogue.
5. Run step_5_clean_raw_data.py
6. Place the text folder into TagAnt to create a tagged version of all the files (make sure that you use the Spanish model, not the English one). For the Display Information, select "word+pos_tag+lemma".
7. Run step_7_tagged_to_csv.py.
8. Now you have an excel sheet with all the data. You can try making some graphs of the data using [Language Variation Suite](https://languagevariationsuite.shinyapps.io/Pages/) or anything else.

If you get errors or are confused you can email me (though I might be busy) or you could try to just copypaste the error and code into ChatGPT.
