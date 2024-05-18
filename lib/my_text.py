#### thai language tools (word split, tokenize..)

#  1) pretty light weight, runs in termux venv..
# pip install pythainlp  (good thai tokenizer ~20mb)
# from pythainlp.tokenize import word_tokenize

#  2) nlkt  (big i think..)
# first: pip install nltk
# second: open a python prompt and execute: nltk.download('punkt')
#    but: not good foor thai
# import nltk
# from nltk.tokenize import word_tokenize  # good for english

# 3) pip install deepcut  - another thai tokenizer
#  (2mb but loooots of dependencies incl. tensorflow with 200mb..)
# import deepcut


import argparse
import importlib
import json
import re


# imoprt modules dynamically, only when need
def import_module(module_name, func_name):
    """
    Imports a module only if a specific function is loaded.

    Args:
      module_name: The name of the module to import.
      func_name: The name of the function to check if loaded.

    Returns:
      The imported module if the function is loaded, None otherwise.
    """
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, func_name):
            return module
    except ImportError:
        pass
    return None


# calculate tokens - or for speed: guess
def thai_tokens(text, engine="newmm"):
    guess = False
    guess = True
    if guess:
        # thai text is almost one char= one token..
        return len(text) // 2
    else:
        tokenize = import_module("pythainlp.tokenize", "word_tokenize")
        # https://platform.openai.com/tokenizer   thai: 3200chr => 3000tokens
        #  so.. almost 1 token = 1 char => no need for tokenizers..
        #  english: 1 token ~4 characters of text for common English text
        # https://pythainlp.github.io/docs/5.0/api/tokenize.html
        tokens = tokenize.word_tokenize(text, engine=engine)  # newmm (default),
        return len(tokens)


def extract_thai(text):
    thai_text = ""
    for char in text:
        if 0xE01 <= ord(char) <= 0xE5B:  # Check for Thai Unicode range
            thai_text += char
    return thai_text


def extract_latin(text):
    latin_text = ""
    for char in text:
        # if ord(char) >= 32 and ord(char) <= 126:  # Check for ASCII range
        if ord(char) >= 0 and ord(char) <= 126:  # Check for ASCII range + space,!? ..
            latin_text += char
    return latin_text


def token_count_thai0(text):
    """
        guesses how many tokens are in the text. counts only thai char. (approximately 1 token per char for chatgpt)
        more precise token counts use more complex libraries (e.g. word separation). just not necessary.
    :param text:
    :return:
    """
    thai_chars = 0
    for char in text:
        if 0xE01 <= ord(char) <= 0xE5B:  # Check for Thai Unicode range
            thai_chars += 1
    return thai_chars


# gemini counts are a lot lower: char 3200 | ChatGPT 3010 tokens | gemini 1300 tokens
#                               pythainlp-newmm 914 token
def token_count_thai1(text):
    text = extract_thai(text)
    token_count = thai_tokens(text, engine="newmm")  # newmm (default),
    return token_count


def token_count_thai2(text):
    text = extract_thai(text)
    token_count = thai_tokens(text, engine="mm")
    return token_count


def token_count_eng0(text):
    """
        gives approximate token count (4 char ~ 1 token). only considers latin char. good enough for this project.
    :param text:
    :return:
    """
    latin_chars = 0
    for char in text:
        if ord(char) >= 32 and ord(char) <= 126:  # Check for ASCII range
            latin_chars += 1
    return latin_chars // 4


def token_count(text):
    """
        returns approximate token count. thai and english will be counted separately to judge more correctly.
        4 en char ~ 1 token, 1 thai char ~ 1 token
    :param text:
    :return:
    """
    th = token_count_thai0(text)
    en = token_count_eng0(text)
    return th + en


def remove_html_tags(text):
    pattern = r"<.*?>"
    return re.sub(pattern, "", text)


def remove_newline(text, separator=" "):
    pattern = r"\n"
    return re.sub(pattern, separator, text)


def repare_tags(text):
    """ the transliterate function (my_transliteration_paiboon.py) messes up the tags.. repair!!
        also remove all html tags except p
    """
    # repare p
    pattern = r"[ ]+<\s+p\s+id\s+= ' ([^ ]+) ' > < / p >"
    repl = r"<p id='\1'></p>"
    text = re.sub(pattern, repl, text)
    # remove all tags that are not p
    pattern = r'<(?!\/?p\b)[^>]*>'
    repl = r""
    text = re.sub(pattern, repl, text)

    return text


