# -*- coding: utf-8 -*-

# how it works:
#   the thai sentences are first tokenized (split into individual words)
#   and then transliterated through a dictionary (thai2ipa.data)

from __future__ import absolute_import, unicode_literals

import codecs

from marisa_trie import Trie
from pythainlp.tokenize import word_tokenize
from pythainlp.transliterate import romanize

# 3.3.2024 data from https://thai-notes.com/tools/thai2ipa.data
template_file = "thai2ipa.data"
with codecs.open(template_file, 'r', encoding='utf8') as f:
    lines = f.read().splitlines()
data = {}
for t in lines:
    w = t.split('\t')
    data[w[0]] = w[1]
DEFAULT_DICT_TRIE = Trie(data.keys())


def word_tokenize_to_g2p(text):
    words = word_tokenize(text)
    ret = []
    for w in words:
        try:
            ret.append(data[w])  # romanize(a,engine='pyicu'))

        # backup transliteration if not found in dictionary
        except:
            word_list_icu = word_tokenize(w, engine="icu")
            for b in word_list_icu:
                ret.append(romanize(b, engine='pyicu'))
    return ' '.join(ret)


if __name__ == "__main__":
    while True:
        tt = input("Text : ")
        a = word_tokenize_to_g2p(tt)
        print(a)

        # output written to file, in case terminal doesn't support some characters
        with open('file.txt', 'w', encoding='utf-8') as f:
            f.write(a)
