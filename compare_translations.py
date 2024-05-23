# termux:
#   pkg install python-grpcio python-pillow   (in termux if venv, needs to passthrough those packages!!)
#   pip install google.generativeai
#   pip install pythainlp tzdata pprint regex chardet

# configs: -p "prj_dtudong_01_th" -i "prj_dtudong_01_th/input_dtudong_thai_v0.2.txt"
# configs: -p "prj_dtudong_01_en" -i "prj_dtudong_01_en/input_dtudong_en.txt"
# configs: -p "prj_lp_choob_04" -i "prj_lp_choob_04/input_lp_choob.txt"

import argparse
import csv
import json
import os
import pickle
import pprint
import random
import re
import shutil
import subprocess
# import subprocess  # to run a command in the terminal: run_command()
import sys
import textwrap
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from lib import my_text
from lib import my_prompts_th_api
from lib import my_prompts_ch_api
from threading import Semaphore, Timer


# from lib import my_transliteration_paiboon


def init_config():
    global conf, stats, files

    conf = {}
    conf['prompts'] = {}

# --------------------------- user config starts here---------------------------------------
        #limits https://ai.google.dev/pricing
        #   gemini 1.0 pro:  15 RPM (requests per minute), 32,000 TPM (tokens per minute), 1,500 RPD (requests per day)
        #   gemini 1.5 pro: 2 RequestsPM, 32,000 TokensPM, 50 RPDay
        #   gemini 1.5 flash: 15 RPM, 1 million TPM (tokens per minute), 1,500 RPD (requests per day)


    # groups of paragraphs are sent bundled into one prompt (maybe better translation through context)
    conf['max_tokens_per_query__gemini'] = 1200  # 1800 token ok for most groups, but some need the limit lower. 1000tk is a good alternative
    conf['max_tokens_per_query__gemini1.5'] = 2000  # 1800 token ok for most groups, but some need the limit lower. 1000tk is a good alternative
    conf['max_groups_to_process'] = 250  # for testing: only do a view querys before finishing
    conf['tasks_per_minute'] = 10  # nr of queries run at the same time (multiprocess)
    conf['max_workers'] = 10  # nr of queries run at the same time (multiprocess)


    # 'gemini_default_2024.03', 'gemini_literal_2024.03',
    conf['prompts_to_process'] = [  'transliterate',
                                    'gemini_1.0_2024.03.23', 'gemini_1.0_k.rob_2024.03.23',
                                    'gemini_1.5_nor_2024.05.08',
                                    'gemini_15flash_nor_01'
                                  ]

    # 'gemini_default_2024.03', 'gemini_literal_2024.03',
    conf['prompts_to_display'] = ['original', 'transliterate', '', 'gemini_1.5_nor_2024.05.08', 'claude_18.05.2014', 'chatGPT_18.05.2014', 'chatGPTo_18.05.2014','gemini_15flash_nor_01',
                                  'gemini_1.0_2024.03.23', 'gemini_1.0_k.rob_2024.03.23']

# --------------------end config ----------------------------------------------------------------------------------------


    # ------  prj_tudong ----------- (chinese project)
    #conf['prompts_to_display'] = ['original',  'D_pali_str_gemini1.0', 'claude_pali', 'chatGPT_pali','chatGPTo_pali', 'B_pali_nor_gemini1.5',]
    #conf['prompts_to_display'] = ['original',  'C_nor_gemini1.0', 'claude', 'chatGPT','chatGPTo','A_cre_gemini_1.5', ]
    # conf['prompts_to_process'] = [  'A_cre_gemini_1.5',  'B_pali_nor_gemini1.5',
    #                                 #'C_nor_gemini1.0', 'D_pali_str_gemini1.0',
    #                               ]




    conf['encode_as'] = 'json'
    # load prompts
    conf['prompts'] = my_prompts_th_api.load_prompts(conf)











    conf['pali_terms_list_mine'] = load_word_substitution_list('lib/pali_terms_mine.txt', sep='\t')
    conf['pali_terms_list_pts'] = load_word_substitution_list('lib/pali_terms_pts.txt', sep='\t')
    conf['word_substitution_list'] = load_word_substitution_list('lib/word_substitution_list.data')
    conf['word_translation_annotation_list'] = load_word_translation_annotation_list(
        'lib/word_translation_annotation_list.data')

    ##########
    # ----------------------------- normal config ends here --------------------------------
    ##########

    # --- process args

    # Create the parser
    parser = argparse.ArgumentParser(description="This script does something with a name and an input file.")

    # Add the '-p' argument for some name, required
    h = ('Specify a Project_Name. The script automatically continues where you last left of (after successul script '
         'execution).')
    parser.add_argument('-p', type=str, required=True, help=h)

    # Add the '-i' argument for the input file, required
    h = ('Specify the input file path. Accepted are Text files with a blank line as paragraph divider. Once the file '
         'is processed, the paragraphs will be stored in [project_folder]/saved_paragraphs.pickle and -i option '
         'neeeds to be specified any more.')
    parser.add_argument('-i', type=str, help=h)

    # Parse the arguments
    args = parser.parse_args()

    # --- process args end

    conf['project_name'] = args.p
    conf['input_file'] = args.i
    conf['path_answers_api'] = 'answers_api'

    try:
        os.makedirs(conf['project_name'], exist_ok=True)
        print(f"Project directory '{conf['project_name']}' successfully opened")
    except OSError as error:
        print(f"Project directory could not be created: '{conf['project_name']}'")

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

    # run only one process if debugging, otherwise the other elements in the queue will finish before debugin is stoped -> error
    if is_debugger_enabled():
        print('debuger enbled -> set max_workers to 1')
        conf['max_workers'] = 1

    stats = {}
    stats['start_time'] = time.time()
    stats['total_requests'] = 0
    stats['total_success'] = 0
    stats['total_failed'] = 0
    stats['total_blocked'] = 0
    stats['total_paragraph_missmatch'] = 0
    stats['total_retries'] = 0
    stats['total_tokens_send'] = 0
    stats['total_tokens_received'] = 0
    stats['failed_paragraphs'] = []


