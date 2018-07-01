#!/usr/bin/env python3
"""This module contains the Vocbulary class.

It's used as a data source for the main table.
"""
import json
import random
import ui


class Vocabulary:
    """The core class to process all of the word data.

    Data is stored as a list of dictionaries. In the future, this may change
    to something more robust like a SQL database.
    """

    def __init__(self, data_file: str):
        """Load the vocabulary from a given data file."""
        # _words[0] is words with notes. _words[1] is history
        self._words = [{}, {}]
        self._query = ''  # used for searching the list
        self.fulltext_toggle = False
        self.data_file = data_file
        self.load_json_file()

    def load_json_file(self, filename=''):
        """Load vocabulary data from the JSON file."""
        if not filename:
            filename = self.data_file
        try:
            with open(filename, 'r') as infile:
                self._words = json.load(infile)
        except FileNotFoundError:
            with open('default-' + filename, 'r') as infile:
                self._words = json.load(infile)

    def save_json_file(self, indent = None):
        """Save vocabulary data to the JSON file."""
        with open(self.data_file, 'w') as outfile:
            json.dump(self._words, outfile, indent=indent)

    def set_word(self, word: str, notes=''):
        """Add a word or updates the word if it already exists.

        After this, call `del_dup_word()`.

        Return either a tuple that can be passed to Table.insert_rows(), or
        return `None` if there is no row to insert.
        """
        word = word.strip()
        new_word = True
        if word and notes:  # adds to notes
            section = 0
        elif word:  # adds to history
            section = 1
        if word in self._words[section]:
            new_word = False
        self._words[section][word] = notes
        self.save_json_file()
        row = self.list_words(section).index(word)
        if self._query:
            section += 1
        if new_word:
            return row, section
        else:
            return None

    def del_dup_word(self, word: str, notes=''):
        """Delete any duplicate entries of a word in the wrong section.

        Call this after `set_word()`.
        Return a tuple that can be passed to TableView.delete_rows(), or
        return `None` if there is no row to delete.
        """
        word = word.strip()
        section = None
        row = None
        if notes and word in self._words[1]:
            # checks if the word has notes and is in history
            section = 1
            row = self.list_words(1).index(word)
        elif not notes and word in self._words[0]:
            # checks if a word without notes is in the notes section
            section = 0
            row = self.list_words(0).index(word)
        if section is not None:
            self.delete_word(section, word)
            if self._query:
                section += 1
            return row, section
        else:
            return None

    def get_notes(self, word: str):
        """Look up a word and return its notes.

        Words without notes return empty strings. This can be used to check if
        a word is in the personal dictionary or not.
        """
        word = word.strip()
        if word in self._words[0]:
            return self._words[0][word]
        else:
            return ''

    def set_query(self, query: str):
        """Set a string that filters `list_words()` output.

        To "unset" the query, just set an empty string.
        """
        self._query = query.strip()

    def _filter_query(self, word):
        hasdef = False
        if self.fulltext_toggle and word in self._words[0]:
            w = self._words[0][word].casefold()
            hasdef = w.find(self._query.casefold()) != -1
        wordbegins = word.casefold().startswith(self._query.casefold())
        return hasdef or wordbegins

    def count_words(self, section: int):
        """Return the number of words in a section."""
        return len(self.list_words(section))

    def list_words(self, section: int):
        """Return a list of words in a section."""
        if self._query:
            words = filter(self._filter_query, self._words[section].keys())
        else:
            words = self._words[section].keys()
        return sorted(words, key=lambda s: s.casefold())

    def delete_word(self, section: int, word: str):
        """Delete a word."""
        word = word.strip()
        del self._words[section][word]
        self.save_json_file()

    def delete_multiple(self, rows: list):
        """Call to delete several words at once.
        
        Returns an iterator of the words deleted.
        """
        # first we extract the words from the rows
        wordlist = []
        for row in rows:
            s = row[0]
            if self._query:
                s -= 1
            word = self.list_words(section=s)[row[1]]
            wordlist.append((s, word))
        # then we deleted them
        # it has to be a two-step process or else the indexes will be off
        for section, word in wordlist:
            del self._words[section][word]
        self.save_json_file()
        # Then we return the words
        return (x[1] for x in wordlist)

    def random_word(self):
        """Return a random word with notes."""
        return random.choice(list(self._words[0].keys()))

    # ---- Tableview methods
    # the `_query` variable activates a hack that inserts a section with search
    # suggestions. I might add actual suggestions from the WordNik API sometime

    def tableview_number_of_sections(self, tableview):
        """Return the number of sections."""
        if self._query:
            # when there's a query, we add a section for it.
            return 3
        else:
            return 2

    def tableview_title_for_header(self, tableview, section):
        """Return a title for the given section."""
        headers = ['Words with notes', 'Words from history']
        if self._query:
            # returns an extra section for search suggestions
            headers.insert(0, '')
        return headers[section]

    def tableview_number_of_rows(self, tableview, section):
        """Return the number of rows in the section."""
        if self._query and section == 0:
            # The search suggestions always have 1 row.
            return 1
        elif self._query:
            # The extra section doesn't exist in the data, so we delete it
            # before calling other methods
            section -= 1
        return self.count_words(section)

    def tableview_cell_for_row(self, tableview, section, row):
        """Create and return a cell for the given section/row."""
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
        """Return True if the user should be able to delete the given row."""
        if self._query and section == 0:  # Can't delete suggestions
            return False
        else:
            return True

    def tableview_delete(self, tableview, section, row):
        """Call when the user confirms deletion of the given row."""
        s = section
        if self._query:
            # The extra section doesn't exist in the data, so we delete it
            # before calling other methods
            s -= 1
        word = self.list_words(section=s)[row]
        self.delete_word(s, word)
        tableview.delete_rows([(row, section)])
        # This is a slightly hacky way to make sure that when the selected word
        # is deleted, it also gets cleared from the WordView
        wordview = tableview.superview.navigation_view.superview.content_column
        if wordview['word'].text == word:
            wordview.clear()
