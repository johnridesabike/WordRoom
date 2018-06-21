#!/usr/bin/env python3
import ui
import console
import json
import random

class Vocabulary:
    '''This is the core class that processes all of the word data. It includes
    methods for setting, retrieving, and searching words and notes. It also
    includes the methods necessary for integrating into `ui.Tableview`.
    
    Data is stored as a list of dictionaries. In the future, this may change
    to something more robust like a SQL database.
    '''
    def __init__(self, data_file: str):
        # _words[0] is words with notes. _words[1] is history
        self._words = [{}, {}]
        self._query = ''  # used for searching the list
        self._ftq = False  # When True, queries search full-text
        self.data_file = data_file
        self.load_json_file()

    def load_json_file(self, filename=''):
        '''Note: needs better error handling.'''
        if not filename:
            filename = self.data_file
        try:
            with open(filename, 'r') as infile:
                self._words = json.load(infile)
        except FileNotFoundError:
            pass  # We'll just write a new one

    def save_json_file(self):
        with open(self.data_file, 'w') as outfile:
            json.dump(self._words, outfile)

    def set_word(self, word: str, notes=''):
        '''Adds a word or updates the word if it already exists.
        Words with notes are saved to the notes dictionary, and words without
        notes are saved to the history dictionary. A word can't be in both.
        '''
        word = word.strip()
        if word and notes:  # adds to notes
            self._words[0][word] = notes
            if word in self._words[1]:  # deletes duplicates
                del self._words[1][word]
        elif word:  # adds to history
            self._words[1][word] = notes
            if word in self._words[0]:  # deletes duplicates
                del self._words[0][word]

    def get_notes(self, word: str, ):
        '''looks up a word and returns its notes. Words without
        notess return empty strings. This can be used to check if a word
        is in the dictionary or not. 
        '''
        word = word.strip()
        if word in self._words[0]:
            return self._words[0][word]
        else:
            return ''
    
    def set_query(self, query: str):
        '''After calling this method, the Vocabulary object will return a
        filtered set of data that matches the query string. To "unset" the
        query, just set an empty string.
        '''
        self._query = query.strip()
    
    def fulltext_toggle(self, onoff=True):
        '''When set to `False`, queries only search words. When set to `True`,
        queries also search the full note text. 
        '''
        self._ftq = onoff
    
    def get_fulltext_toggle(self):
        '''Returns the status of the toggle.'''
        return self._ftq
    
    def _filter_query(self, word):
        '''Filters data based on the query and fulltext toggle'''
        hasdef = False
        if self._ftq and word in self._words[0]:
            w = self._words[0][word].casefold()
            hasdef = w.find(self._query.casefold()) != -1
        wordbegins = word.casefold().startswith(self._query.casefold())
        return hasdef or wordbegins

    def count_words(self, section: int):
        return len(self.list_words(section))
    
    def list_words(self, section: int):
        if self._query:
            words = filter(self._filter_query, self._words[section].keys())
        else:
            words = self._words[section].keys()
        return sorted(words, key=lambda s: s.casefold())
    
    def delete_word(self, section: int, word: str):
        word = word.strip()
        del self._words[section][word]

    def random_word(self):
        return random.choice(list(self._words[0].keys()))
    
    # ---- Tableview methods
    # the `_query` variable activates a hack that inserts a section with search
    # suggestions. I might add actual suggestions from the WordNik API sometime
     
    def tableview_number_of_sections(self, tableview):
        '''When there's a query, this returns an extra section for search 
        Suggestions.
        '''
        if self._query:
            return 3
        else:
            return 2
        
    def tableview_title_for_header(self, tableview, section):
        '''When there's a query, this returns an extra section for search 
        Suggestions.
        '''
        headers = ['Words with notes', 'Words from history']
        if self._query:
            headers.insert(0, '')
        return headers[section]
        
    def tableview_number_of_rows(self, tableview, section):
        '''When there's a query, this returns an extra row for search 
        Suggestions. 
        '''
        if self._query and section == 0:
            return 1
        elif self._query:
            # The extra section doesn't exist in the data, so we delete it 
            # before calling other methods
            section -= 1
        return self.count_words(section)

    def tableview_cell_for_row(self, tableview, section, row):
        if self._query and section == 0 and row == 0:
            # Adds a special table cell for search suggestions
            cell = ui.TableViewCell('value1')
            cell.text_label.text = self._query
            detail = 'Look up “' + self._query + '”'
            cell.detail_text_label.text = detail
            cell.image_view.image = ui.Image.named('iob:ios7_search_24')
            cell.accessory_type = 'disclosure_indicator'
            return cell
        elif self._query:
            # The extra section doesn't exist in the data, so we delete it 
            # before calling other methods
            section -= 1
        cell = ui.TableViewCell()
        cell.text_label.text = self.list_words(section=section)[row]
        if section == 0:
            img = 'iob:document_text_24'
        elif section == 1:
            img = 'iob:ios7_clock_outline_24'
        cell.image_view.image = ui.Image.named(img)
        cell.accessory_type = 'disclosure_indicator'
        return cell
    
    def tableview_can_delete(self, tableview, section, row):
        if self._query and section == 0:  # Can't delete suggestions
            return False
        else:
            return True
        
    def tableview_delete(self, tableview, section, row):
        s = section
        if self._query:
            # The extra section doesn't exist in the data, so we delete it 
            # before calling other methods
            s -= 1
        self.delete_word(s, self.list_words(section=s)[row])
        tableview.delete_rows([(row, section)])
    
    def tableview_delete_multiple(self, tableview):
        '''This isn't a regular tableview method. It's only called by the 
        action_delete function. I might rewrite this because it's kind of ugly.
        '''
        rows = tableview.selected_rows
        for row in rows:
            s = row[0]
            if self._query:
                s -= 1
            word = self.list_words(section=s)[row[1]]
            self.delete_word(s, word)
        # `tableview.delete_rows` uses backwards tuples. This fixes it.
        # https://forum.omz-software.com/topic/2733/delete-rows-in-tableview/6
        backwards_rows = []
        for row in rows:
            backwards_rows.append((row[1], row[0]))
        tableview.delete_rows(backwards_rows)
        console.hud_alert('Deleted %s word(s).' % len(rows))