def load_word_substitution_list(file_name='lib/word_substitution_list.data', sep=','):
    with open(file_name, 'r', encoding='utf8') as f:
        lines = f.read().splitlines()
    data = {}
    for t in lines:
        w = t.split(sep, 1)
        if len(w) != 2 or w[0][0:1] == '#':
            continue
        data[w[0]] = w[1]
    return data


def load_word_translation_annotation_list(file_name='lib/word_translation_annotation_list.data'):
    with open(file_name, 'r', encoding='utf8') as f:
        lines = f.read().splitlines()
    data = {}
    for t in lines:
        w = t.split(',', 1)
        data[w[0]] = f"'{w[0]}': {w[1]}"
    return data


def replace_with_word_substitution_list(text, wrap='', add_original=False):
    dic = conf['word_substitution_list']

    for pattern, repl in dic.items():
        if add_original:
            add = f'{pattern}: '
        else:
            add = ''
        if wrap == '{}':
            repl = '{' + add + repl + '}'
        if wrap == '[]':
            repl = '[' + add + repl + ']'
        if wrap == 'exp':
            r = repl.split('|')
            repl = '" or "'.join(r)
            repl = '{' + 'the next occurrence of "' + pattern + '" needs to be translated as  "' + repl + '"}'
        text = re.sub(pattern, repl, text)
    return text


def run_command(command):
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
    return result


def is_debugger_enabled():
    """ checks if pycharm started this script through debugger or run mode (sets the env variable) """
    return 'PYDEVD_LOAD_VALUES_ASYNC' in os.environ


def pp(arr):
    pprint.pprint(arr)


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


def pickle_paragraphs(project_dir, paragraphs_direct=[]):
    global paragraphs
    if len(paragraphs_direct) > 0:
        paragraphs = paragraphs_direct
    file = f'{project_dir}/saved_paragraphs.pickle'
    with open(file, 'wb') as f:
        pickle.dump(paragraphs, f)


def pickle_paragraphs_exists(project_dir: str = 'test') -> str:
    file = f'{project_dir}/saved_paragraphs.pickle'
    return os.path.exists(file)


def unpickle_paragraphs(project_dir: str) -> dict:
    global paragraphs
    file = f'{project_dir}/saved_paragraphs.pickle'
    with open(file, 'rb') as f:
        return pickle.load(f)


