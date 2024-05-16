

def load_prompts(conf):

    pro = {}


    pro['A_cre_gemini_1.5'] = {
        'prompt': """
                        I give you a part of an xml file in Thai Language.
                        Output in the same xml structure. <item> elements can not be merged together for translation or output.

                        translate the text of the <item> elements into Manderin with simplified Chinese script. 
                        do not include any explanations, just translate. 

                        for pali terms like dukkha, samsara use established Chinese Buddhist terms that correspond to these concepts.
                        for example: dukkha -> 苦, samsara -> 轮回 or 生死 

             """,
        'temperature': '1.0', 'top_p': '0.95', 'top_k': '0',
        'engine': 'gemini', 'model': 'models/gemini-1.5-pro-latest', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 31,  # 2 RequestsPM, 32,000 TokensPM, 50 RPDay
        'max_tokens_per_query': conf['max_tokens_per_query__gemini1.5'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    # kruba bue
    pro['B_pali_nor_gemini1.5'] = {
        'prompt': """
                        I give you a part of an xml file in Thai Language.
                        Output in the same xml structure. <item> elements can not be merged together for translation or output.

                        translate the text of the <item> elements into Manderin with simplified Chinese script. 
                        do not include any explanations, just translate. 

                        do not translate pali terms like  苦 , 乐 , 烦恼 , 天 , 修 , 定 , 观 , 慧 , 灭 , 行 , 法 , 托钵 , 大 , 境 , 功课 , 
                        解脱 , 想 , 受 , 无常 , 色 , 无我 , 僧 , 比丘 , 律 , 禅 , 舍 , 慈 , 正见 , 戒 , 慧 , 轮回 , 烦恼 . 
                        write them in pali in simplified chinese script.

             """,
        'temperature': '0.9', 'top_p': '0.50', 'top_k': '0',
        'engine': 'gemini', 'model': 'models/gemini-1.5-pro-latest', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 31,  # 2 RequestsPM, 32,000 TokensPM, 50 RPDay
        'max_tokens_per_query': conf['max_tokens_per_query__gemini1.5'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    pro['C_nor_gemini1.0'] = {
        'prompt': """
                        I give you a part of an xml file in Thai Language.
                        Output in the same xml structure into a code block. <item> elements can not be merged together for translation or output.

                        translate all the text of the <item> elements into Manderin with simplified Chinese script. 
                        do not include any explanations, just translate. 

                        for pali terms like dukkha, samsara translate into manderin in established Chinese Buddhist terms that correspond to these concepts.
                        for example: dukkha -> 苦, samsara -> 轮回 or 生死 
                        

            """,
        'temperature': '0.9', 'top_k': '8', 'top_p': '0.5',
        'engine': 'gemini', 'model': 'models/gemini-1.0-pro', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 9,
        # 15 RPM (requests per minute), 32,000 TPM (tokens per minute), 1500 RPD (requests per day)

        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    pro['D_pali_str_gemini1.0'] = {
        'prompt': """
                        I give you a part of an xml file in Thai Language.
                        Output in the same xml structure into a code block. <item> elements can not be merged together for translation or output.

                        translate all the text of the <item> elements into Manderin with simplified Chinese script. 
                        do not include any explanations, just translate. 

                        do not translate pali terms like  苦 , 乐 , 烦恼 , 天 , 修 , 定 , 观 , 慧 , 灭 , 行 , 法 , 托钵 , 大 , 境 , 功课 , 
                        解脱 , 想 , 受 , 无常 , 色 , 无我 , 僧 , 比丘 , 律 , 禅 , 舍 , 慈 , 正见 , 戒 , 慧 , 轮回 , 烦恼 . 
                        write them in pali in simplified chinese script.
                        

            """,
        'temperature': '0.75', 'top_k': '15', 'top_p': '0.8',
        'engine': 'gemini', 'model': 'models/gemini-1.0-pro', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 9,
        # 15 RPM (requests per minute), 32,000 TPM (tokens per minute), 1500 RPD (requests per day)

        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }


    return pro