# TODO:
#  - pickle oBlocks. if oBlocks.pickle exists, load and continue with next oBlocks[i]==""
#  - second oBlocks loop to spawn workers by paragraph (transliteration + explain ideoms)
#  - transliterate from thai-language.com
#  - bs4 -> retrieve html page and extract text to <proj>input/input.txt + images
#  - import images
#  - !! pickle oBlocks
#  - handle roman char in translation



#               seems to work good..
#           p mindful_th-en_v02.py  -temp 0.5 -top_p=0.4 -top_k=1
#               good as well
#           p mindful_th-en_v02.py  -temp 0.6 -top_p=0.4 -top_k=1

# termux:
#   pkg install python-grpcio python-pillow   (in termux if venv, needs to passthrough those packages!!)
#   pip install google.generativeai
#   pip install pythainlp tzdata pprint regex chardet

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import concurrent.futures
import re
import sys
import textwrap
import shutil



import argparse
import subprocess
import copy

from google.generativeai.types.generation_types import collections
from lib import my_text
from lib import my_transliteration_paiboon
from lib import my_grab_urls
import pprint
import time


# parser = argparse.ArgumentParser()
# parser.add_argument(
#     "-temp",
#     type=str,
#     default="0.5",
#     help="temperature of the response: 0.0 = strict, 1.0=ceative -> higher means, that less likly choices get more probible, the difference of probibility between likly and unlikly is reduced.",
# )
# parser.add_argument(
#     "-top_k", type=str, default="2", help="top_k (almost loke top_p, but limits output word choices by probibility.)"
# )
# parser.add_argument(
#     "-top_p",
#     type=str,
#     default="0.4",
#     help="top_p nucleus(limit nr of output word choices by only alowing the first N words - sorted by probibility)",
# )
# args = parser.parse_args()
# # use: args.t
# # print(args)  # Will output a Namespace object like Namespace(another_arg='something', test='value')


# conf = {}

def init_config():
    global conf, stats, files

    stats = {}
    stats['start_time'] = time.time()
    stats['total_requests'] = 0
    stats['total_success'] = 0
    stats['total_failed'] = 0
    stats['total_retries'] = 0
    stats['total_tokens_send'] = 0
    stats['total_tokens_received'] = 0
    stats['failed_blocks'] = []

    conf = {}
    conf['project_name'] = "prj_lp_choob_01"

    conf['start_block'] = 31       # start at 0
    conf['end_block'] = 60        # put in 9999 for the end of the book
    conf['max_attempts'] = 15    # maximum retries to send to an ai before giving up
    conf['max_workers'] = 20
    conf['pause_between_retries'] = 5
    conf['max_tokens_per_block'] = 1500


    conf['debug'] = True   # debugger_is_active()    # i couldnt get the debug check to work.. do manually
    conf['debug'] = False   # debugger_is_active()    # i couldnt get the debug check to work.. do manually
    if conf['debug']:
        conf['max_workers'] = 1



    files = {}
    files['out'] = open(conf['project_name'] + "/translated.txt", "w", encoding="utf-8")
    files['error_out'] = open(conf['project_name'] + "/errors.txt", "w", encoding="utf-8")
    files['blocks'] = open(conf['project_name'] + "/blocks.txt", "w", encoding="utf-8")

    try:
        os.makedirs(conf['project_name'], exist_ok=True)
        print(f"Project directory '{conf['project_name']}' created successfully")
    except OSError as error:
        print(f"Loading from Project directory '{conf['project_name']}' ")

    #  google servers (not vertex)
    # gemini pro:
    # Input token limit     30720
    # Output token limit    2048
    # Rate limit  60 requests per minute

    # gemini pro vision:
    # Input token limit     12288
    # Output token limit    4096
    # Rate limit  60 requests per minute

    #  vertex server
    # gemini pro:
    # Input token limit     32,760
    # Output token limit    8,192
    # Rate limit  60 requests per minute

    conf['safty'] = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    }

    conf["prompts"] = {}
    conf["prompts"]["transliterate"] = [
        {
            # "prompt": "transliterate the thai text with the ISO 11940 system. do not include any explanations. keep html tags.\n\nText: ",
            "prompt": "Transliteration is now done through the pythainpl library, together with a dictionary thai(script)->transliteration(paiboon). (not through gemini or chatgpt)",
            # "temperature": "0.6", "top_k": "2", "top_p": "0.4",
            "engine": "transliterate__pythainpl_dict_paiboon", "position": "prepend", "type": "footnote",
        },
    ]
    conf["prompts"]["default"] = [
        {
            "prompt": "translate the text into english. do not include any explanations, just translate. keep html tags and characters that are in roman/latin  unchanged.\n\n ",
            "temperature": "0.6", "top_k": "2", "top_p": "0.4","engine": "gemini", "position": "append", "type": "paragraph",
            "max_tokens": 1400,            # decides how many paragraphs will be send at one time to the AI. 1 = each separatly, 1400 = approx 4 pages of text

        },


    ]
    conf["prompts"]["strict"] = [
        {
            "prompt": "translate the text into english. do not include any explanations, just translate. keep html tags and characters that are in roman/latin  unchanged.\n\n ",
            "temperature": "0.2", "top_k": "1", "top_p": "0.4",
            "engine": "gemini", "position": "append", "type": "footnote", "label": "more litteral",
            "max_tokens": 1400,     # decides how many paragraphs will be send at one time to the AI. 1 = each separatly, 1400 = approx 4 pages of text
        },
    ]
    conf["prompts"]["creative"] = [
        {
            "prompt": "translate the text into english. do not include any explanations, just translate. keep html tags and characters that are in roman/latin  unchanged.\n\n ",
            "temperature": "1.0", "top_k": "3", "top_p": "0.4",
            "engine": "gemini", "position": "append", "type": "footnote", "label": "more readable",
            "max_tokens": 1400,     # decides how many paragraphs will be send at one time to the AI. 1 = each separatly, 1400 = approx 4 pages of text
        },
    ]
    # conf["prompts"]['lern'] = [ "go paragraph by paragraph and explain ideoms and slang terms from each paragraph. keep html tags.\n\n ", "1.0", "3", "0.4", {"position":"append","type":"footnote","label":"details"}]

    # return conf


