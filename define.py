#!/usr/bin/env python3
"""This module contains the functions used for retrieving word definitions.

Outside of this module, you'll usually just call the define() function.
"""
import console
import json
import re
from urllib.error import URLError
from config import CONFIG_FILE

WORDNIK_IS_LOADED = False


def check_wordnik_key():
    """Check if the WordNik API is reachable."""
    global WORDNIK_API_KEY
    global WORDNIK_IS_LOADED
    global wn_api
    try:
        with open(CONFIG_FILE, 'r') as file:
            WORDNIK_API_KEY = json.load(file).get('wordnik_api_key')
        WORDNIK_IS_LOADED = bool(WORDNIK_API_KEY)
    except FileNotFoundError:
        WORDNIK_API_KEY = None
    if WORDNIK_API_KEY:
        try:
            wn_api = WordApi(swagger.ApiClient(WORDNIK_API_KEY,
                                               WORDNIK_API_URL))
        except NameError:
            WORDNIK_IS_LOADED = False


try:
    from wordnik import swagger
    from wordnik.WordApi import WordApi
    WORDNIK_API_URL = 'https://api.wordnik.com/v4'
    check_wordnik_key()
except ImportError:
    WORDNIK_IS_LOADED = False


def define(word: str):
    """Return definition and metadata for a given word.

    It's returned in the following dictionary format:
    {'word' : 'word',
     'definitions': [{'text': 'The first definition',
                      'partofspeech': 'noun'},
                     {'definition': 'The second definition',
                      'text': 'verb'}],
     'attribution': 'Dictionary Source, Public Domain',
     'attributionUrl' : 'https://creativecommons.org/publicdomain/zero/1.0/',
     'suggestions': ['suggestion one', 'suggestion two'],
     'messages' : ['error message one', 'error message two']
    }
    """
    if WORDNIK_IS_LOADED:
        data = wordnik(word)
    else:
        data = opted(word)
        m = ['WordRoom is using a limited offline dictionary.',
             '''This app is a free personal project, so I don't share my online
             API access. <a href="https://developer.wordnik.com/">You can get
             your own from developer.wordnik.com</a>''',
             '''<a href="wordroom://-change_key">Add an API key to WordRoom
             here.</a>''']
        if not data['definitions']:
            data['messages'] += m
    data['word'] = word
    return data


def wordnik(word: str):
    """Return the WordNik definition of a word.

    If can't connect to WordNik API, then return opted() instead.
    """
    try:
        console.show_activity()
        defs = wn_api.getDefinitions(word, limit=5) or []
        suggs = wn_api.getWord(word, includeSuggestions=True)
        console.hide_activity()
        suggestions = suggs.suggestions or []
        definitions = [{'text': d.text,
                        'partOfSpeech': d.partOfSpeech} for d in defs]
        if defs:
            attribution = defs[0].attributionText
            attribution_url = defs[0].attributionUrl
        else:
            attribution = ''
            attribution_url = ''
        data = {'definitions': definitions,
                'attribution': attribution,
                'attributionUrl': attribution_url,
                'suggestions': suggestions,
                'messages': []}
    except URLError:
        data = opted(word)
        data['messages'].append('''WordRoom couldn't connect to WordNik.com to
                                retrieve online definitions.''')
    return data


opted_cache = {}


def opted(word: str):
    """Return the OPTED definition of a word."""
    messages = []
    alpha = re.sub('[^a-zA-Z]', '', word)[:1].lower()
    if not opted_cache.get(alpha) and alpha:
        try:
            with open('opted/' + alpha + '.json', 'r') as f:
                opted_cache[alpha] = json.load(f)
        except FileNotFoundError:
            opted_cache[alpha] = {}
            messages.append('''WordRoom couldn't load the offline dictionary.
                            If you're storing WordRoom in iCloud, check that
                            iOS downloaded all of its files.''')
    if alpha:
        definitions = opted_cache[alpha].get(word) or []
    else:  # if the input had no ascii letters
        definitions = []
    if len(definitions) > 0:
        attr = 'from The Online Plain Text English Dictionary, Public Domain.'
        attribution_url = 'http://www.mso.anu.edu.au/%7Eralph/OPTED/index.html'
    else:
        attr = ''
        attribution_url = ''
    return {'definitions': definitions,
            'attribution': attr,
            'attributionUrl': attribution_url,
            'suggestions': [],
            'messages': messages}
