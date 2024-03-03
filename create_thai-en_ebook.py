# TODO:
#  - pickle oBlocks. if oBlocks.pickle exists, load and continue with next oBlocks[i]==""
#  - second oBlocks loop to spawn workers by paragraph (translitteration + explain ideoms)
#  - translitterate from thai-language.com
#  - bs4 -> retrieve html page and extract text to <proj>input/input.txt + images
#  - import images


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
import textwrap
import argparse

from google.generativeai.types.generation_types import collections
from lib import my_text
from lib import my_grab_urls
import pprint
import time


parser = argparse.ArgumentParser()
parser.add_argument(
    "-temp",
    type=str,
    default="0.5",
    help="temperature of the response: 0.0 = strict, 1.0=ceative -> higher means, that less likly choices get more probible, the difference of probibility between likly and unlikly is reduced.",
)
parser.add_argument(
    "-top_k", type=str, default="2", help="top_k (almost loke top_p, but limits output word choices by probibility.)"
)
parser.add_argument(
    "-top_p",
    type=str,
    default="0.4",
    help="top_p nucleus(limit nr of output word choices by only alowing the first N words - sorted by probibility)",
)
args = parser.parse_args()
# use: args.t
# print(args)  # Will output a Namespace object like Namespace(another_arg='something', test='value')

project_name = "prj_lp_choob_01"

# Start the timer
start_time = time.time()

total_ai_requests = 0
total_failed = 0
total_retries = 0

start_block = 0
end_block = 1
sum_T_in = 0
sum_T_out = 0

file_out = open(project_name + "/translated.txt", "w", encoding="utf-8")
file_error_out = open(project_name + "debug.txt", "w", encoding="utf-8")

try:
    os.makedirs(project_name, exist_ok=True)
    print("Project directory '%s' created successfully" % directory)
except OSError as error:
    print("Loading from Project directory '%s' " % directory)


def p(arr):
    pprint.pprint(arr)


def run_command(command):
    """Runs a system command.

    Args:
      command: The system command to run.

    Returns:
      The output of the command.
    """

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    output, _ = process.communicate()
    return output.decode("utf-8")


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


def save_error(text):
    file_error_out.write(text)


def save(text):
    file_out.write(text)


def wrap_text(text):
    # save(text)
    t_columns, t_lines = os.get_terminal_size()
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


# Replace with your actual Gemini API key
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]  # to fetch an environment variable.
genai.configure(api_key=GOOGLE_API_KEY)


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


safty = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
}


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
        blocks = my_text.split_text_by_tokens(content, max_tokens=max_tokens, delimiter="\n\n")
        # blocks = re.findall(delimiter, content, flags=re.MULTILINE)
        # remove whitespace at beginning of the lines
        for i in range(0, len(blocks)):
            blocks[i] = re.sub(r"^[ ]+", "", blocks[i], flags=re.MULTILINE)
            blocks[i] = re.sub(r"˶", "“", blocks[i], flags=re.MULTILINE)
            blocks[i] = re.sub(r"˝", "”", blocks[i], flags=re.MULTILINE)
    return blocks


def send_prompt(prompt, temperature=0.5, top_p=0.3, top_k=1):
    global total_ai_requests
    total_ai_requests += 1
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

    response = model.generate_content(prompt, safety_settings=safty, generation_config=generation)  # global, no change
    # print()
    return response


filename = project_name + "input/input.txt"
# blocks = load_and_split_text(filename, delimiter='----')
blocks = load_and_split_text(filename, delimiter="\n\n", max_tokens=1500)
# for block in blocks:
#     print(' >'+block+'\n')


#  with the paiboon+ system.  treat text in quotation marks like normal text.
prompts = {}
prompts["translitterate"] = [
    "translitterate the thai text with the ISO 11940 system. do not include any explanations. keep html tags.\n\nText: ",
    "0.6",
    "2",
    "0.4",
    {"position": "prepend", "type": "footnote"},
]
prompts["default"] = [
    "translate the text into english. do not include any explanations, just translate. keep html tags.\n\n ",
    "0.6",
    "2",
    "0.4",
    {"position": "append", "type": "paragraph"},
]
prompts["strict"] = [
    "translate the text into english. do not include any explanations, just translate. keep html tags.\n\n ",
    "0.2",
    "1",
    "0.4",
    {"position": "append", "type": "footnote", "label": "more litteral"},
]
prompts["creative"] = [
    "translate the text into english. do not include any explanations, just translate. keep html tags.\n\n ",
    "1.0",
    "3",
    "0.4",
    {"position": "append", "type": "footnote", "label": "more readable"},
]
# prompts['lern'] = [ "go paragraph by paragraph and explain ideoms and slang terms from each paragraph. keep html tags.\n\n ", "1.0", "3", "0.4", {"position":"append","type":"footnote","label":"details"}]