def query_gemini(prompt_text: str, temperature: float = 0.5, top_p: float = 0.3, top_k: int = 1,
                 model_name: str = 'models/gemini-1.0-pro',
                 safety: dict = None) -> object:
    """ sends a prompt to gemini and returns the result """

    finish_reason = (-1, 'still running')
    safety_rating = []
    text = ''
    success = False
    safety_block = True

    block_setting = HarmBlockThreshold.BLOCK_LOW_AND_ABOVE  # blocks all querys (for testing)
    block_setting = HarmBlockThreshold.BLOCK_NONE  # blocks only when HarmBlockThreshold is HIGH ( = 4)

    safety = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: block_setting,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: block_setting,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: block_setting,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: block_setting,
    }

    # saved in C:/Users/watdo/python/pycharm_default_enviroment_var.env
    GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']  # to fetch an environment variable.
    #print(f'    api key: {GOOGLE_API_KEY}')
    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel(model_name)
    generation = genai.types.GenerationConfig(
        candidate_count=1,  # Only one candidate for now.
        # stop_sequences=['list of max 5 str', 'when encountering this, output will be stoped', 'i am just a simple IA model'],
        # max_output_tokens=20,         # stop if output exceeds max_tokens
        ## https://medium.com/@daniel.puenteviejo/the-science-of-control-how-temperature-top-p-and-top-k-shape-large-language-models-853cb0480dae
        temperature=temperature,  # 0.0=strickt, 1.0=creative/random     default: 0.9  (models/gemini-1.0-pro    )
        top_k=top_k,  # int     default: 1      (models/gemini-1.0-pro    )
        top_p=top_p,  # float   default: 1.0    (models/gemini-1.0-pro    )
    )
    try:
        response = model.generate_content(prompt_text, safety_settings=safety, generation_config=generation)

        safety_flat = ''
        # create my own safety ratings variable
        for s in response.prompt_feedback.safety_ratings:
            sa_str = f'{s.category.name[14:]:<30} = {s.category.value:<6} ---  {s.probability.name:<20} = ' + \
                     f'{s.probability.value}    blocked: {s.blocked}'
            safety_flat += f'{s.category.name[14:].lower():<18} = {s.probability.name.lower():<10} | '
            # print(sa_str)
            safety_rating.append(
                (s.category.name[14:].lower(), s.probability.name.lower(), s.category.value, s.probability.value))

        # finis_reason: 0 = FINISH_REASON_UNSPECIFIED (not used), 1 = Stop (query completet without errors, natural stop),
        # 2 = MAX_TOKENS (too long a answer, truncated),
        # 3 = SAFETY (not possible, SAFETY throws an error because candidates is []), check
        #     through response.prompt_feedback.block_reason.value instead
        if response.prompt_feedback.block_reason.value == 1:
            safety_block = True
            finis_reason = (3, safety_flat)
        else:
            safety_block = False
            finish_reason = (response.candidates[0].finish_reason.value, response.candidates[0].finish_reason.name)

        text = response.text

        if finish_reason[0] == 1 and safety_block is False:
            success = True

    # thrown when SAFETY was triggered
    except ValueError:
        s = 'Blocked. SAFETY rating too low. '
        safety_block = True
        finish_reason = (3, safety_flat)
    # thrown when something completely unexpected happen
    except Exception as e:
        s = 'unusual error: ' + str(e)
        finish_reason = (-2, s)

    # time.sleep(1)
    ret = [text, success, finish_reason, safety_block, safety_rating]
    ret = {'text': text, 'success': success, 'finish_reason': finish_reason, 'safety_block': safety_block,
           'safety_rating': safety_rating}

    # Generate a random float number between 1 and 3
    pause_time = random.uniform(1, 3)

    # Pause execution for the generated duration
    time.sleep(pause_time)

    return ret


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
    for key, c in conf['prompts'].items():
        if key == 'transliterate':
            continue
        prompts_stats = (
                prompts_stats
                + f"""
    -----

    **{key} prompt (temperature: {c['temperature']} | top_k: {c['top_k']} | top_p: {c['top_p']}):**  \\
    "{c['prompt']}"
        """
        )

    stats_text1 = f"""

    -----

    **Ai Model / Prompts** 

    {prompts_stats}

    """
    stats_text2 = f"""
    
     # statistics
    
    sum tokens prompt: {stats['total_tokens_send']}  \\
    sum tokens response (only translation): {stats['total_tokens_received']}  \\
    (only counting successful question-answer pairs)
    
    ----

    total execution time: {h}:{m}:{s}  \\
    total prompts send to AI: {stats['total_requests']}  \\
    total successful prompts: {stats['total_success']}  \\
    total blocked prompts (harassment etc): {stats['total_blocked']}  \\
    total paragraph mismatches: {stats['total_paragraph_missmatch']}  \\
    total failed prompts (retries): {stats['total_retries']}  \\
    total failed prompts (misc errors eg quota / timeout): {stats['total_failed']}  \\
    average seconds per prompt: {seconds_per_prompt}  \\

    """

    return (stats_text1, stats_text2)


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

        spl = my_text.split_paragraphs(content, encoded_as='double_newline', trim=True)

        paragraphs = []

        for i, s in spl.items():
            # remove spaces at the beginning of a paragraph
            s = re.sub(r'^[ ]+', '', s, flags=re.MULTILINE)

            # TODO: remove later. only for the LP Fak bio
            s = re.sub(r'˶', '“', s, flags=re.MULTILINE)
            s = re.sub(r'˝', '”', s, flags=re.MULTILINE)
            s = re.sub(r'\n', ' ', s, flags=re.MULTILINE)

            paragraphs.append({'original': {'text': s}})

    return paragraphs


def create_paragraph_groups(paragraphs, prompts, prompt_names_to_process):
    prompts_to_process = {}
    for name in prompt_names_to_process:
        if name == 'transliterate':
            continue
        prompts_to_process[name] = []

    for prompt_name, l in prompts_to_process.items():
        if prompt_name in prompts:
            print(f'prompt {prompt_name} will be processed')
            max_tokens = prompts[prompt_name]['max_tokens_per_query']
            groups = my_text.group_paragraphs_by_tokens(paragraphs, max_tokens, prompt_name, process_only_unfinished=True)
            prompts_to_process[prompt_name] = groups
        else:
            print(f'prompt id: {prompt_name} not found')
    return prompts_to_process


