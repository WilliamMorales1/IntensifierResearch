# IntensifierResearch

This is the code I used to analyze a number of Spanish transcripts for sociolinguistic research.

Stuff you'll need: Python and Jupyter (I recommend just downloading [VSCode ](https://code.visualstudio.com/download)and adding the Python and Jupyter extensions) and [TagAnt](https://www.laurenceanthony.net/software/tagant/)

1. Dowload all the files on the GitHub by going to Code -> Dowload Zip. You put the files whereever you want.
2. Put the original .docx transcript files in datos/original.
3. Create an excel sheet that you'll use to write out the information for each speaker you have. Go through each transcript and get that information (their gender, education level, age, etc.) with each row being a seperate speaker.
4. Then, go through each transcript and remove everything up until the first line of actual dialogue.
5. Run Raw_data_to_Cleaned.py (this converts the .docx's into .txt's). It should make a new folder of txt's called text.
6. Place the text folder into TagAnt to create a tagged version of all the files (make sure that you use the Spanish model, not the English one). For the Display Information, select "word+pos_tag+lemma" Move the newly created tagged folder to be under datos (so datos/tagged).
7. Run each cell in Tagged_to_Data.ipynb. This'll create an excel sheet with all the data for the intensifiers (including null cases).
8. Run id_data_to_tokens.py. This will combine the excell sheet with the information for every speaker that you made (id_df) with the excel sheet with all the intensifier data made in step 7 (int_df).
9. Now you have an excel sheet with all the data. You can try making some graphs of the data using [Language Variation Suite](https://languagevariationsuite.shinyapps.io/Pages/) or anything else. 

If you get errors or are confused you can email me (though I might be busy) or you could try to just copypaste the error and code into ChatGPT.
