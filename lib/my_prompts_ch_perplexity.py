

def load_prompts(conf, pali=True):

    pro = {}

    if (pali):
        pali_terms = """              
        do not translate pali terms like  苦 , 乐 , 烦恼 , 天 , 修 , 定 , 观 , 慧 , 灭 , 行 , 法 , 托钵 , 大 , 境 , 功课 , 
        解脱 , 想 , 受 , 无常 , 色 , 无我 , 僧 , 比丘 , 律 , 禅 , 舍 , 慈 , 正见 , 戒 , 慧 , 轮回 , 烦恼 . 
        but write them in pali in simplified chinese script.
        """
    else:
        pali_terms = """
        for pali terms like dukkha, samsara use established Chinese Buddhist terms that correspond to these concepts.
        for example: dukkha -> 苦, samsara -> 轮回 or 生死 
        """

    output_format = """
    I give you a part of an txt file with a xml structure, the top-level element is  <items> and it contains multiple <item> elements. 
    Each <item> element has a unique id and some text inside the tag (eg <item id="7">some text to translate</value> ).
    Output in the same xml structure into a code block  (surround the xml with ```). <item> elements can not be merged together for translation or output.
    all items need to be translated in sequence, if max token is reached, simply stop with the warning: max token reached.
    do not include any explanations.
    """


    pro['chatGPT_pali'] = f"""

        You are a translator app now. 

        {output_format}

        Translate the xml values into Manderin with simplified Chinese script. 
         (you, the awesome translator app). 
         
         {pali_terms}
         
         """

    pro['chatGPTo_pali'] = f"""

        You are a translator app now. 

        {output_format}

        Translate the xml values into Manderin with simplified Chinese script. 
         (you, the awesome translator app). 

        {pali_terms}

        """

    pro['claude_pali'] = f"""

        You are a translator app now. 

        {output_format}

        Translate the xml values into Manderin with simplified Chinese script. 
         (you, the awesome translator app). 


        {pali_terms}

         """

    return pro