def split_paragraphs(text, encoded_as='json', trim=True) -> dict:
    """     encoded_as:
                double_newline      eg. text1\n\ntext2
                newline             eg. text1\ntext2
                list                eg. 1. text1\n\n2. text2
                json                eg {"1":"text1", "2":"text2"}
                xml                 eg <item id="1">text1</item>\n<item id="2">text2</item>
                p                   eg <p id='1'>text1</p>\n<p id='2'>text2</p>

    """
    # remove block notation if there where any
    text = re.sub(r'```(xml)*(\n)*', '', text)

    if encoded_as in ['newline','list','xml','p']:
        paragraphs_list = re.split('\n', text)
    if encoded_as == 'double_newline':
        paragraphs_list = re.split("\n[ ]*\n", text)

    paragraphs = {}
    # using a simple number list to mark paragraph beginnings
    if encoded_as == 'list':
        for i, paragraph in enumerate(paragraphs_list):
            # find id
            regex = r"^\s*(\d+)\."
            matches = re.findall(regex, paragraph)
            if matches:
                id_p = matches[0]
            else:
                continue
            # remove id tag from p
            paragraph = re.sub(r"^\s*(\d+)\.\s*", "", paragraph)
            # insert p in at the right place of the list paragraph_sorted
            # If the index is greater than the length of the list, new elements will be created with the value `None`.
            try:
                paragraphs[int(id_p)] = paragraph
            except ValueError:
                paragraphs[i] = paragraph
    # using html tags to mark paragraphs
    elif encoded_as == 'p':
        for i, paragraph in enumerate(paragraphs_list):
            # find id
            regex = r"<p id='Pa_(\d+)'></p>"
            matches = re.findall(regex, paragraph)
            if matches:
                id_p = matches[0]
            else:
                continue
            # remove id tag from p
            paragraph = re.sub(r"<p id='Pa_\d+'></p>[ ]*", "", paragraph)
            # insert p in at the right place of the list paragraph_sorted
            # If the index is greater than the length of the list, new elements will be created with the value `None`.
            try:
                paragraphs[int(id_p)] = paragraph
            except ValueError:
                paragraphs[i] = paragraph
    elif encoded_as == 'xml':
        for i, paragraph in enumerate(paragraphs_list):
            # find id
            paragraph = re.sub(r'^ +$', "", paragraph)
            if paragraph == '':
                continue

            regex = r'<item id="(\d+)">'
            matches = re.findall(regex, paragraph)
            if matches:
                id_p = matches[0]
            else:
                return []
                continue
            # remove id tag from p
            paragraph = re.sub(r'<item id="\d+">', "", paragraph)
            paragraph = re.sub(r'</item>', "", paragraph)
            # insert p in at the right place of the list paragraph_sorted
            # If the index is greater than the length of the list, new elements will be created with the value `None`.
            try:
                paragraphs[int(id_p)] = paragraph
            except ValueError:
                paragraphs[i] = paragraph
    elif encoded_as == 'json':
        try:
            # Remove everything before the first {
            text = re.sub(r'^.*?\{', '{', text, flags=re.DOTALL)

            # Remove everything after the last }
            text = re.sub(r'\}.*$', '}', text, flags=re.DOTALL)

            # fix forgotten escape char for " inside the value part, eg. {"1":"mr x said:"hi""} -> {"1":"mr x said:\"hi\""}
            text = fix_unescaped_quotes_in_json(text)

            paragraphs = json.loads(text)
        except Exception as e:
            return []
    elif encoded_as in ['newline', 'double_newline']:
        
        for i in range(0, len(paragraphs_list)):
            if trim:
                paragraphs[i] = paragraphs_list[i].strip()
            else:
                paragraphs[i] = paragraphs_list[i]

    return paragraphs


def group_paragraphs_by_tokens(paragraphs, max_tokens, prompt_name, process_only_unfinished=True, add_to_tokencount='json', ):

    """ encode_in:
                list                eg. 1. text1\n\n2. text2
                json                eg {"1":"text1", "2":"text2"}
                xml                 eg <item id="1">text1</item>\n<item id="2">text2</item>
                p                   eg <p id='1'>text1</p>\n<p id='2'>text2</p>


        add_to_tokencount
                    json        add a view char to judge tokens better -> "0232":"",
                    xml         add a view char to judge tokens better -> <item id="0007"></item>
    """

    paragraph_groups = []
    current_group = []
    current_group_tokens = 0
    previous_added_paragraph = 0

    for i in range(len(paragraphs)):
        # check if paragraph was already processed by prompt_name
        # and ignore block if already processed
        if prompt_name in paragraphs[i] and 'success' in paragraphs[i][prompt_name] and \
                paragraphs[i][prompt_name]['success'] and process_only_unfinished:
            continue

        # test for only creating continous blocks (simulates paragraph successfully queried)
        # if i == 3 or i == 5:
        #     continue

        # Check if adding the current paragraph exceeds the max_tokens limit
        #  or: check that it is a continous block of paragraphs
        adding = ''
        if add_to_tokencount=='xml':
            adding = '<item id="0007"></item>'          # approx char that will be added because of xml format
        if add_to_tokencount=='json':
            adding = '"0007":"",'                       # approx char that will be added because of json format

        current_paragraph_tokens = token_count(adding+paragraphs[i]['original']['text'])
        if current_group_tokens + current_paragraph_tokens > max_tokens or previous_added_paragraph + 1 != i:
            # If current group is not empty, add list id to paragraph_groups
            if current_group:
                paragraph_groups.append(current_group)
            # Start a new group with the current paragraph
            current_group = [i]
            current_group_tokens = current_paragraph_tokens
        else:
            # Add paragraph to the current group
            current_group.append(i)
            current_group_tokens += current_paragraph_tokens
        previous_added_paragraph = i

    # Add the last group if it's not empty
    if current_group:
        paragraph_groups.append(current_group)

    return paragraph_groups


