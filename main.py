#!/usr/bin/env python3
# coding: utf-8
import ui
import dialogs
import console
# import appex
import webbrowser
from urllib.parse import urlparse, unquote
import json
from jinja2 import Environment, FileSystemLoader
from vocabulary import Vocabulary
import define
from config import *

# fix icloud sync issue

# ---- Functions & button actions
# When convenient, button actions are set in the UI designer and defined here.
# Some button actions are more useful when set and defined inside their view
# classes.


def load_word_view(word: str='', parent_view=None):
    '''If this is called from a view that's not the main view, the view needs
    to be passed in order to call the navigation view.
    '''
    if not parent_view:
        parent_view = main
    v = ui.load_view('word')
    v.load_word(word)
    parent_view.navigation_view.push_view(v)

    
def action_random(sender):
    load_word_view(vocab.random_word())


def export_notes_format(word, notes):
    '''Note: I might update this with more sofisticated markup.'''
    return '%s\n\n%s' % (word, notes)


def action_share_multiple(sender):
    table = sender.superview.superview['table']
    words = []
    for row in table.selected_rows:
        cell = vocab.tableview_cell_for_row(table, row[0], row[1])
        word = cell.text_label.text
        definition = vocab.get_notes(word)
        words.append(export_notes_format(word, definition))
    dialogs.share_text('\n\n----\n\n'.join(words))


def action_export(sender):
    vocab.save_json_file()
    console.open_in(VOCABULARY_FILE)


def action_import(sender):
    '''Note: This may need more advanced error handling.'''
    choice = console.alert('This will override your current data',
                           button1='Okay')
    if choice:
        f = dialogs.pick_document(types=['public.text'])
        try:
            vocab.load_json_file(f)
        except json.JSONDecodeError:
            dialogs.hud_alert('Invalid JSON file.', icon='error')
            return
        dialogs.hud_alert('Import was successful.')
        main['table'].reload()

              
def action_cancel(sender):
    search = sender.superview['search_field']
    search.text = ''
    search.delegate.textfield_did_change(search)
    search.end_editing()


def action_switch_search(sender):
    vocab.fulltext_toggle(bool(sender.selected_index))
    sender.superview['table'].reload()


def action_change_key(sender=None):
    try:
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    d = dialogs.text_dialog(title='WordNik.com API Key',
                            text=config.get('wordnik_api_key') or '')
    if d is not None:
        config['wordnik_api_key'] = d
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)
    define.check_wordnik_key()

# ---- The view classes


class LookupView(ui.View):
    def did_load(self):
        self['table'].data_source = vocab
        self['table'].delegate = TableViewDelegate()
        self['search_field'].delegate = SearchDelegate()
        self['toolbar']['delete'].action = self.button_delete
        about_img = ui.Image.named('iob:ios7_help_outline_24')
        about_button = ui.ButtonItem(image=about_img, action=self.button_about)
        edit_button = ui.ButtonItem(title='Edit', action=self.button_edit)
        self.right_button_items = [about_button]
        self.left_button_items = [edit_button]
        #self['search_field'].begin_editing()
    
    def button_about(self, sender):
        v = ui.load_view('about')
        self.navigation_view.push_view(v)
    
    def button_edit(self, sender):
        if self['table'].editing:
            self.end_editing()
        else:
            self.start_editing()
    
    def start_editing(self):
        self['table'].set_editing(True, True)
        self.left_button_items[0].title = 'Done'
    
    def end_editing(self):
        self['table'].set_editing(False, True)
        self['toolbar']['share'].enabled = False
        self['toolbar']['delete'].enabled = False
        self.left_button_items[0].title = 'Edit'
    
    def button_delete(self, sender):
        self['table'].data_source.tableview_delete_multiple(self['table'])
        self.button_edit(sender)


class WordView(ui.View):
    def did_load(self):
        self['webcontainer']['wordnik_def'].delegate = WebDelegate()
        self['textview'].delegate = TextViewDelegate()
        self['segmentedcontrol1'].action = self.button_switch_modes
        self['webcontainer']['open_safari'].action = self.button_open_in_safari
        share_img = ui.Image.named('iob:ios7_upload_outline_32')
        share_button = ui.ButtonItem(image=share_img, action=self.button_share)
        self.right_button_items = [share_button]
        
    def load_word(self, word: str):
        self['word'].text = word
        self['textview'].text = vocab.get_notes(word)
        if self['textview'].text:
            self['segmentedcontrol1'].selected_index = 0
        else:
            self['segmentedcontrol1'].selected_index = 1
        self.switch_modes()
        self.load_definition(word)
    
    @ui.in_background
    def load_definition(self, word: str):
        template = jinja2env.get_template('definition.html')
        d = define.define(word)
        html = template.render(**d)
        self['webcontainer']['wordnik_def'].load_html(html)
        if d['definitions'] and not vocab.get_notes(word):
            # only save the word to history if there are definitions for it
            vocab.set_word(word)
            main['table'].reload()
    
    def button_share(self, sender):
        '''Note: I might update this with more softisticated markup.'''
        options = ['Share Word', 'Share Word & Notes']
        d = dialogs.list_dialog(items=options)
        word = self['word'].text
        if d == options[0]:
            text = word
        elif d == options[1]:
            text = export_notes_format(word, self['textview'].text)
        else:  # no option was selected
            return
        dialogs.share_text(text)
    
    def button_open_in_safari(self, sender):
        word = self['word'].text
        webbrowser.get('safari').open('https://wordnik.com/words/' + word)
    
    def button_switch_modes(self, sender):
        self.switch_modes()
    
    def switch_modes(self):
        def switch_webview():
            self['textview'].end_editing()
            self['webcontainer'].alpha = 1.0
            self['textview'].alpha = 0.0
            
        def switch_textview():
            self['webcontainer'].alpha = 0.0
            self['textview'].alpha = 1.0
        
        animations = (switch_textview, switch_webview)
        index = self['segmentedcontrol1'].selected_index
        ui.animate(animations[index])