def group_query_ai(args, send_with_paragraph_tag=True):
    """     encoded_as:
                double_newline      eg. text1\n\ntext2
                newline             eg. text1\ntext2
                list                eg. 1. text1\n\n2. text2
                json                eg {"1":"text1", "2":"text2"}
                xml                 eg <item id="1">text1</item>\n<item id="2">text2</item>
                p                   eg <p id='1'>text1</p>\n<p id='2'>text2</p>

    """
    paragraphs_slice, paragraph_ids_group, prompt_name, prompt, conf, query_arg_id = args

    encode_as = conf['encode_as']

    m = f'   paragraph group {paragraph_ids_group[0]:>4}:{paragraph_ids_group[-1]:>4} - ' + \
        f'query nr {query_arg_id + 1:>4}: start'
    print(m)

    text_group = ''
    if encode_as != 'json':
        for paragraph_id in paragraphs_slice:
            if encode_as == 'list':
                text_group = text_group + f'\n\n{paragraph_id}. {paragraphs_slice[paragraph_id]}'
            elif encode_as == 'xml':
                text_group = text_group + f'<item id="{paragraph_id}">{paragraphs_slice[paragraph_id]}</item>\n'
            elif encode_as == 'p':
                text_group = text_group + f"<p id='{paragraph_id}'>{paragraphs_slice[paragraph_id]}</p>\n"
            elif encode_as == 'newline':
                text_group = text_group + f'\n{paragraphs_slice[paragraph_id]}'
            elif encode_as == 'double_newline':
                text_group = text_group + f'\n\n{paragraphs_slice[paragraph_id]}'
    if encode_as == 'json':
        text_group = json.dumps(paragraphs_slice, sort_keys=True, indent=4, ensure_ascii=False)

    # remove the 2 empty newlines at the beginning
    if not send_with_paragraph_tag:
        text_group = text_group[2:]

    # ask google
    if prompt['engine'] == 'gemini':
        try:
            p1 = prompt['prompt'] + "\n\n" + text_group
            ret = query_gemini(p1, temperature=float(prompt['temperature']),
                               top_k=int(prompt['top_k']),
                               top_p=float(prompt['top_p']), model_name=prompt['model'])

            # r = "\n\n".split(ret)

            add_file_info = ''
            ret['finish_reason_short'] = ''

            ret['paragraphs'] = my_text.split_paragraphs(ret['text'], encoded_as=conf['encode_as'])
            if 'paragraphs' not in ret or len(ret['paragraphs']) == 0:
                ret['success'] = False
                ret['finish_reason'] = 'paragraph xml tag missing in return or not formated corectly'
                add_file_info += '_fail_missmatch'
                ret['fail_reason'] = 'paragraphs_not_equal'
            else:
                # check if sent paragarph id matches received paragraph id eg. sent: 301,302.. received: 301:'text', 302:'more'
                errors = 0
                for i, p in enumerate(ret['paragraphs']):
                    if paragraph_ids_group[i] != int(p):
                        errors += 1
                if errors > 0:
                    ret['success'] = False
                    ret['finish_reason'] = 'paragraphs not matching input, eg sent: 301,302.. received: 300:"text", 302:"more"'
                    add_file_info += '_fail_missmatch_detail_1'
                    ret['fail_reason'] = 'paragraph_numbers_off'
            if ret['safety_block'] == True:
                ret['success'] = False
                ret['finish_reason'] = 'safetyblock'
                add_file_info += '_fail_safety'
                ret['fail_reason'] = 'safety'
            ret['paragraph_ids_group'] = paragraph_ids_group
            ret['query_arg_id'] = query_arg_id
            ret['prompt_name'] = prompt_name
            ret['prompt_text'] = prompt['prompt']
            ret['text_send'] = p1

            # because the sub-processes can not talk directly to the main-process, the workers will save the return values as a file
            #  and the main thread will on start an finish parse all files and save them in the global paragraphs object
            filename = f'{prompt_name}__p{paragraph_ids_group[0]:>4}-{paragraph_ids_group[-1]:>4}-{query_arg_id:>3}{add_file_info}.json'
            path = f"{conf['project_name']}/{conf['path_answers_api']}/"
            save_query_result_to_file(filename, path, ret)

            m = f"   [{ret['prompt_name']}] group {ret['paragraph_ids_group'][0]:>4}:{ret['paragraph_ids_group'][-1]:>4} - query nr {ret['query_arg_id'] + 1:>3}: "
            if ret['success'] == True:
                print(m + ' returned successfull')
            else:
                print(m + ' failed')

        # t = f'{prompt_name} + {paragraphs_slice[0]}'
        except Exception as e:
            print(e)
        # safety ratings..
    # https://ai.google.dev/docs/safety_setting_gemini

    return ret


def import_ai_answers_to_paragraphs(directory_path, print_details = False, print_errors = False):
    global conf, paragraphs, err

    # List to hold the contents of each file
    file_contents = []

    try:
        # Loop through each file in the directory
        for filename in os.listdir(directory_path):
            # Construct full file path
            file_path = os.path.join(directory_path, filename)
            # Open and read the file
            with open(file_path, 'r', encoding='utf8') as file:
                try:
                    # Parse the JSON data
                    data = json.load(file)
                    # Append the data to the list
                    file_contents.append(data)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from file {filename}")
    except Exception as e:
        print('answers_api not yet created')
        return

    # Optionally, print the contents of file_contents to verify
    #print(file_contents)

    for cont in file_contents:
        if cont['success'] == True:
            for paragraph_id, par in cont['paragraphs'].items():
                # if this paragraph is new
                id = int(paragraph_id)
                try:
                    # if the paragraph was already successfully inserted -> ignore

                    if paragraphs[id][cont['prompt_name']]['success'] == True:
                        continue
                except KeyError:
                    # if its the first time the paragraph was processed -> create the dict
                    paragraphs[id][cont['prompt_name']] = {}
                    paragraphs[id][cont['prompt_name']]['retries'] = 0

                try:
                    # add the query result into paragraphs
                    paragraphs[id][cont['prompt_name']]['text'] = cont['paragraphs'][str(id)]
                    paragraphs[id][cont['prompt_name']]['retries'] += 1

                    paragraphs[id][cont['prompt_name']]['success'] = cont['success']
                    paragraphs[id][cont['prompt_name']]['finish_reason'] = cont['finish_reason']
                    paragraphs[id][cont['prompt_name']]['safety_block'] = cont['safety_block']
                    paragraphs[id][cont['prompt_name']]['safety_rating'] = cont['safety_rating']
                    paragraphs[id][cont['prompt_name']]['processed_in_paragraph_group'] = cont['paragraph_ids_group']
                    paragraphs[id][cont['prompt_name']]['prompt'] = [cont['prompt_name'], cont['prompt_text']]

                except Exception as e:
                    if print_errors: print('error: couldnt update paragraphs correctly, but succeeded in entered  the query')

            m = f"   [{cont['prompt_name']}] group {cont['paragraph_ids_group'][0]:>4}:{cont['paragraph_ids_group'][-1]:>4} - query nr {cont['query_arg_id'] + 1:>4}: added successfully"
            if print_details: print(m)

        # if the query wasnt a success, generate error messages and statistics
        else:
            try:
                if cont['fail_reason'] == 'safety':
                    stats['total_blocked'] += 1
                else:
                    stats['total_failed'] += 1
                m = f" [{cont['prompt_name']}] group {cont['paragraph_ids_group'][0]:>4}:{cont['paragraph_ids_group'][-1]:>4}" + \
                    f" - query nr {cont['query_arg_id'] + 1:>4}: failed (finish reason {cont['finish_reason']})"
                if print_details: print(m)

            except Exception as e:
                if print_errors: print(f"error: could not add to {stats['total_failed']}")

            try:
                if cont['fail_reason'] == 'paragraphs_not_equal' or cont['fail_reason'] == 'paragraph_numbers_off':
                    stats['total_paragraph_missmatch'] += 1
                    err_msg = f" [{cont['prompt_name']}] group {cont['paragraph_ids_group'][0]:>4}:{cont['paragraph_ids_group'][-1]:>4} - query nr {cont['query_arg_id'] + 1:>4}: -- mismatched paragraphs (log to error.cvs)"
                    # for paragraphs_slice in query_args[query_arg_id][0]:
                    #     org_text += '\n\n' + paragraphs_slice['original']['text']
                    err.append([cont['text_send'], cont['text'], err_msg])
                if print_details: print(err_msg)
            except Exception as e:
                if print_errors: print('error: could not process paragraph mismatch')


