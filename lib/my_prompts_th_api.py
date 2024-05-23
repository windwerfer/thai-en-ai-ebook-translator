import re


def load_prompts(conf, pali=True):

    if conf['encode_as'] == 'json':
        output_format = """
        The input is a json string with a key and value pair. Output as a json string. 
        translate and change only the values.
        """
    else:
        output_format = """
        I give you a part of an xml file.
        Output in the same xml structure into a code block. <item> elements can not be merged together for translation or output.

        translate the text of the <item> elements into english. do not include any explanations, just translate. 
        """

    if (pali):
        pali_terms = """              
        keep all pali terms in pali. for example dukkha, sukkha,
        kilesa, deva, khadas, bhāvanā, samādhi, vipassanā, paññā, nirodha, saṅkhāra, dhamma, piṇḍapāta, maha, 
        ārammaṇa, kammaṭṭhāna, vimutti, saññā, vedanā, anicca, rupa, anattā, saṅgha, bhikkhu, vinaya, jhāna, 
        upekkhā, mettā, sammādiṭṭhi, sīla, paññā, saṃsāra, āsavā and write them in romanized pali  
        

        passages in pali need to be romanized (eg. Evaṃ me sutaṃ). Take special care to translate places and names correctly.
        """
    else:
        pali_terms = """

        """
    # (don't translate pali terms them into: suffering, happiness, defilement, angel etc).

    pro = {}

    # special case: Thai transliteration. processed through pythainlp not gemini
    # engine: 'transliterate__pythainpl_dict_paiboon'
    pro['transliterate'] = {
        # 'prompt': 'transliterate the thai text with the ISO 11940 system. do not include any explanations. keep html tags.\n\nText: ',
        'prompt': 'Transliteration is now done through the pythainpl library, together with a dictionary thai(script)->transliteration(paiboon). (not through gemini or chatgpt)',
        # 'temperature': '0.6', 'top_k': '2', 'top_p': '0.4',
        'engine': 'pythainpl_dict_paiboon', 'position': 'prepend', 'type': 'footnote',
        'use_word_substitution_list': False,
    }



    pro['gemini_15_cre_01'] = {
        'prompt': f"""
                        {output_format}

                        Translate the {conf['encode_as']} values into English (you, the awesome translator app). 
                        
                        do not include any explanations, just translate. 

                        {pali_terms}

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun


            """,
        'temperature': '0.9', 'top_p': '0.65', 'top_k': '0',
        'engine': 'gemini', 'model': 'models/gemini-1.5-pro-latest', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 31,  # 2 RequestsPM, 32,000 TokensPM, 50 RPDay
        'max_tokens_per_query': conf['max_tokens_per_query__gemini1.5'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }
    pro['gemini_15_nor_01'] = {
        'prompt': f"""
                        {output_format}

                        Translate the {conf['encode_as']} values into English (you, the awesome translator app). 
                        
                        do not include any explanations, just translate. 

                        {pali_terms}

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun


            """,
        'temperature': '0.9', 'top_k': '8', 'top_p': '0.5',
        'engine': 'gemini', 'model': 'models/gemini-1.5-pro-latest', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 31,  # 2 RequestsPM, 32,000 TokensPM, 50 RPDay
        'max_tokens_per_query': conf['max_tokens_per_query__gemini1.5'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }
    pro['gemini_15flash_nor_01'] = {
        'prompt': f"""
                        {output_format}

                        Translate the {conf['encode_as']} values into English (you, the awesome translator app). 
                        
                        do not include any explanations, just translate. 
                        
                        {pali_terms}

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

            """,
        'temperature': '0.9', 'top_k': '8', 'top_p': '0.5',
        'engine': 'gemini', 'model': 'models/gemini-1.5-flash-latest', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 31,  # 2 RequestsPM, 32,000 TokensPM, 50 RPDay
        'max_tokens_per_query': conf['max_tokens_per_query__gemini1.5'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    pro['gemini_1_nor'] = {
        'prompt': f"""
                        {output_format}

                        Translate the {conf['encode_as']} values into English (you, the awesome translator app). 
                        
                        do not include any explanations, just translate. 
                        
                        {pali_terms}

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

            """,
        'temperature': '0.9', 'top_k': '8', 'top_p': '0.5',
        'engine': 'gemini', 'model': 'models/gemini-1.0-pro', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 9,
        # 15 RPM (requests per minute), 32,000 TPM (tokens per minute), 1500 RPD (requests per day)

        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    pro['gemini_1_krob_01'] = {
        'prompt': f"""                    
                        {output_format}

                        Translate the {conf['encode_as']} values into English (you, the awesome translator app). 
                        
                        do not include any explanations, just translate. 
                        
                        {pali_terms}

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

            """,
        'temperature': '0.75', 'top_k': '15', 'top_p': '0.8',
        'engine': 'gemini', 'model': 'models/gemini-1.0-pro', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 9,
        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    for i, p in pro.items():
        pro[i]['prompt'] = remove_double_whitepace(pro[i]['prompt'])

    return pro


def remove_double_whitepace(text):
    text = re.sub(r'^[ ]+','',text)
    text = re.sub(r'[ ]+$','',text)
    text = re.sub(r'[ ]{2,}',' ',text)
    return text