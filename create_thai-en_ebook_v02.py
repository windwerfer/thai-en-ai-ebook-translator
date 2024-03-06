# termux:
#   pkg install python-grpcio python-pillow   (in termux if venv, needs to passthrough those packages!!)
#   pip install google.generativeai
#   pip install pythainlp tzdata pprint regex chardet

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import re
import sys
import textwrap
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
import pickle
import subprocess  # to run a command in the terminal: run_command()

from lib import my_text
from lib import my_transliteration_paiboon
from lib import my_grab_urls

import time


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
    stats['failed_paragraphs'] = []

    conf = {}
    conf['project_name'] = 'prj_lp_choob_01'

    conf['start_block'] = 31  # start at 0
    conf['end_block'] = 60  # put in 9999 for the end of the book
    conf['max_attempts'] = 15  # maximum retries to send to an AI before giving up
    conf['max_workers'] = 20
    conf['pause_between_retries'] = 5
    conf['max_tokens_per_query'] = 1500

    conf['debug'] = True  # debugger_is_active()    # i couldn't get the debug check to work.. do manually
    conf['debug'] = False  # debugger_is_active()    # i couldn't get the debug check to work.. do manually
    if conf['debug']:
        conf['max_workers'] = 1

    files = {}
    files['out'] = open(conf['project_name'] + '/translated.txt', 'w', encoding='utf-8')
    files['error_out'] = open(conf['project_name'] + '/errors.txt', 'w', encoding='utf-8')
    files['blocks'] = open(conf['project_name'] + '/blocks.txt', 'w', encoding='utf-8')

    try:
        os.makedirs(conf['project_name'], exist_ok=True)
        print(f'Project directory "{conf['project_name']}" successfully opened')
    except OSError as error:
        print(f'Project directory could not be created: "{conf['project_name']}" ')

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

    conf['safety'] = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    }

    conf['prompts'] = {}

    # engine: 'transliterate__pythainpl_dict_paiboon'  ->   uses the pythainpl lib to transliterate
    conf['prompts']['transliterate'] = {
        # 'prompt': 'transliterate the thai text with the ISO 11940 system. do not include any explanations. keep html tags.\n\nText: ',
        'prompt': 'Transliteration is now done through the pythainpl library, together with a dictionary thai(script)->transliteration(paiboon). (not through gemini or chatgpt)',
        # 'temperature': '0.6', 'top_k': '2', 'top_p': '0.4',
        'engine': 'transliterate__pythainpl_dict_paiboon', 'position': 'prepend', 'type': 'footnote',
    }

    conf['prompts']['gemini_default_2024.03'] = {
        'prompt': 'translate the text into english. do not include any explanations, just translate. keep html tags and characters that are in roman/latin  unchanged.\n\n ',
        'temperature': '0.6', 'top_k': '2', 'top_p': '0.4', 'engine': 'gemini', 'position': 'append',
        'type': 'paragraph',
        'max_tokens_per_query': 1400,
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text

    }

    conf['prompts']['gemini_literal_2024.03'] = {
        'prompt': 'translate the text into english. do not include any explanations, just translate. keep html tags and characters that are in roman/latin  unchanged.\n\n ',
        'temperature': '0.2', 'top_k': '1', 'top_p': '0.4',
        'engine': 'gemini', 'position': 'append', 'type': 'footnote', 'label': 'more literal',
        'max_tokens_per_query': 1400,
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    conf['prompts']['gemini_creative_2024.03'] = {
        'prompt': 'translate the text into english. do not include any explanations, just translate. keep html tags and characters that are in roman/latin  unchanged.\n\n ',
        'temperature': '1.0', 'top_k': '3', 'top_p': '0.4',
        'engine': 'gemini', 'position': 'append', 'type': 'footnote', 'label': 'more readable',
        'max_tokens_per_query': 1400,
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }


def run_command(command):
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
    return result


def is_debugger_enabled():
    return 'PYDEVD_LOAD_VALUES_ASYNC' in os.environ


def wrap_text(text):
    """for Termnial output: Wraps text to the specified width, breaking lines at word boundaries."""
    t_columns, t_lines = shutil.get_terminal_size()
    paragraphs = []
    wrapped_text = ''
    paragraphs = text.splitlines()  # Split into paragraphs by existing newlines
    wrapped_text = '\n'.join(
        # Wrap each paragraph
        textwrap.fill(p, width=t_columns - 1)
        for p in paragraphs
    )
    return wrapped_text


def pickle_paragraphs(project_dir):
    global paragraphs
    file = '{project_dir}/saved_paragraphs.pickle'
    with open(file, 'wb') as f:
        pickle.dump(paragraphs, f)

def pickle_paragraphs_exists(project_dir):
    file = '{project_dir}/saved_paragraphs.pickle'
    return os.path.exists(file)

def unpickle_paragraphs(project_dir):
    global paragraphs
    file = '{project_dir}/saved_paragraphs.pickle'
    with open(file, 'rb') as f:
        return pickle.load(f)


def query_gemini(prompt, temperature=0.5, top_p=0.3, top_k=1, safety=None):
    """ sends a prompt to gemini and returns the result """

    if safety is None:
        safety = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        }

    GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']  # to fetch an environment variable.
    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel('gemini-pro')
    generation = genai.types.GenerationConfig(
        candidate_count=1,      # Only one candidate for now.
        # stop_sequences=['x'],
        # max_output_tokens=20,
        ## https://medium.com/@daniel.puenteviejo/the-science-of-control-how-temperature-top-p-and-top-k-shape-large-language-models-853cb0480dae
        temperature=temperature,  # 0.0=strickt, 1.0=creative/random
        top_k=top_k,  # int default: 1
        top_p=top_p,  # Set top_p, default: 1.0
    )

    response = model.generate_content(prompt, safety_settings=safety, generation_config=generation)
    return response