def debugger_is_active() -> bool:
    """Return if the debugger is currently active"""
    return hasattr(sys, 'gettrace') and sys.gettrace() is not None

def p(arr):
    pprint.pprint(arr)


def run_command(command):
    """Runs a system command.

    Args:
      command: The system command to run.

    Returns:
      The output of the command.
    """

    # result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
    os.system(command)
    return True


def delete_file(file_path):
    """Deletes a file.

    Args:
      file_path: The path to the file to delete.

    Raises:
      FileNotFoundError: If the file does not exist.
    """

    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print(f'File "{file_path}" not found.')


def save_blocks(text):
    files['blocks'].write(text)


def save_error(text):
    files['error_out'].write(text)
    files['error_out'].flush()

def save(text):
    files['out'].write(text)
    files['out'].flush()


def wrap_text(text):
    # save(text)
    t_columns, t_lines = shutil.get_terminal_size()
    """Wraps text to the specified width, breaking lines at word boundaries."""
    paragraphs = []
    wrapped_text = ""
    paragraphs = text.splitlines()  # Split into paragraphs by existing newlines
    wrapped_text = "\n".join(
        # Wrap each paragraph
        textwrap.fill(p, width=t_columns - 1)
        for p in paragraphs
    )
    return wrapped_text



def load_and_split_text(filename, delimiter="\n", max_tokens=1000):
    """
    Loads a text file, splits the content by a specified delimiter,
    and returns the result as an array of blocks.

    Args:
        filename (str): The name of the text file to load.
        delimiter (str, optional): The character to use for splitting the text.
                                   Defaults to '\n' (newline).

    Returns:
        list: An array of text blocks, where each block is a string resulting
              from splitting the file content.
    """

    blocks = []
    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()
        # blocks = content.split(delimiter)
        # blocks = re.split(delimiter, content, flags=re.MULTILINE)

        # reduce all paragraph spacing to only one empty line in between - gemini will get confused otherwise with the paragraph count
        content = re.sub(r'(\n[ \t]*)+\n', '\n\n', content)
        content = re.sub(r'\t', ' ', content)
        content = re.sub(r"^\s+|\s+$", "", content)

        blocks = my_text.split_text_by_tokens(content, max_tokens=max_tokens, delimiter="\n\n", add_paragraph_tag=True)
        # blocks = re.findall(delimiter, content, flags=re.MULTILINE)
        # remove whitespace at beginning of the lines
        for i in range(0, len(blocks)):
            blocks[i] = re.sub(r"^[ ]+", "", blocks[i], flags=re.MULTILINE)
            blocks[i] = re.sub(r"˶", "“", blocks[i], flags=re.MULTILINE)
            blocks[i] = re.sub(r"˝", "”", blocks[i], flags=re.MULTILINE)
    return blocks


