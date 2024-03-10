# termux:
#   pkg install python-grpcio python-pillow   (in termux if venv, needs to passthrough those packages!!)
#   pip install google.generativeai
#   pip install pythainlp tzdata pprint regex chardet
import csv
import os
import pickle
import pprint
import re
import shutil
import subprocess  # to run a command in the terminal: run_command()
import textwrap
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from lib import my_text
from lib import my_transliteration_paiboon


def init_config():
    global conf, stats, files

    conf = {}
    conf['project_name'] = 'prj_lp_choob_02'

    conf['start_block'] = 31  # start at 0
    conf['end_block'] = 60  # put in 9999 for the end of the book
    conf['max_attempts'] = 15  # maximum retries to send to an AI before giving up
    conf['pause_between_retries'] = 5
    conf['max_tokens_per_query__gemini'] = 1400
    conf['pickle_paragraphs_every_X_successfull_querys'] = 20
    conf['max_workers'] = 10  # nr of queries run simultaniusly
    if is_debugger_enabled():
        print('debuger enbled -> set max_workers to 1')
        conf[
            'max_workers'] = 1  # run only one process if debugging, otherwise the other elements in the queue will finish before debugin is stoped -> error

    # files = {}
    # files['out'] = open(conf['project_name'] + '/translated.txt', 'w', encoding='utf-8')
    # files['error_out'] = open(conf['project_name'] + '/errors.txt', 'w', encoding='utf-8')
    # files['blocks'] = open(conf['project_name'] + '/blocks.txt', 'w', encoding='utf-8')

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

    conf['prompts'] = {}

    # engine: 'transliterate__pythainpl_dict_paiboon'  ->   uses the pythainpl lib to transliterate
    conf['prompts']['transliterate'] = {
        # 'prompt': 'transliterate the thai text with the ISO 11940 system. do not include any explanations. keep html tags.\n\nText: ',
        'prompt': 'Transliteration is now done through the pythainpl library, together with a dictionary thai(script)->transliteration(paiboon). (not through gemini or chatgpt)',
        # 'temperature': '0.6', 'top_k': '2', 'top_p': '0.4',
        'engine': 'pythainpl_dict_paiboon', 'position': 'prepend', 'type': 'footnote',
        'use_word_substitution_list': False,
    }

    # keep html tags and characters that are in roman/latin  unchanged.

    word_annotation_hint = 'Text in Square Brackets are annotations how the word before should be handled ' + \
                           'differently. if they contain a condition, only follow the annotation if the ' + \
                           'condition is met. do not print text in square brackets.'

    conf['prompts']['gemini_default_2024.03'] = {
        'prompt': 'translate the text into english. do not include any explanations, just translate. keep paragraphs divided by newline.\n\n ',
        'temperature': '0.6', 'top_k': '2', 'top_p': '0.4', 'engine': 'gemini', 'position': 'append',
        'type': 'paragraph', 'use_word_substitution_list': 'default', 'use_word_annotation_list': 'default',
        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text

    }

    conf['prompts']['gemini_literal_2024.03'] = {
        'prompt': 'translate the text into english. do not include any explanations, just translate. keep paragraphs divided by newline.\n\n ',
        'temperature': '0.2', 'top_k': '1', 'top_p': '0.4',
        'engine': 'gemini', 'position': 'append', 'type': 'footnote', 'label': 'more literal',
        'use_word_substitution_list': 'default',
        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    conf['prompts']['gemini_creative_2024.03'] = {
        'prompt': 'translate the text into english. do not include any explanations, just translate. keep paragraphs divided by newline.\n\n ',
        'temperature': '1.0', 'top_k': '3', 'top_p': '0.4',
        'engine': 'gemini', 'position': 'append', 'type': 'footnote', 'label': 'more flowing',
        'use_word_substitution_list': 'default',
        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    conf['prompts']['gemini_k.rob_creative02'] = {
        'prompt': 'translate the text into english. do not include any explanations, just translate. keep paragraphs divided by newline.\n\n ',
        'temperature': '0.75', 'top_k': '15', 'top_p': '0.8',
        'engine': 'gemini', 'position': 'append', 'type': 'footnote', 'label': 'more flowing',
        'use_word_substitution_list': 'default',
        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    conf['word_substitution_list'] = load_word_substitution_list('lib/word_substitution_list.data')
    conf['word_translation_annotation_list'] = load_word_translation_annotation_list(
        'lib/word_translation_annotation_list.data')

    stats = {}
    stats['start_time'] = time.time()
    stats['total_requests'] = 0
    stats['total_success'] = 0
    stats['total_failed'] = 0
    stats['total_paragraph_missmatch'] = 0
    stats['total_retries'] = 0
    stats['total_tokens_send'] = 0
    stats['total_tokens_received'] = 0
    stats['failed_paragraphs'] = []


def load_word_substitution_list(file_name='lib/word_substitution_list.data'):
    with open(file_name, 'r', encoding='utf8') as f:
        lines = f.read().splitlines()
    data = {}
    for t in lines:
        w = t.split(',', 1)
        if len(w) != 2:
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


def pickle_paragraphs(project_dir):
    global paragraphs
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
    GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY_wasser']  # to fetch an environment variable.
    GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY_wdcmm']  # to fetch an environment variable.
    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel('gemini-pro')
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

    time.sleep(1)

    return {'text': text, 'success': success, 'finish_reason': finish_reason, 'safety_block': safety_block,
            'safety_rating': safety_rating}


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
            groups = my_text.group_paragraphs_by_tokens(paragraphs, max_tokens, prompt_name,
                                                        process_only_unfinished=True)
            prompts_to_process[prompt_name] = groups
        else:
            print(f'prompt id: {prompt_name} not found')
    return prompts_to_process


def group_query_ai(query):
    paragraphs_slice, group, prompt_name, prompt, conf, query_id = query

    print(f'   paragraph group {group[0]:>4}:{group[-1]:>4} - query nr {query_id + 1:>4}: start')

    text_group = ''
    for idx, p in enumerate(paragraphs_slice):
        text_group = text_group + f'\n\n{p["original"]["text"]}'

    # remove the 2 empty newlines at the beginning
    text_group = text_group[2:]

    # ask google
    if prompt['engine'] == 'gemini':
        ret = query_gemini(prompt['prompt'] + text_group, temperature=float(prompt['temperature']),
                           top_k=int(prompt['top_k']),
                           top_p=float(prompt['top_p']))
    # r = "\n\n".split(ret)

    ret['texts'] = my_text.split_paragraphs(ret['text'])

    # t = f'{prompt_name} + {paragraphs_slice[0]}'

    # safety ratings..
    # https://ai.google.dev/docs/safety_setting_gemini

    return ret


def run_queries(paragraph_groups, paragraphs, prompts):
    """  takes the paragraph list indexes from prompt_list and creates textblocks
            those textblocks will be sent to an AI (gemini only at the moment)
            after they arrive back, they will be transfered into the paragraphs variable
     """

    global stats, conf

    querys = []
    err = []  # format: [origin_text: , answer_text: , error_message]

    # run as multiple processes
    for prompt_name, groups in paragraph_groups.items():
        for group in groups:
            # assuming that each group is continuous (required when creating) the slice is done by using the first and last item of the group
            paragraphs_slice = paragraphs[group[0]:group[-1] + 1]

            # prepare the querys: a list of paragraphs to be send to the AI_query, the id of them in the original paragraphs list and the prompt that will be processed
            querys.append([paragraphs_slice, group, prompt_name, prompts[prompt_name], conf])

    # Create a ProcessPoolExecutor with a maximum of 3 processes
    with ProcessPoolExecutor(max_workers=conf['max_workers']) as executor:
        # Submit the tasks to the executor
        future_to_prompt = {executor.submit(group_query_ai, query + [query_id]): query_id for query_id, query in
                            enumerate(querys)}
        for future in as_completed(future_to_prompt):
            querys_id = future_to_prompt[future]
            stats['total_requests'] += 1

            try:
                # Get the result of the query
                result = future.result()
                if not result['success']:
                    # query failed, log to stats
                    stats['total_failed'] += 1
                    print(
                        f' paragraph group {querys[querys_id][1][0]:>4}:{querys[querys_id][1][-1]:>4} - query nr {querys_id + 1:>4}: failed (finish reason {result['finish_reason']})')
                # if the len of the result is equal the len of the second element of the in the querys list (= group)
                elif len(result['texts']) == len(querys[querys_id][1]):
                    # paragraphs match, probably correct
                    stats['total_success'] += 1

                    prompt_name = querys[querys_id][2]

                    # querys[idx][1]: list of all the paragraph ids, this paragraph_group send to query
                    # j is the id of the paragraph of the paragraph group
                    for j, paragraph_id in enumerate(querys[querys_id][1]):
                        try:
                            # try to assign the received paragraph text to paragraphs
                            paragraphs[paragraph_id][prompt_name]['text'] = result['texts'][j]
                            paragraphs[paragraph_id][prompt_name]['retries'] += 1
                        except KeyError:
                            # if this is the first time the paragraph was sent, the dict for that prompt_name
                            #   has to be created first
                            paragraphs[paragraph_id][prompt_name] = {}
                            paragraphs[paragraph_id][prompt_name]['text'] = result['texts'][j]
                            paragraphs[paragraph_id][prompt_name]['retries'] = 0

                        paragraphs[paragraph_id][prompt_name]['success'] = result['success']
                        paragraphs[paragraph_id][prompt_name]['finish_reason'] = result['finish_reason']
                        paragraphs[paragraph_id][prompt_name]['safety_block'] = result['safety_block']
                        paragraphs[paragraph_id][prompt_name]['safety_rating'] = result['safety_rating']
                        paragraphs[paragraph_id][prompt_name]['processed_in_paragraph_group'] = querys[querys_id][1]
                        paragraphs[paragraph_id][prompt_name]['prompt'] = [querys[querys_id][2], querys[querys_id][3]]

                    conf = querys[querys_id][4]

                    # pickle paragraphs from time to time -> no loss on errors
                    # if stats['total_success'] % conf['pickle_paragraphs_every_X_successfull_querys'] == 0:
                    #     pickle_paragraphs(conf['project_name'])
                    print(
                        f'   paragraph group {querys[querys_id][1][0]:>4}:{querys[querys_id][1][-1]:>4} - query nr {querys_id + 1:>4}: returned successfully')
                else:
                    stats['total_paragraph_missmatch'] += 1
                    err_msg = f' paragraph group {querys[querys_id][1][0]:>4}:{querys[querys_id][1][-1]:>4} - query nr {querys_id + 1:>4}: -- mismatched paragraphs'
                    org_text = ''
                    for paragraphs_slice in querys[querys_id][0]:
                        org_text += '\n\n' + paragraphs_slice['original']['text']
                    err.append([org_text[2:], result['text'], err_msg])
                    print(err_msg)

                # print(f"Result for prompt '{querys[idx][1]}': {" -- ".join(result)[0:40]}")

            except Exception as e:

                print(
                    f"unusual error paragraph group {querys[querys_id][1][0]:>4}:{querys[querys_id][1][-1]:>4} - query nr {querys_id + 1:>4}: " + str(
                        e))

    pickle_paragraphs(conf['project_name'])

    save_matrix_to_cvs(f'{conf['project_name']}/error.csv', err)

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
            stats[prompt_name]['retries'] += p[prompt_name]['retries']
            if p[prompt_name]['safety_block']:
                stats[prompt_name]['failed_because_of_safety'] += 1
            if p[prompt_name]['finish_reason'][0] == 2:
                stats[prompt_name]['failed_because_of_token_max'] += 1
            if p[prompt_name]['finish_reason'][0] == -2:
                stats[prompt_name]['failed_because_of_unknown'] += 1

            # add on point to the appropriate element
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


def load_and_process_paragraphs(prompts_to_process):
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
        else:
            # grab from url is not working too well, proof of concept more than anything
            # my_grab_urls.prepare_input(conf['project_name'])

            filename = conf['project_name'] + "/input.txt"

            paragraphs = load_paragraphs(filename)

            pickle_paragraphs(conf['project_name'])

    # returns a list of queries: [{paragraphs: list_of_paragraph_ids, model: AI model to query,
    #                               prompt: prompt_text+some_paragraphs,
    #                               temperature: float, top_k=int, top_p=float}

    if True:
        paragraph_stats = compile_paragraph_statics(paragraphs, prompts_to_process)

        safety_rating_overview = safety_matrix_to_text(paragraph_stats)

        paragraph_groups = create_paragraph_groups(paragraphs, conf['prompts'], prompts_to_process)

        paragraphs = run_queries(paragraph_groups, paragraphs, conf['prompts'])

        if 'transliterate' in prompts_to_process:
            for i, p in enumerate(paragraphs):
                paragraphs[i]['transliterate'] = {
                    'text': my_transliteration_paiboon.tokenize_and_transliterate(paragraphs[i]['original']['text'])}


def save_paragraphs_to_epub(prompts_to_display, date_str):
    final_text = merge_paragraphs(paragraphs, prompts_to_display)
    # Get the current date and time

    file_name = f'translated_{date_str}.md'
    file_name_full = f'{conf["project_name"]}\\{file_name}'
    with open(file_name_full, 'w', encoding='utf-8') as file:
        file.write(final_text)

    create_epub(file_name, conf["project_name"], date_str)


def save_matrix_to_cvs(file_name, l):
    ma = []
    for row in l:
        row = []
        for cell in row:
            row.append(cell)
        ma.append(row)

    # file_name = f'{conf['project_name']}/{conf['project_name']}_{date_str}.csv'
    # Open the file in write mode ('w') and create a csv.writer object
    # Ensure to open the file with newline='' to prevent adding extra newline characters on Windows
    with open(file_name, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Write all rows at once
        writer.writerows(ma)

    print(f"File '{file_name}' saved successfully.")


def save_paragraphs_to_cvs(prompts_to_display, date_str):
    global conf, paragraphs

    c = [prompts_to_display]

    for p in paragraphs:
        row = []

        for pr in prompts_to_display:
            if pr in p:
                if pr == '':
                    row.append('')
                    continue
                row.append(p[pr]['text'])
            else:
                row.append('')

        c.append(row)

    file_name = f'{conf['project_name']}/{conf['project_name']}_{date_str}.csv'
    # Open the file in write mode ('w') and create a csv.writer object
    # Ensure to open the file with newline='' to prevent adding extra newline characters on Windows
    with open(file_name, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Write all rows at once
        writer.writerows(c)

    print(f"File '{file_name}' saved successfully.")


if __name__ == '__main__':
    init_config()

    prompts_to_process = ['transliterate', 'gemini_default_2024.03', 'gemini_literal_2024.03',
                          'gemini_creative_2024.03']
    prompts_to_process = ['gemini_k.rob_creative02']
    prompts_to_process = ['gemini_default_2024.03']

    load_and_process_paragraphs(prompts_to_process)
    # load_and_process_paragraphs(prompts_to_process)
    # load_and_process_paragraphs(prompts_to_process)
    # load_and_process_paragraphs(prompts_to_process)
    # load_and_process_paragraphs(prompts_to_process)

    now = datetime.now()
    date_str = now.strftime('%Y.%m.%d_%H%M')
    prompts_to_display = ['original', 'transliterate', 'gemini_default_2024.03', 'gemini_literal_2024.03',
                          'gemini_creative_2024.03', 'gemini_k.rob_creative02']
    # save_paragraphs_to_epub(prompts_to_display, date_str)

    prompts_to_display = ['original', 'transliterate', '', 'gemini_default_2024.03', 'gemini_literal_2024.03',
                          'gemini_creative_2024.03', 'gemini_k.rob_creative02']
    # save_paragraphs_to_cvs(prompts_to_display, date_str)
