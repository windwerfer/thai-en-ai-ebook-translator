import re


def load_prompts(conf, encode_as='json', pali=True):

    pro = {}
    if (pali):
        pali_terms = """              
        keep pali terms in pali like for example dukkha, sukkha,
        kilesa, deva, khadas, bhāvanā, samādhi, vipassanā, paññā, nirodha, saṅkhāra, dhamma, piṇḍapāta, maha, 
        ārammaṇa, kammaṭṭhāna, vimutti, saññā, vedanā, anicca, rupa, anattā, saṅgha, bhikkhu, vinaya, jhāna, 
        upekkhā, mettā, sammādiṭṭhi, sīla, paññā, saṃsāra, āsavā and write them in romanized pali  
        (don't translate pali terms them into: suffering, happiness, defilement, angel etc). 

        passages in pali need to be romanized (eg. Evaṃ me sutaṃ). Take special care to translate places and names correctly.
        """
    else:
        pali_terms = """
        
        """
    if encode_as == 'json':
        output_format = """
        The input is a json string with a key and value pair. Output as a json string into a code block  (surround the json with ```). 
        translate and change only the values.
        """
    else:
        output_format = """
        I give you a part of an txt file with a xml structure, the top-level element is  <items> and it contains multiple <item> elements. 
        Each <item> element has a unique id and some text inside the tag (eg <item id="7">some text to translate</value> ).
        Output in the same xml structure into a code block  (surround the xml with ```). <item> elements can not be merged together for translation or output.
        all items need to be translated in sequence, if max token is reached, simply stop with the warning: max token reached.
        do not include any explanations.
        """


    pro['chatGPTo_02'] = {
        'prompt': f"""

        You are a translator app now. 

        {output_format}
        
        Translate the {encode_as} values into English (you, the awesome translator app). 
        
        {pali_terms}

        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun


                """,
        'platform': 'perplexity', 'model': 'chatGPTo',
    }

    pro['chatGPT_02'] = {
        'prompt': f"""

        You are a translator app now. 

        {output_format}
        
        Translate the {encode_as} values into English (you, the awesome translator app). 
        
        {pali_terms}

        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun


                """,
        'platform': 'perplexity', 'model': 'chatGPT',
    }
    pro['claude_02'] = {
        'prompt': f"""

        You are a translator app now. 

        {output_format}

        Translate the {encode_as} values into English (you, the awesome translator app). 
        
        {pali_terms}

        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun

 
                """,
        'platform': 'perplexity', 'model': 'claude_opus',
    }






    #-----------------------------------------------------------------------------------------------
    # -------------------------------------not needed anymore --------------------------------------


    pro['gemini_1.5'] = {
        'prompt': f"""

        I give you a part of an txt file with a xml structure, the top-level element is  <items> and it contains multiple <item> elements. 
        Each <item> element has a unique id and some text inside the tag (eg <item id="7">some text to translate</value> ).
        Output in the same xml structure and print into a code block. <item> elements can not be merged together for translation or output.
        all items need to be translated in sequence. 
        do not include any explanations.

        Translate the xml values into English (you, the awesome translator app). 
        
        {pali_terms}


        Some special names I want you to translate as follows: พระอาจารย์ฟัก = Luang Pu Fug, พระอาจารย์มั่น = Luang Pu Mun


        -----xml text:-----

    """,
        'platform': 'perplexity', 'model': 'claude_opus',
    }

    for i, p in pro.items():
        pro[i]['prompt'] = remove_double_whitepace(pro[i]['prompt'])

    return pro


def remove_double_whitepace(text):
    text = re.sub(r'^[ ]+','',text)
    text = re.sub(r'[ ]+$','',text)
    text = re.sub(r'[ ]{2,}',' ',text)
    return text