def query_gemini(prompt, temperature=0.5, top_p=0.3, top_k=1, safty=None):

    # stats['total_requests'] += 1

    # Replace with your actual Gemini API key
    GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]  # to fetch an environment variable.
    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel("gemini-pro")
    generation = genai.types.GenerationConfig(
        # Only one candidate for now.
        candidate_count=1,
        # stop_sequences=['x'],
        # max_output_tokens=20,
        ## https://medium.com/@daniel.puenteviejo/the-science-of-control-how-temperature-top-p-and-top-k-shape-large-language-models-853cb0480dae
        # (temperature=creativity)
        # Higher temperature=higher chances for less likely tokens to be selected.
        # As temperature values approach 0 the probability to select the words with higher probabilities valuez increase further, making their selection much more likely.
        # Conversely, when the temperature gets much higher, the probabilities between the words that can be selected are softened, making more unexpected words more likely to be selected
        temperature=temperature,  # 0=strickt, 1=creative/random
        # (top_k = diversity)
        # def: Top_k (Top-k Sampling): It restricts the selection of tokens to the “k” most likely options, based on their probabilities. This prevents the model from considering tokens with very low probabilities, making the output more focused and coherent.
        # top-k is a technique used to limit the number of possible next tokens during text generation
        # def:
        top_k=top_k,  # default: 1
        # def: Top_p (Nucleus Sampling): It selects the most likely tokens from a probability distribution, considering the cumulative probability until it reaches a predefined threshold “p”. This limits the number of choices and helps avoid overly diverse or nonsensical outputs.
        top_p=top_p,  # Set top_p, default: 1.0
        # for translations try: temperature=0.3, top_k=20
        # ??? The temperature and top_p for underrepresented language generation must be set very low. Lower than in ChatGPT. The perplexity of languages with small amounts of training corpus (think Vietnamese, Portuguese) is very high, like a model with 1/100th the knowledge as English plus the confusion of having English in there also.
        # ??? The AI wasn’t pretrained on language simply to be a translator. It’s more “Throw all human knowledge we’ve got in there”…and see the quality that can come out.
    )

    response = model.generate_content(prompt, safety_settings=safty,
                                      generation_config=generation)  # global, no change
    # print()
    return response