def make_dir_if_not_exists(directory_path):
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            print(f"Directory '{directory_path}' was created.")
    except Exception as e:
        print(f'couldnt create {directory_path}.')


def save_query_result_to_file(filename, path, data):
    # Write JSON data to a file
    make_dir_if_not_exists(path)
    with open(path + filename, 'w', encoding='utf8') as file:
        json.dump(data, file, sort_keys=False, indent=4, ensure_ascii=False)  # Use indent for pretty-printing

    #print(f"Data has been written to {filename}")


def run_queries(paragraph_groups, paragraphs, prompts):
    """  takes the paragraph list indexes from prompt_list and creates textblocks
            those textblocks will be sent to an AI (gemini only at the moment)
            after they arrive back, they will be transfered into the paragraphs variable
     """

    global stats, conf

    interval = 60 / conf['tasks_per_minute']  # Calculate the interval between task submissions

    # # Add this at the beginning of your run_queries function
    # semaphore = Semaphore(conf['max_requests_per_min'])  # Initialize the semaphore with your rate limit
    # Timer(0, reset_semaphore,
    #       args=(semaphore, conf['max_requests_per_min'])).start()  # Start the timer to reset semaphore every minute

    query_args = []
    err = []  # format: [origin_text: , answer_text: , error_message]
    group_entry_count = 0

    # run as multiple processes
    for prompt_name, group in paragraph_groups.items():
        for paragraph_ids_group in group:
            # assuming that each group is continuous (required when creating) the slice is done by using the first
            #  and last item of the group
            paragraphs_slice = {}
            for i in range(paragraph_ids_group[0], paragraph_ids_group[-1] + 1):
                if conf['prompts'][prompt_name]['use_word_substitution_list']:
                    paragraphs_slice[str(i)] = replace_with_word_substitution_list(paragraphs[i]['original']['text'],
                                                                                   wrap='{}')
                else:
                    paragraphs_slice[str(i)] = paragraphs[i]['original']['text']

            # prepare the querys: a list of paragraphs to be send to the AI_query, the id of them in the original
            #  paragraphs list and the prompt that will be processed
            query_args.append([paragraphs_slice, paragraph_ids_group, prompt_name, prompts[prompt_name], conf])
            group_entry_count += 1

            # development: limit groups to process..
            if group_entry_count >= conf['max_groups_to_process']:
                break
        if group_entry_count >= conf['max_groups_to_process']:
            break

    # Create a ProcessPoolExecutor with a maximum of 3 processes
    with ProcessPoolExecutor(max_workers=conf['max_workers']) as executor:
        # Submit the tasks to the executor
        #future_to_prompt = {executor.submit(group_query_ai, query_arg + [query_arg_id]): query_arg_id
        #                    for query_arg_id, query_arg in enumerate(query_args)}

        task_timer_id = 0
        task_id = 0
        start_time = time.time()
        futures = []
        # Continue to submit tasks for one cycle of tasks_per_minute
        for _ in range(len(query_args)):
            if task_timer_id >= conf['tasks_per_minute']:
                # Check if a minute has passed
                if time.time() - start_time < 60:
                    continue
                else:
                    # Reset for the next minute
                    task_timer_id = 0
                    start_time = time.time()
            # if task_id + 1 >= len(query_args):
            #     break

            # Submit a new task
            future = executor.submit(group_query_ai, query_args[task_id] + [task_id])
            futures.append(future)
            #print(f"Submitted task {task_id}")
            task_id += 1
            task_timer_id += 1

            # Wait for the interval before submitting the next task
            time.sleep(interval)

    if len(err) > 0:
        save_matrix_to_cvs(f'{conf["project_name"]}/error.csv', err)

    return paragraphs