def fix_unescaped_quotes_in_json(json):
    """
         fix forgotten escape char for " inside the value part, eg. {"1":"mr x said:"hi""} -> {"1":"mr x said:\"hi\""}
    """
    pattern = r'(.*?:\s*")(.*)(",*)'

    def escape_quotes(match):
        pattern_unescaped_quotes = r'(?<!\\)"'
        m1 = match.group(1)
        m2 = match.group(2)
        m2b = re.sub(pattern_unescaped_quotes, r'\"', m2)
        m3 = match.group(3)
        return f'{m1}{m2b}{m3}'

    # Escape the quotes

    fixed = re.sub(pattern, escape_quotes, json)
    return fixed


def split_text_by_tokens(text, max_tokens=1000, encoded_as='double_newline', add_paragraph_tag=True):
    """Splits a long text into blocks of approximately max_chars characters,
    while respecting paragraph boundaries.

    Args:
        text: The input text to split.
        max_chars: The maximum desired length of each block.

    Returns:
        A list of text blocks.
    """

    blocks = []
    current_block = ""

    text = text

    paragraphs = split_paragraphs(text, encoded_as=encoded_as)

    for i in range(0, len(paragraphs)):
        paragraph = paragraphs[i]
        if add_paragraph_tag:
            paragraph_tag = f"<p id='Pa_{i}'></p>"
        else:
            paragraph_tag = ""
        if token_count_thai1(current_block) + token_count_thai1(paragraph) <= max_tokens:
            current_block += paragraph_tag + paragraph.strip() + delimiter  # Add paragraph with a newline
        else:
            blocks.append(current_block.strip())  # Keep paragraph boundaries intact
            current_block = paragraph_tag + paragraph.strip() + delimiter

    if current_block:
        blocks.append(current_block)

    for i in range(0, len(blocks)):
        blocks[i] = re.sub("\ufeff", "", blocks[i])

    return blocks


def split_text_by_char(text, max_chars=1000):
    """Splits a long text into blocks of approximately max_chars characters,
    while respecting paragraph boundaries.

    Args:
        text: The input text to split.
        max_chars: The maximum desired length of each block.

    Returns:
        A list of text blocks.
    """

    blocks = []
    current_block = ""

    for paragraph in text.split("\n"):
        if len(current_block) + len(paragraph) <= max_chars:
            current_block += paragraph + "\n"  # Add paragraph with a newline
        else:
            blocks.append(current_block.strip())  # Keep paragraph boundaries intact
            current_block = paragraph + "\n"

    if current_block:
        blocks.append(current_block.strip())

    return blocks


def main():
    parser = argparse.ArgumentParser(description="Split Thai text into blocks based on token count.")
    parser.add_argument("-in_file", default="input.txt", help="Path to the input Thai text file.")
    parser.add_argument("-out_file", default="out_blocks.txt", help="Path to the output file for split text blocks.")
    parser.add_argument(
        "--max_tokens", type=int, default=1000, help="Maximum number of tokens per block (default: 1000)"
    )

    args = parser.parse_args()

    with open(args.in_file, "r", encoding="utf-8") as f:
        thai_text = f.read()

    # blocks = split_thai_text_by_tokens(thai_text, args.max_tokens)
    blocks = split_text_by_tokens(thai_text, args.max_tokens)
    tokens_sum = token_count(thai_text)

    with open(args.out_file, "w", encoding="utf-8") as f:
        i = 1
        for block in blocks:
            t = token_count(block)
            t2 = token_count_thai1(block)
            f.write(
                f"\n\n--- block {i} - approx tokens charGPT: {t}, pythainlp tokens {t2}: ---\n\n"
                + re.sub("\ufeff", "", block)
            )
            i += 1
        f.write("tokens sum: " + str(tokens_sum) + "\n\n")


if __name__ == "__main__":
    main()