def translate_block(workload_item, conf):

    stat = {}
    stat['requests'] = 0
    stat['success'] = 0
    stat['retries'] = 0
    stat['failed'] = 0
    stat['tokens_send'] = 0
    stat['tokens_received'] = 0
    stat['error_message'] = []
    stat['failed_block_nr'] = None


    # unpack the workload_item tuple (needs to be passed as tuple to run in parallel process)
    block, block_nr, blocks_total = workload_item



    print(f"start block {block_nr} from {blocks_total}")


    collect = {"original": block}

    paragraphs_org = len(my_text.split_paragraphs(block))

    # print(wrap_text(f"\n{blocks[i]}\n\n"))
    for pKey, pValue in conf['prompts'].items():
        success = False
        config_pr = pValue[0]
        config = pValue[1]
        # if setting engine is
        if config["engine"] == "transliterate__pythainpl_dict_paiboon":
            # raise AttributeError('no answer')
            # print(f"Block {block_nr}: transliteration start")
            text = my_transliteration_paiboon.tokenize_and_transliterate(block)
            text = my_text.repare_tags(text)
            # print(f"Block {block_nr}: transliteration end")
            collect[pKey] = text
            success = True

        elif (config["engine"] == "gemini"):
            # create transliteration
            for attempt in range(conf['max_attempts']):
                try:

                    prompt = config_pr['prompt'] + block
                    res = query_gemini(prompt, temperature=float(config_pr['temperature']),
                                       top_k=int(config_pr['top_k']),
                                       top_p=float(config_pr['top_p']),
                                       safty=conf['safty'])

                    stat['requests'] += 1
                    text = res.text

                    count = len(my_text.split_paragraphs(text))
                    if paragraphs_org != count:
                        e = f"    Block {block_nr} {pKey}: paragraph missmatch {attempt + 1}x (pause tread {conf['pause_between_retries']}s) "
                        print(e)
                        stat['error_message'].append(e + "\n\n" + text + "\n\n")
                        stat['retries'] += 1
                        time.sleep(int(conf['pause_between_retries']))
                        continue

                    T_in = my_text.token_count(prompt)
                    T_out = my_text.token_count(text)
                    stat['tokens_send'] += T_in
                    stat['tokens_received'] += T_out
                    # print(wrap_text(f"{res2.text}^[tokens prompt:{T_in}, tokens response:{T_out}]\n\n---\n\n"))
                    collect[pKey] = text

                    success = True
                    stat['success'] += 1
                    t_trlate = my_text.token_count(text)
                    t_console = my_text.remove_html_tags(text)
                    t_console = my_text.remove_newline(t_console)
                    print(f"   Block {block_nr} {pKey}: {t_console[0:30]}..  token: {t_trlate}")
                    break
                except Exception as e:
                    # print(f"An error occurred: {e}")
                    try:
                        # Attempt to access res and possibly res.candidates
                        if hasattr(res, 'prompt_feedback'):
                            err = my_text.remove_newline(str(res.prompt_feedback))
                        else:
                            # print("res exists, but it does not have a candidates attribute.")
                            err = ''
                    except NameError:
                        # print("res does not exist.")
                        err = ''

                    m = f"    Block {block_nr} {pKey}: no / partial Answer {attempt + 1}x (pause tread {conf['pause_between_retries']}s) {err}"
                    print(m)
                    stat['error_message'].append(f"{m}\n")
                    stat['retries'] += 1
                    time.sleep(int(conf['pause_between_retries']))

        else:
            text = f"Warning: engine {pKey} not found"
            collect[pKey] = text
            success = True

        if success == False:
            collect[pKey] = ""
            t_console = my_text.remove_html_tags(block)
            t_console = my_text.remove_newline(t_console, separator=" ")

            m = f"  !!translation failed! Block {block_nr} {pKey}: "
            print(f"{m} {t_console[0:30]}..")
            stat['error_message'].append(f"{m} {t_console[0:150]}\n")
            stat['failed'] += 1
            stat['failed_block_nr'] = block_nr

    return block_nr, collect, stat


def translate_blocks(blocks, start=0, end=10000):
    # initialze the result list
    global stats, conf

    oBlocks = ["" for i in range(0, end - start)]

    for i in range(0, len(blocks)):
        blocks[i] = blocks[i].strip(' \r')
        save_blocks(f"\n\n----next: block {i}-----\n\n" + blocks[i])
    files['blocks'].close()

    #pycharm doesnt like to debug multiprocess, so if debuging -> single process
    if conf['debug']:
        results = []
        for i in range(start, end):
            work = (blocks[i], i, len(oBlocks))
            results.append(translate_block(work, conf))

    else:
        workload = [(blocks[i], i, len(oBlocks)) for i in range(start, end )]  # 12 prompts

        # Use ProcessPoolExecutor to run tasks in separate processes
        with concurrent.futures.ProcessPoolExecutor(conf['max_workers']) as executor:
            # Map the function and arguments to the executor
            # The executor will return results as they are completed
            results = list(executor.map(translate_block, workload, [conf] * len(workload)))

    for r in results:
        oBlocks[r[0]] = r[1]
        s = r[2]
        stats['total_requests'] += s['requests']
        stats['total_success'] += s['success']
        stats['total_retries'] += s['retries']
        stats['total_failed'] += s['failed']
        stats['total_tokens_send'] += s['tokens_send']
        stats['total_tokens_received'] += s['tokens_received']
        save_error(" ".join(s['error_message']))
        if s['failed_block_nr'] is not None:
            stats['failed_blocks'].append(s['failed_block_nr'])

    return oBlocks