def merge_paragraphs(paragraphs, prompts_to_display):
    global conf

    text = ''

    for p in paragraphs:

        if 'original' in prompts_to_display:
            paragraph = p['original']['text']
        else:
            paragraph = ''

        for d in prompts_to_display:

            # check if the prompt_name is found in the global prompts
            if d not in conf['prompts']:
                continue
            meta = conf['prompts'][d]

            # if the paragraph doesnt have the prompt_name -> try next prompt name
            if d not in p:
                continue

            part = p[d]['text']

            # in case something is not ok the translation, go to the next
            if part == "" or part is None:
                continue
            if "label" in meta:
                part = f"{meta['label']}: {part}"
            if meta["type"] == "footnote":
                part = f" ^[{part}] "
            else:
                part = f"\n\n{part} "
            if meta["position"] == "prepend":
                paragraph = part + paragraph
            else:
                paragraph = paragraph + part

            paragraph = paragraph.strip()

        text = text + '\n\n' + paragraph
    return text


def compile_paragraph_statics(paragraphs, prompts):
    stats = {}
    for prompt_name in prompts:
        if prompt_name == 'transliterate':
            continue

        stats[prompt_name] = {
            'unprocessed': 0,
            'success': 0,
            'failed': 0,
            'retries': 0,
            'failed_because_of_safety': 0,
            'failed_because_of_token_max': 0,
            'failed_because_of_unknown': 0,
            'safety_stat': [  # put it in a simple matrix: x-axis: neglegtible-high, y-axis: harrasment-sex content
                [0, 0, 0, 0],  # harrassment
                [0, 0, 0, 0],  # hate speach
                [0, 0, 0, 0],  # sexually explicit
                [0, 0, 0, 0]  # dangerous content
            ],
        }

        for i, p in enumerate(paragraphs):
            if prompt_name not in p:
                stats[prompt_name]['unprocessed'] += 1
                continue
            if 'success' in p[prompt_name] and p[prompt_name]['success']:
                stats[prompt_name]['success'] += 1
            else:
                stats[prompt_name]['failed'] += 1
            if 'retries' in p[prompt_name]:
                stats[prompt_name]['retries'] += p[prompt_name]['retries']
            else:
                stats[prompt_name]['retries'] = 0
            if 'safety_block' in p[prompt_name] and p[prompt_name]['safety_block']:
                stats[prompt_name]['failed_because_of_safety'] += 1
            if 'finish_reason' in p[prompt_name] and p[prompt_name]['finish_reason'][0] == 2:
                stats[prompt_name]['failed_because_of_token_max'] += 1
            if 'finish_reason' in p[prompt_name] and p[prompt_name]['finish_reason'][0] == -2:
                stats[prompt_name]['failed_because_of_unknown'] += 1

            # add on point to the appropriate element
            if 'safety_rating' in p[prompt_name]:
                for s in p[prompt_name]['safety_rating']:
                    category = s[2] - 7
                    rating = s[3] - 1
                    stats[prompt_name]['safety_stat'][category][rating] += 1

    return stats


def safety_matrix_to_text(stats):
    ret = {}
    for prompts_name in stats:

        text = ''
        ma = stats[prompts_name]['safety_stat']
        x = [f'[{prompts_name}]', 'Negligible', 'Low', 'Medium', 'High']
        y = ['Harassment', 'Hate speech', 'Sexually explicit', 'Dangerous']
        text += f'{x[0]:<30} {x[1]:<20} {x[2]:<20} {x[3]:<20} {x[4]:<20}\n'

        for i, j in enumerate(ma):
            text += f'{y[i]:<30} {ma[i][0]:<20} {ma[i][1]:<20} {ma[i][2]:<20} {ma[i][3]:<20}\n'

        ret[prompts_name] = text
    return ret


def create_epub(file_name, project_name, date_str):
    # https://pandoc.org/installing.html            #install pandoc
    # https://miktex.org/download                   #install latex (used by pandoc)
    p = r"C:\Users\watdo\AppData\Local\Pandoc\pandoc.exe "
    p2 = r"C:\Users\watdo\python\thai-en-ai-ebook-translator"
    # c = f"{p} -f markdown+inline_notes -t epub --css='{p2}\\lib\\epub.css' --metadata title='gemini translation test' -o '{p2}\\{project_name}\\{project_name}.epub' '{p2}\\{project_name}\\{file_name}'"
    # print(c)
    # windows needs the absolut path to pandoc
    # run_command(c)
    command = [
        "cmd.exe",
        "/c",
        "C:\\Users\\watdo\\AppData\\Local\\Pandoc\\pandoc.exe",
        "-f", "markdown+inline_notes",
        "-t", "epub",
        f"--css='{p2}\\lib\\epub.css'",
        "--metadata", "title='gemini translation test'",
        "-o", f"'{p2}\\{project_name}\\{project_name}.epub'",
        f"'{p2}\\{project_name}\\{file_name}'"
    ]
    print(" ".join(command[2:]))
    #   should work, but on windows pandoc doesnt seem to like cmd.exe process, with powershell it runs without problems
    # subprocess.run(command, check=True)

    # better use the pypandoc wrapper!!
    # pip install pypandoc     or   pip install pypandoc_binary  (includes the pandoc programm itself, so no need to install it manually with pkg or winsetup)
    import pypandoc

    # Define the input and output file paths
    input_file = f"{p2}/{project_name}/{file_name}"
    output_file = f"{p2}/{project_name}/{project_name}_{date_str}.epub"
    css_file = f"{p2}/lib/epub.css"

    # Define the metadata
    title = 'gemini translation test'
    title_file = f"{p2}/{project_name}/title.md"

    # Convert the file, both versions work..
    # pypandoc.convert_file([title_file, input_file], 'epub', outputfile=output_file, extra_args=['--css=' + css_file])
    pypandoc.convert_file(input_file, 'epub', outputfile=output_file,
                          extra_args=['--css=' + css_file, f'--metadata=title:"{title}"'])


