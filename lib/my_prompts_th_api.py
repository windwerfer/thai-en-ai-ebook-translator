

def load_prompts(conf):

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


    pro['gemini_1.5_nor_2024.05.08'] = {
        'prompt': """
                        I give you a part of an xml file.
                        Output in the same xml structure into a code block. <item> elements can not be merged together for translation or output.

                        translate the text of the <item> elements into english. do not include any explanations, just translate. 

                        don't put quote characters around pali terms eg. dukkha, sukkha,
                        kilesa, deva, khadas, bhāvanā, samādhi, vipassanā, paññā, nirodha, saṅkhāra, dhamma, piṇḍapāta, maha, 
                        ārammaṇa, kammaṭṭhāna, vimutti, saññā, vedanā, anicca, rupa, anattā, saṅgha, bhikkhu, vinaya, jhāna, 
                        upekkhā, mettā, sammādiṭṭhi, sīla, paññā, saṃsāra, āsavā and write them in romanized pali  
                        (like in the example, don't translate them into: suffering, happiness, defilement, angel etc). 

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

                        passages in pali need to be romanized (eg. Evaṃ me sutaṃ). Take special care to translate places and names correctly.

            """,
        'temperature': '0.9', 'top_p': '0.65', 'top_k': '0',
        'engine': 'gemini', 'model': 'models/gemini-1.5-pro-latest', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 31,  # 2 RequestsPM, 32,000 TokensPM, 50 RPDay
        'max_tokens_per_query': conf['max_tokens_per_query__gemini1.5'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    pro['gemini_1.0_2024.03.23'] = {
        'prompt': """
                        I give you a part of an xml file.
                        Output in the same xml structure into a code block. <item> elements can not be merged together for translation or output.

                        translate the text of the <item> elements into english. do not include any explanations, just translate. 

                        don't put quote characters around pali terms eg. dukkha, sukkha,
                        kilesa, deva, khadas, bhāvanā, samādhi, vipassanā, paññā, nirodha, saṅkhāra, dhamma, piṇḍapāta, maha, 
                        ārammaṇa, kammaṭṭhāna, vimutti, saññā, vedanā, anicca, rupa, anattā, saṅgha, bhikkhu, vinaya, jhāna, 
                        upekkhā, mettā, sammādiṭṭhi, sīla, paññā, saṃsāra, āsavā and write them in romanized pali  
                        (like in the example, don't translate them into: suffering, happiness, defilement, angel etc). 

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

                        passages in pali need to be romanized (eg. Evaṃ me sutaṃ). Take special care to translate places and names correctly.

            """,
        'temperature': '0.9', 'top_k': '8', 'top_p': '0.5',
        'engine': 'gemini', 'model': 'models/gemini-1.0-pro', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 9,
        # 15 RPM (requests per minute), 32,000 TPM (tokens per minute), 1500 RPD (requests per day)

        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    pro['gemini_1.0_k.rob_2024.03.23'] = {
        'prompt': """                    
                        I give you a part of an xml file.
                        Output in the same xml structure into a code block. <item> elements can not be merged together for translation or output.

                        translate the text of the <item> elements into english. do not include any explanations, just translate. 

                        don't put quote characters around pali terms eg. dukkha, sukkha,
                        kilesa, deva, khadas, bhāvanā, samādhi, vipassanā, paññā, nirodha, saṅkhāra, dhamma, piṇḍapāta, maha, 
                        ārammaṇa, kammaṭṭhāna, vimutti, saññā, vedanā, anicca, rupa, anattā, saṅgha, bhikkhu, vinaya, jhāna, 
                        upekkhā, mettā, sammādiṭṭhi, sīla, paññā, saṃsāra, āsavā and write them in romanized pali  
                        (like in the example, don't translate them into: suffering, happiness, defilement, angel etc). 

                        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

                        passages in pali need to be romanized (eg. Evaṃ me sutaṃ). Take special care to translate places and names correctly.

            """,
        'temperature': '0.75', 'top_k': '15', 'top_p': '0.8',
        'engine': 'gemini', 'model': 'models/gemini-1.0-pro', 'position': 'append', 'type': 'footnote',
        'label': 'more flowing',
        'use_word_substitution_list': False, 'min_wait_between_submits': 9,
        'max_tokens_per_query': conf['max_tokens_per_query__gemini'],
        # decides how many paragraphs will be sent at one time to the AI. 1 = each separately, 1400 = approx 4 pages of text
    }

    return pro