def main():
    global conf

    my_grab_urls.prepare_input(conf['project_name'])

    filename = conf['project_name'] + "/input.txt"
    # blocks = load_and_split_text(filename, delimiter='----')
    blocks = load_and_split_text(filename, delimiter="\n\n", max_tokens=conf['max_tokens_per_block'])
    # for block in blocks:
    #     print(' >'+block+'\n')

    #  with the paiboon+ system.  treat text in quotation marks like normal text.


    # batching
    start_block = conf['start_block']
    end_block = conf['end_block']

    if end_block > len(blocks):
        end_block = len(blocks)

    oBlocks = translate_blocks(blocks, start_block, end_block)

    book = []

    # merge everything together
    for i in range(0, len(oBlocks)):
        text = ""

        paragraph_lists = {}
        for pKey, pValue in oBlocks[i].items():
            # paragraph_list is split by html tag.
            #   if a paragraph is not found in the translation -> item=''
            #   pKey==original -> is the meassure
            paragraph_lists[pKey] = my_text.split_paragraphs(pValue, use_html_tag_guides=True)

        for j in range(0, len(paragraph_lists["original"])):
            paragraph = f"{paragraph_lists['original'][j]}"

            for pKey, pValue in conf['prompts'].items():

                meta = pValue[1]

                if len(paragraph_lists[pKey]) > j:

                    part = paragraph_lists[pKey][j]
                    if part == "" or part is None:
                        continue
                    if "label" in meta:
                        part = f"{meta['label']}: {part}"
                    if meta["type"] == "footnote":
                        part = f" ^[{part}] "
                    else:
                        part = f"\n\n {part} "
                    if meta["position"] == "prepend":
                        paragraph = part + paragraph
                    else:
                        paragraph = paragraph + part

            text = text + paragraph + "\n\n"

        tok_block = my_text.token_count(oBlocks[i]["original"])
        tok_default = my_text.token_count(oBlocks[i]["default"])
        # save_error(f'--- block {i}  tokens original: {tok_block} | tokens translation (default): {tok_default} ---\n\n' + oBlocks[i]["default"])
        book.append(
            text
            + " -- prev block: "
            + str(i + 1)
            + r" tokens original: {tok_block} | tokens translation (default): {tok_default} --"
        )

    save("\n\n".join(book))

    # Stop the timer
    end_time = time.time()

    # Calculate the execution time
    execution_time = end_time - stats['start_time']

    # Convert the execution time to hh:mm:ss format
    h = int(execution_time // 3600)
    m = int((execution_time % 3600) // 60)
    s = int(execution_time % 60)


    if stats['total_requests'] == 0:
        seconds_per_prompt = 0
    else:
        seconds_per_prompt = round(execution_time / stats['total_requests'], 3)

    prompts_stats = ""
    for key, values in conf['prompts'].items():
        c = values[0]
        prompts_stats = (
                prompts_stats
                + f"""
    -----
    
    **{key} prompt (temperature: {c['temperature']} | top_k: {c['top_k']} | top_p: {c['top_p']}):**  \\
    "{c['prompt']}"
        """
        )

    stats_text = f"""
    
    # statistics
    
    **Ai Model** 
    
    {prompts_stats}
    
    ----
    
    sum blocks processed: {len(oBlocks)}  
    sum tokens prompt: {stats['total_tokens_send']}  \\
    sum tokens response (only translation): {stats['total_tokens_received']}  \\
    
    ----
    
    total ecexution time: {h}:{m}:{s}  \\
    total prompts send to AI: {stats['total_requests']}  \\
    total successfull prompts (retries): {stats['total_success']}  \\
    total failed prompts (retries): {stats['total_retries']}  \\
    total failed prompts (given up on): {stats['total_failed']}  \\
    average seconds per prompt: {seconds_per_prompt}  \\
    
    
    """
    print(wrap_text(stats_text))
    save(stats_text)
    files['out'].close()
    files['error_out'].close()


    # https://pandoc.org/installing.html            #install pandoc
    # https://miktex.org/download                   #install latex (used by pandoc)
    p = r"C:\Users\watdo\AppData\Local\Pandoc"+"\\"
    p2 = r"C:\Users\watdo\python\thai-en-ai-ebook-translator"+"\\"
    c = f"pandoc.exe -f markdown+inline_notes -t epub --css='{p2}lib\\epub.css' --metadata title='gemini translation test' -o '{p2}{conf['project_name']}\\{conf['project_name']}.epub' '{p2}{conf['project_name']}\\translated.txt'"
    print(p+c)
    # windows needs the absolut path to pandoc
    run_command(  p+c )


if __name__ == '__main__':
    init_config()
    main()