def load_and_process_paragraphs(prompts_to_process, save_unknowns=True):
    global conf, stats, paragraphs, cycles

    # if paragraphs are already loaded (eg rerun main), no need to reload paragraphs

    try:
        cycles += 1
        print(f' ----  new start of main: {cycles}x ------')
    except Exception as e:
        cycles = 0

    if cycles == 0:
        if pickle_paragraphs_exists(conf['project_name']):
            paragraphs = unpickle_paragraphs(conf['project_name'])

            ## best to set groups_to_process = 1, run through it once, and than comment the mark_pra.. function out again
            ##  because only after all goups are processed, will the paragraphs be pickled again..
            # mark_paragraphs_unsuccessful(model='gemini_1.0_k.rob_2024.03.23')
            # mark_paragraphs_unsuccessful(model='gemini_1.0_2024.03.23')
        else:
            # grab from url is not working too well, proof of concept more than anything
            # my_grab_urls.prepare_input(conf['project_name'])

            filename = conf['input_file']

            if filename is None:
                print('when you start a new project, you need to specify an input file with the option -i')
                sys.exit(1)

            paragraphs = load_paragraphs(filename)

            pickle_paragraphs(conf['project_name'])

        # on first load import all paragaphs
        import_ai_answers_to_paragraphs(f"{conf['project_name']}/{conf['path_answers_api']}")

    # returns a list of queries: [{paragraphs: list_of_paragraph_ids, model: AI model to query,
    #                               prompt: prompt_text+some_paragraphs,
    #                               temperature: float, top_k=int, top_p=float}

    if True:
        paragraph_stats = compile_paragraph_statics(paragraphs, prompts_to_process)

        safety_rating_overview = safety_matrix_to_text(paragraph_stats)

        paragraph_groups = create_paragraph_groups(paragraphs, conf['prompts'], prompts_to_process)

        paragraphs = run_queries(paragraph_groups, paragraphs, conf['prompts'])

        if 'transliterate' in prompts_to_process:
            # if not imported yet, import the transliteration libs
            if "lib.my_transliteration_paiboon" not in sys.modules:
                from lib import my_transliteration_paiboon

            unknowns = []
            for i, p in enumerate(paragraphs):
                if 'transliterate' not in paragraphs[i]:
                    (transliteration, unknown_words) = my_transliteration_paiboon.tokenize_and_transliterate(
                            paragraphs[i]['original']['text'])
                    paragraphs[i]['transliterate'] = {
                        'text': transliteration }
                    unknowns = unknowns + unknown_words

            if save_unknowns:
                unique_sorted_unknowns = sorted(set(unknowns))
                # output written to file, in case terminal doesn't support some characters
                with open(f"{conf['project_name']}/tranliteration_unknown_words.txt", 'w', encoding='utf-8') as f:
                    f.write('\t\n'.join(unique_sorted_unknowns))

        import_ai_answers_to_paragraphs(f"{conf['project_name']}/{conf['path_answers_api']}")

        pickle_paragraphs(conf['project_name'])

    # save_paragraphs_to_json(paragraphs, file_name=f'{conf['project_name']}/paragraphs_original.json')
    # save_paragraphs_to_xml3(paragraphs,
    #                         file_name=f'{conf['project_name']}/lp_choob_paragraphs_original_v01_complex.xml')
    # save_paragraphs_to_xml2(paragraphs, file_name=f'{conf['project_name']}/lp_choob_paragraphs_original_v01_medium.xml')


def save_paragraphs_to_epub(prompts_to_display, date_str):
    final_text = merge_paragraphs(paragraphs, prompts_to_display)
    # Get the current date and time

    file_name = f'translated_{date_str}.md'
    file_name_full = f'{conf["project_name"]}\\{file_name}'
    with open(file_name_full, 'w', encoding='utf-8') as file:
        file.write(final_text)

    create_epub(file_name, conf["project_name"], date_str)
    print(f"File '{file_name}' saved successfully.")


