import console
import string
import json
from urllib.error import URLError
from config import *

WORDNIK_IS_LOADED = False


def check_wordnik_key():
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
    '''Returns word data in the following dictionary format:
    {'word' : 'word',
     'definitions': [{'definition': 'The first definition',
                      'partofspeech': 'noun'},
                     {'definition': 'The second definition',
                      'partofspeech': 'verb'}
                    ],
     'attribution': 'Dictionary Source, Public Domain',
     'suggestions': ['suggestion one', 'suggestion two'],
     'messages' : ['error message one', 'message two']
    }
    '''
    if WORDNIK_IS_LOADED:
        data = wordnik(word)
    else:
        data = opted(word)
        # this uses a special link that main.py uses to open the API Key dialog
        m = '''WordRoom is using a limited offline dictionary.
            <a href="wordroom://-change_key">Open the WordRoom settings to
            activate access to the complete online sources.</a><br/><br/>
            <a href="https://developer.wordnik.com/">Get an API key from
            developer.wordnik.com</a>'''
        data['messages'].append(m)
    data['word'] = word
    return data

    
def wordnik(word: str):
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
        else:
            attribution = ''
        data = {'definitions': definitions,
                'attribution': attribution,
                'suggestions': suggestions,
                'messages': []}
    except URLError:
        data = opted(word)
        data['messages'].append('''WordRoom couldn't connect to WordNik.com to
                                retrieve online definitions.''')
    return data


opted_cache = {}


def opted(word: str):
    messages = []
    alpha = word[:1].lower()
    if not opted_cache.get(alpha):
        try:
            with open('opted/' + alpha + '.json', 'r') as f:
                opted_cache[alpha] = json.load(f)
        except FileNotFoundError:
            opted_cache[alpha] = {}
            messages.append('''WordRoom couldn't load the offline dictionary. If
                            you're storing WordRoom in iCloud, check that iOS
                            downloaded all of its files.''')
    definitions = opted_cache[alpha].get(word) or []
    if len(definitions) > 0:
        attr = 'from The Online Plain Text English Dictionary, Public Domain.'
    else:
        attr = ''
    return {'definitions': definitions,
            'attribution': attr,
            'suggestions': [],
            'messages': messages}

if __name__ == '__main__':
    print('Ya done goofed. Try running main.py instead.')
