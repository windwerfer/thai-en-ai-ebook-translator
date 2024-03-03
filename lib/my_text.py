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


import importlib


import argparse
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
    latin_chars = 0
    for char in text:
        if ord(char) >= 32 and ord(char) <= 126:  # Check for ASCII range
            latin_chars += 1
    return latin_chars // 4


def token_count(text):
    th = token_count_thai0(text)
    en = token_count_eng0(text)
    return th + en

def remove_html_tags(text):
    pattern = r"<.*?>"
    return re.sub(pattern, "", text)

def remove_newline(text):
    pattern = r"\n"
    return re.sub(pattern, "", text)


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

def split_paragraphs(text, delimiter="\n[ ]*\n", use_html_tag_guides=False, trim=True):
    paragraph = re.split(delimiter, text)
    if trim:
        for i in range(0, len(paragraph)):
            paragraph[i] = paragraph[i].strip()
    if use_html_tag_guides:
        paragraph_sorted = []
        for p in paragraph:
            # find id
            regex = r"<p id='Pa_(\d+)'></p>"
            matches = re.findall(regex, p)
            if matches:
                id_p = matches[0]
            else:
                continue

            # remove id tag from p
            p = re.sub(r"<p id='Pa_\d+'></p>[ ]*", "", p)
            # insert p in at the right place of the list paragraph_sorted
            # If the index is greater than the length of the list, new elements will be created with the value `None`.
            paragraph_sorted.insert(int(id_p), p)
        paragraph = paragraph_sorted

    return paragraph


def split_text_by_tokens(text, max_tokens=1000, delimiter="\n\n", add_paragraph_tag=True):
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

    paragraphs = split_paragraphs(text, delimiter=delimiter)

    for i in range(0, len(paragraphs)):
        paragraph = paragraphs[i]
        paragraph_tag = f"<p id='Pa_{i}'></p>"
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