def save_matrix_to_cvs(file_name, li):
    # li is already in the correct format - funny
    # ma = []
    # for row in l:
    #     r = []
    #     for cell in row:
    #         r.append(cell)
    #     ma.append(r)

    # file_name = f'{conf['project_name']}/{conf['project_name']}_{date_str}.csv'
    # Open the file in write mode ('w') and create a csv.writer object
    # Ensure to open the file with newline='' to prevent adding extra newline characters on Windows
    with open(file_name, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Write all rows at once
        writer.writerows(li)

    print(f"File '{file_name}' saved successfully.")


def save_paragraphs_to_cvs(prompts_to_display, date_str, stat_str):
    global conf, paragraphs

    c = [prompts_to_display]

    for p in paragraphs:
        row = []

        for pr in prompts_to_display:
            if pr in p:
                if pr == '':
                    row.append('')
                    continue
                try:
                    text1 = re.sub(r'\n', ' ', p[pr]['text'])
                    text1 = re.sub('\n', ' ', text1)
                    text1 = re.sub(r'\t', ' ', text1)
                    text1 = re.sub('\t', ' ', text1)
                except Exception as e:
                    print('  csv export: no {str(pr)} element in paragraph or no text var..')
                row.append(text1)
            else:
                row.append('')

        c.append(row)
    stat_strs = stat_str.split('\n')
    for s1 in stat_strs:
        c.append([s1])
    file_name = f'{conf["project_name"]}/{conf["project_name"]}_{date_str}.csv'
    # Open the file in write mode ('w') and create a csv.writer object
    # Ensure to open the file with newline='' to prevent adding extra newline characters on Windows
    with open(file_name, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Write all rows at once
        writer.writerows(c)

    print(f"File '{file_name}' saved successfully.")


def save_paragraphs_to_json(paragraphs, file_name, only_original_text=True):
    # Create list of key-value pairs as objects
    json_array_with_keys = [{f"{str(k + 2)}": v['original']['text']} for k, v in enumerate(paragraphs)]

    json_string_1 = json.dumps(json_array_with_keys, ensure_ascii=False)

    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(json_string_1)

    return json_array_with_keys


def mark_paragraphs_unsuccessful(model='chatGPT', paragraph_id_from=0, paragraph_id_to=99999):
    global paragraphs
    for i in range(paragraph_id_from, paragraph_id_to):
        if i > len(paragraphs):
            break
        try:
            paragraphs[i][model]['success'] = False
        except Exception as e:
            print(f' -mark unsuccessful not possible for paragraph {i}')


def save_paragraphs_to_xml3(paragraphs, file_name, only_original_text=True, simple=False):
    # Create list of key-value pairs as objects
    xml_dict = [{k: v['original']['text']} for k, v in enumerate(paragraphs)]

    import xml.etree.ElementTree as ET

    # Create the root element
    root = ET.Element('items')

    if simple:
        # Iterate over the dictionary items and create an 'item' element for each
        for key, value in enumerate(xml_dict):
            item = ET.SubElement(root, 'item')
            item.set('key', str(key))
            item.set('value', value)
    else:
        for key, value in enumerate(xml_dict):
            item_element = ET.SubElement(root, 'item')
            key_element = ET.SubElement(item_element, 'key')
            key_element.text = str(key)
            value_element = ET.SubElement(item_element, 'value')
            value_element.text = str(value)

    # Convert the ElementTree to a string and write it to a file
    tree = ET.ElementTree(root)

    with open(file_name, 'wb') as file:
        tree.write(file, encoding='utf-8', xml_declaration=True)

    return tree


def save_paragraphs_to_xml2(paragraphs, file_name, only_original_text=True):
    import dicttoxml

    # Create list of key-value pairs as objects
    xml_dict = [{k: v['original']['text']} for k, v in enumerate(paragraphs)]

    xml = dicttoxml.dicttoxml(xml_dict, custom_root='items', item_func=lambda x: 'item')

    # print(xml)
    # json_string_1 = json.dumps(json_array_with_keys, ensure_ascii=False)

    # with open(file_name, 'w', encoding='utf-8') as file:
    with open(file_name, 'wb') as file:
        file.write(xml)

    return xml


def save_paragraphs_to_xml(paragraphs, file_name, max_tokens=4000, only_original_text=True,
                           word_substitution_list=False):
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom.minidom import parseString

    groups = my_text.group_paragraphs_by_tokens(paragraphs, max_tokens=max_tokens, prompt_name='to_xml',
                                                process_only_unfinished=False)

    items = Element('items')

    # for k, v in enumerate(paragraphs):
    #     SubElement(items, 'value', {'id': str(k + 2)}).text = v['original']['text']
    token_count = 0
    for gr_id, group in enumerate(groups):
        for p_id in group:
            text = paragraphs[p_id]['original']['text']
            if word_substitution_list:
                text = replace_with_word_substitution_list(text, wrap='exp')
            token_count += my_text.token_count(text)
            SubElement(items, 'item', {'id': str(p_id + 2), 'gr': str(gr_id), 'tk': str(token_count)}).text = re.sub(
                r'\n', ' ', text)

    xml_str = tostring(items, 'utf-8')
    pretty_xml = parseString(xml_str).toprettyxml()

    with open(file_name, 'w', encoding='utf-8') as xml_file:
        xml_file.write(pretty_xml)

    return pretty_xml


if __name__ == '__main__':

    paragraphs = {}

    try:
        init_config()
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

    load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])
    # load_and_process_paragraphs(conf['prompts_to_process'])

    #save_paragraphs_to_xml(paragraphs, file_name=f'{conf["project_name"]}/xml_2000tok.xml', max_tokens=2000)
    save_paragraphs_to_xml(paragraphs, file_name=f'{conf["project_name"]}/xml_1300tok.xml', max_tokens=1300)
    # save_paragraphs_to_xml(paragraphs, file_name=f'{conf['project_name']}/lp_fug_3200tok_word-repl.xml',
    #                        max_tokens=2000, word_substitution_list=True)

    now = datetime.now()
    date_str = now.strftime('%Y.%m.%d_%H%M')

    # save_paragraphs_to_epub(conf['prompts_to_display'], date_str)

    stat_text_prompts, stat_text_execution = format_stats(stats, conf)
    print(stat_text_execution)

    save_paragraphs_to_cvs(conf['prompts_to_display'], date_str, stat_text_prompts + stat_text_execution)
