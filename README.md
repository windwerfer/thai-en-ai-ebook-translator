# thai-en-ai-ebook-translator

 !! work in progress !! all components are there, but it will not yet produce anything.

use google gemini-api or chatgpt-api to translate thai html / text files and turn them into an ebook. 

possibility to add translitterations and different translations to compare. 

----

used python packages:

pip install pandas numpy pillow
pip install google-generativeai
pip3 install torch torchvision torchaudio  -- probably not any more
pip install pythainlp[full] chardet

also needed:
Windows:
pandoc from https://pandoc.org/epub.html
latex from https://miktex.org/
Linux: packed manager

or: pip install pypandoc-binary

-----

--- Warning ---

this project is still in early alpha. it might work, but probably not without some python knowledge.

set the environment variable GOOGLE_API_KEY to your api key (get one free if you have a google account under https://aistudio.google.com/app/apikey)

to run the script install the dependencies from above into a new python virtual environment and then start the script with:

  > python create_thai-en_ebook_v02.py -p project_name -i input_text_file.txt

input_text_file.txt needs to be a text file, with paragraphs separated by a blank line.

it will create the file project_name\saved_paragraphs.pickle to keep all the already processed paragraphs. reruning the script continues where you left of.

most of the settings are in the python create_thai-en_ebook_v02.py file in the function init_config() pretty close to the top.

there you can set what the prompts will be (eg. 'translate into english.').

the script will take a couple of paragraphs (not more than conf['max_tokens_per_query__gemini']) and send them together with the prompt to gemini.

the results will be saved in the saved_paragraphs.pickle file. it will only send conf['max_groups_to_process'] groups before exiting (good for testing).

when the script is run again, it will continue where it left of, and resend the groups that failed before.

at the moment it creates an epub and a cvs file with the columns original, transliteration (for thai), prompt1, prompt2, prompt3, prompt4 but that can be configured with the variables
conf['prompts_to_process'] and conf['prompts_to_display']

each prompt can be fine tuned with temperature, top_k and top_p values (search for conf['prompts']['gemini_default_2024.03'] ). add more or remove some if you want.

the script sends 10 prompts at the same time. can be configured with conf['max_workers'] (google will refuse to answer if too many are send at the same time).

in lib/word_substitution_list.data is a list of values that will be substituted in the text, before they are send to gemini.

this script can be used and modified however you want (if you get it to run).


---- Transliteration to Paiboon+ ----

original script from https://github.com/wannaphong/thai-grapheme-to-phoneme
(now updated to work with pythainlp 5.0.1)

his project uses a dictionary (lib/thai2ipa.data) to convert thai script -> ipa transliteration 

there is an online converter that uses thai2ipa.data dictionary as well: 
https://thai-notes.com/tools/thai2ipa.html

it is originally from http://www.sealang.net/thai/dictionary.htm

how it works: 
1) using pythainlp.tokenize() to split the thai sentences into words
2) using the dictionary data from thai2ipa.data to transliterate<br>
   fallback if word not in dictionary: pythainlp.romaniz() for transliteration 