# batching


def translate_block(tup):

    block, block_nr, blocks_total = tup

    global sum_T_in, sum_T_out, total_retries, total_failed

    print(f"start block {block_nr} from {blocks_total}")

    max_attempts = 5
    collect = {"original": block}

    paragraphs_org = len(my_text.split_paragraphs(block))

    # print(wrap_text(f"\n{blocks[i]}\n\n"))
    for pKey, pValue in prompts.items():
        success = False

        # create translitteration
        for attempt in range(max_attempts):
            try:
                # if (pKey == "translitterate"):
                #     raise AttributeError('no answer')

                prompt = pValue[0] + block
                res2 = send_prompt(prompt, temperature=float(pValue[1]), top_k=int(pValue[2]), top_p=float(pValue[3]))

                count = len(my_text.split_paragraphs(res2.text))
                if paragraphs_org != count:
                    e = f"    Block {block_nr} {pKey}: paragraph missmatch {attempt+1}x"
                    print(e)
                    save_error(e + "\n\n" + res2.text + "\n\n")
                    total_retries += 1
                    continue

                T_in = my_text.token_count(prompt)
                T_out = my_text.token_count(res2.text)
                sum_T_in += T_in
                sum_T_out += T_out
                # print(wrap_text(f"{res2.text}^[tokens prompt:{T_in}, tokens response:{T_out}]\n\n---\n\n"))
                collect[pKey] = res2.text

                success = True
                T_trlate = my_text.token_count(res2.text)
                print(f"   Block {block_nr} {pKey}: {res2.text[15:30]}..  token: {T_trlate}")
                break
            except Exception as e:
                # print(f"An error occurred: {e}")
                print(f"    Block {block_nr} {pKey}: no Answer {attempt+1}x")
                total_retries += 1

        if success == False:
            collect[pKey] = ""
            print(f"!! Block {block_nr} {pKey}: translation failed")
            total_failed += 1

    return block_nr, collect


if end_block > len(blocks):
    end_block = len(blocks)


def translate_blocks(blocks, start=0, end=10000):

    # initialze the result list
    oBlocks = ["" for i in range(0, end - start)]

    workload = [(blocks[i], i, len(oBlocks)) for i in range(start, end)]  # 12 prompts

    # Use ProcessPoolExecutor to run tasks in separate processes
    with concurrent.futures.ProcessPoolExecutor(max_workers=3) as executor:
        # Map the function and arguments to the executor
        # The executor will return results as they are completed
        results = list(executor.map(translate_block, workload))

    for r in results:
        oBlocks[r[0]] = r[1]

    return oBlocks


oBlocks = translate_blocks(blocks, start_block, end_block)

book = []


# merg everything together
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

        for pKey, pValue in prompts.items():

            meta = pValue[4]

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
execution_time = end_time - start_time

# Convert the execution time to hh:mm:ss format
h = int(execution_time // 3600)
m = int((execution_time % 3600) // 60)
s = int(execution_time % 60)

seconds_per_prompt = round(execution_time / total_ai_requests, 3)

prompts_stats = ""
for key, values in prompts.items():
    prompts_stats = (
        prompts_stats
        + f"""
-----

**{key} prompt (temperature: {values[1]} | top_k: {values[2]} | top_p: {values[3]}):**  \\
"{values[0]}"
    """
    )

stats = f"""

# statistics

**Ai Model** {model.model_name}

{prompts_stats}

----

sum blocks processed: {len(oBlocks)}  
sum tokens prompt: {sum_T_in}  \\
sum tokens response (only translation): {sum_T_out}  \\

----

total ecexution time: {h}:{m}:{s}  \\
total prompts send to AI: {total_ai_requests}  \\
total failed prompts (retries): {total_retries}  \\
total failed prompts (given up on): {total_failed}  \\
average seconds per prompt: {seconds_per_prompt}  \\


"""
print(wrap_text(stats))
save(stats)
file_out.close()
file_error_out.close()


run_command(
    "pandoc  -f markdown+inline_notes -t epub --css='epub.css' --metadata title='gemini translation test' -o {project_name}/{project_name}.epub {project_name}/translated.txt"
)