def format_stats(stats, conf):
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

    return stats_text


def generate_pandoc_cmd(file):
    pandoc_home = r"C:\Users\watdo\AppData\Local\Pandoc"
    script_folder = r"C:\Users\watdo\python\thai-en-ai-ebook-translator"
    cmd = f"{pandoc_home}\\pandoc.exe -f markdown+inline_notes -t epub --css='{script_folder}\\lib\\epub.css' " + \
          f"--metadata title='gemini translation test' -o '{script_folder}\\{conf['project_name']}\\{conf['project_name']}.epub' " + \
          f"'{script_folder}\\{conf['project_name']}\\translated.txt'"
    print(cmd)


def load_paragraphs(filename, delimiter='\n\n'):
    """
    Loads a text file, splits the content by a specified delimiter,
    and returns the result as an array of paragraphs.

    Args:
        filename (str): The name of the text file to load.
        delimiter (str, optional): The character to use for splitting the text.
                                   Defaults to '\n\n' (double newline).

    Returns:
        list: An array of dictionaries  { 'original': { 'text':  <paragraph> } }
    """

    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()
        # blocks = content.split(delimiter)
        # blocks = re.split(delimiter, content, flags=re.MULTILINE)

        # remove whitespaces, if line is empty
        content = re.sub(r'^[ \t]+$', '', content)

        # reduce all paragraph spacing to only one empty line in between - gemini will get confused otherwise with the paragraph count
        content = re.sub(r'(\n)+\n\n', '\n\n', content)

        # convert tab to spaces
        content = re.sub(r'\t', '  ', content)

        # remove leading and trailing blank lines
        content = re.sub(r'^\s+|\s+$', '', content)

        spl = my_text.split_paragraphs(content)

        paragraphs = []

        for s in spl:
            # remove spaces at the beginning of a paragraph
            s = re.sub(r'^[ ]+', '', s, flags=re.MULTILINE)

            # TODO: remove later. only for the LP Fak bio
            s = re.sub(r'˶', '“', s, flags=re.MULTILINE)
            s = re.sub(r'˝', '”', s, flags=re.MULTILINE)

            paragraphs.append({'original': {'text': s}})

    return paragraphs


def create_queries(paragraphs, prompts, prompts_to_process):
    for prompt_name, l in prompts_to_process.items():
        if prompt_name in prompts:
            print(f'prompt {prompt_name} will be processed')
            max_tokens = prompts[prompt_name]['max_tokens_per_query']
            groups = my_text.group_paragraphs_by_tokens(paragraphs, max_tokens, prompt_name,
                                                        process_only_unfinished=True)
            prompts_to_process[prompt_name] = groups
        else:
            print(f'prompt id: {prompt_name} not found')
    return prompts_to_process


def run_queries(prompt_list, paragraphs):
    """  takes the paragraph list indexes from prompt_list and creates textblocks
            those textblocks will be sent to an AI (gemini only at the moment)
            after they arrive back, they will be transfered into the paragraphs variable
     """


    return paragraphs


def main():
    global conf, stats, paragraphs

    if (pickle_paragraphs_exists(conf['project_name'])):
        paragraphs = unpickle_paragraphs(conf['project_name'])
    else:
        my_grab_urls.prepare_input(conf['project_name'])

        filename = conf['project_name'] + "/input.txt"

        paragraphs = load_paragraphs(filename)

    prompts_to_process = {'gemini_default_2024.03': [], 'gemini_literal_2024.03': [], 'gemini_creative_2024.03': []}

    # returns a list of queries: [{paragraphs: list_of_paragraph_ids, model: AI model to query,
    #                               prompt: prompt_text+some_paragraphs,
    #                               temperature: float, top_k=int, top_p=float}
    prompt_list = create_queries(paragraphs, conf['prompts'], prompts_to_process)

    paragraphs = run_queries(paragraphs, prompt_list)


if __name__ == '__main__':
    init_config()
    main()