class AboutView(ui.View):
    def did_load(self):
        html = jinja2env.get_template('about.html')
        self['webview1'].load_html(html.render())
        self['webview1'].delegate = WebDelegate()
        self['imageview1'].image = ui.Image.named('wordnik_badge_a1.png')

# ---- View Delegates


class TableViewDelegate:
    def tableview_did_select(self, tableview, section, row):
        '''Either checks the row for editing or opens the word.
        Note: setting the `action` attribute in the UI designer would pass an
        empty ui.ListDataSource as the sender. This method fixes that.
        '''
        if tableview.editing:
            tableview.superview['toolbar']['delete'].enabled = True
            tableview.superview['toolbar']['share'].enabled = True
        else:
            item = vocab.tableview_cell_for_row(tableview,
                                                section, row)
            load_word_view(item.text_label.text)
                
    def tableview_did_deselect(self, tableview, section, row):
        if not tableview.selected_rows and tableview.editing:
            tableview.superview['toolbar']['delete'].enabled = False
            tableview.superview['toolbar']['share'].enabled = False


class WebDelegate:
    def webview_should_start_load(self, webview, url, nav_type):
        '''This handles the links in the definition WebView and about WebView.
        Links to suggested words will load in a fresh WordView.
        Links to external sites will load in Safari.
        There's one special rule for changing the API key.
        '''
        if nav_type == 'link_clicked':
            parsed_url = urlparse(url)
            if parsed_url.scheme == 'wordroom':
                wv = webview.superview.superview
                if parsed_url.netloc == 'word':
                    load_word_view(unquote(parsed_url.path[1:]), wv)
                elif parsed_url.netloc == '-change_key':
                    # This is one special condition for when define.define()
                    # returns a message asking to change an API key.
                    action_change_key()
                    wv.load_word(wv['word'].text)
                else:
                    print('unknown url:', parsed_url)
                    return False
            else:
                webbrowser.get('safari').open(url)
            return False
        else:
            return True


class TextViewDelegate:
    def textview_did_end_editing(self, textview):
        '''Saves the text'''
        word = textview.superview['word'].text
        definition = textview.text
        vocab.set_word(word, definition)
        main['table'].reload()


class SearchDelegate:
    def __init__(self):
        self._editing = False  # used to show/hide the "Cancel" button
        
    def textfield_did_change(self, textfield):
        vocab.set_query(textfield.text)
        if textfield.text.find('#') != -1:
            # Typing a #hashtag automaticaly activates fulltext search
            textfield.superview['segmentedcontrol1'].selected_index = 1
            action_switch_search(textfield.superview['segmentedcontrol1'])
        if not self._editing:
            # This is called just to activate the animation.
            self.textfield_did_end_editing(textfield)
        textfield.superview['table'].reload()

    def textfield_should_return(self, textfield):
        if textfield.text:
            load_word_view(textfield.text.strip())
        else:
            textfield.end_editing()
        return True

    def textfield_did_begin_editing(self, textfield):
        '''Animates the "Cancel" button'''
        self._editing = True
        cancel = textfield.superview['cancel']
        
        def animation():
            textfield.width -= cancel.width + 6
            cancel.x = main.width - cancel.width - 6
        if not textfield.text:
            ui.animate(animation)
            cancel.enabled = True
        
    def textfield_did_end_editing(self, textfield):
        '''Animates the "Cancel" button'''
        self._editing = False
        cancel = textfield.superview['cancel']
        
        def animation():
            textfield.width = main.width - 12
            cancel.x = main.width + 6
        if not textfield.text:
            ui.animate(animation)
            cancel.enabled = False


class ContainerView(ui.View):
    '''This view contains the navigation view so we can save our data. When a
    ui.NavigationView closes, `will_close` doesn't get called on any of the
    views inside it.
    '''
    def will_close(self):
        vocab.save_json_file()

if __name__ == '__main__':
    vocab = Vocabulary(data_file=VOCABULARY_FILE)
    jinja2env = Environment(loader=FileSystemLoader(HTML_TEMPLATE_DIR))
    main = ui.load_view('lookup')
    container = ContainerView(flex='WH')
    container.height = main.height
    container.width = main.width
    nav = ui.NavigationView(main, flex='WH')
    nav.height = main.height
    nav.width = main.width
    container.add_subview(nav)
    container.present('sheet', hide_title_bar=True)
    # if appex.is_running_extension():
    #    load_word_view(appex.get_text())
