# thai-en-ai-ebook-translator

 !! work in progress !! all components are there, but it will not yet produce anything.

use google gemini-api or chatgpt-api to translate thai html / text files and turn them into an ebook. 

possibility to add translitterations and different translations to compare. 

----

used python packages:

pip install pandas numpy pillow
pip install google-generativeai
pip3 install torch torchvision torchaudio
pip install pythainlp[full] chardet

also needed:
Windows:
pandoc from https://pandoc.org/epub.html
latex from https://miktex.org/
Linux: packed manager

-----

--- Warning ---

this project is still in early alpha. all components are there, but not yet working..

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