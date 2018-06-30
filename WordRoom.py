#!/usr/bin/env python3
"""This is the main WordRoom script.

It contains all of the UI views and actions.
"""
# coding: utf-8
import json
import webbrowser
from urllib.parse import urlparse, unquote
import ui
import dialogs
import console
# import appex
from jinja2 import Environment, FileSystemLoader
from vocabulary import Vocabulary
import define
from config import VOCABULARY_FILE, CONFIG_FILE, HTML_TEMPLATE_DIR

__author__ = 'John Jackson'
__copyright__ = 'Copyright 2018 John Jackson'
__license__ = 'MIT'
__version__ = '1.1'
__maintainer__ = "John Jackson"
__email__ = "jbpjackson@icloud.com"

# ---- Functions & button actions
# When convenient, button actions are set in the UI designer and defined here.
# Some button actions are more useful when set and defined inside their view
# classes.


def load_word_view(word=''):
    """Open a WordView."""
    if container.current_layout != 'compact':
        word_view.load_word(word)
        if container.current_layout == 'regular_narrow':
            ui.animate(container.hide_menu)
    else:
        compact_word_view.load_word(word)
        container.nav_column.push_view(compact_word_view)
    container.open_words = [word]


def action_random(sender):
    """Open a random word."""
    dialogs.hud_alert('Random word opened.')
    load_word_view(vocab.random_word())


def export_notes_format(word, notes):
    """Return a string with a given word and note for exporting.

    This might need more sofisticated markup.
    """
    return '%s\n\n%s' % (word, notes)


def action_share_multiple(sender):
    """Open the iOS share dialog to export selected words and notes."""
    table = sender.superview.superview['table']
    words = []
    for row in table.selected_rows:
        cell = vocab.tableview_cell_for_row(table, row[0], row[1])
        word = cell.text_label.text
        definition = vocab.get_notes(word)
        words.append(export_notes_format(word, definition))
    dialogs.share_text('\n\n----\n\n'.join(words))


def action_export(sender):
    """Open the iOS share dialog to send the vocabulary data file."""
    vocab.save_json_file()
    console.open_in(VOCABULARY_FILE)


def action_import(sender):
    """Import a new vocabulary file.

    This selects a file from the iOS file picker and replace the current
    vocabulary file with it.
    """
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
        lookup_view['table'].reload()


def action_cancel(sender):
    """Cancel the search. Used by the "cancel" button."""
    search = sender.superview['search_field']
    search.text = ''
    search.delegate.textfield_did_change(search)
    search.end_editing()


def action_switch_search(sender):
    """Switch between searching words and searching full-text notes."""
    vocab.fulltext_toggle = bool(sender.selected_index)
    sender.superview['table'].reload()


def action_change_key(sender=None):
    """Input the WordNik API key with a dialog box."""
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


def action_about(sender):
    """Open the "About" view."""
    about_view.present('sheet', hide_close_button=True)


# ---- The view classes


class LookupView(ui.View):
    """This is the view for the main word list and search interface.

    In compact mode, this view is the "home" view. In regular mode, it's the
    left column.
    """

    def did_load(self):
        """Initialize the buttons."""
        self['table'].data_source = vocab
        self['table'].delegate = TableViewDelegate()
        self['search_field'].delegate = SearchDelegate()
        self['editbar']['delete'].action = self.action_delete
        self['toolbar']['edit'].action = self.start_editing
        self['editbar']['done'].action = self.end_editing
        about_img = ui.Image.named('iob:ios7_help_24')
        about_button = ui.ButtonItem(image=about_img, action=action_about)
        self.right_button_items = [about_button]
        close_img = ui.Image.named('iob:close_round_24')
        close_button = ui.ButtonItem(image=close_img, action=self.action_close)
        self.left_button_items = [close_button]

    def action_close(self, sender):
        """Close the main view."""
        container.close()

    def start_editing(self, sender):
        """Set the table for editing and activate the editbar."""
        self['table'].set_editing(True, True)
        self['toolbar'].hidden = True
        self['editbar'].hidden = False
        self['editbar'].frame = self['toolbar'].frame

    def end_editing(self, sender):
        """End the table editing and hide the editbar."""
        self['table'].set_editing(False, True)
        self['editbar']['share'].enabled = False
        self['editbar']['delete'].enabled = False
        self['toolbar'].hidden = False
        self['editbar'].hidden = True

    def action_delete(self, sender):
        """Delete the selected rows."""
        vocab.tableview_delete_multiple(self['table'])


class WordView(ui.View):
    """This is the view for displaying notes and definitions.

    In compact mode, it's displayed in LookupView's NavigationView. In regular
    mode, it's displayed on the right column.
    """

    def did_load(self):
        """Initialize the buttons."""
        self['webcontainer']['html_definition'].delegate = WebDelegate()
        self['textview'].delegate = TextViewDelegate()
        self['segmentedcontrol1'].action = self.action_switch_modes
        self['webcontainer']['open_safari'].action = self.action_open_in_safari
        share_img = ui.Image.named('iob:ios7_upload_outline_32')
        share_button = ui.ButtonItem(image=share_img, action=self.action_share,
                                     enabled=False)
        lookup_img = ui.Image.named('iob:ios7_search_32')
        lookup_button = ui.ButtonItem(image=lookup_img,
                                      action=self.action_search)
        self.right_button_items = [share_button, lookup_button]
        self.add_subview(ui.load_view(('blank')))
        self['blank'].background_color = 'white'
        self['blank'].flex = 'WH'
        self['blank'].frame = self.frame

    def load_word(self, word: str):
        """Open a word."""
        if self['word'].text == word:
            return
        self['blank'].hidden = True
        self.right_button_items[0].enabled = True
        self['word'].text = word
        self['textview'].text = vocab.get_notes(word)
        if self['textview'].text:
            self['segmentedcontrol1'].selected_index = 0
        else:
            self['segmentedcontrol1'].selected_index = 1
            loading = jinja2env.get_template('loading.html').render()
            self['webcontainer']['html_definition'].load_html(loading)
        self.switch_modes()
        self.load_definition(word)

    def clear(self):
        """Clear the word data and display a placeholder "blank" view."""
        self['blank'].hidden = False
        self['word'].text = ''
        self['textview'].text = ''
        self['webcontainer']['html_definition'].load_html('')
        self.right_button_items[0].enabled = False
        container.open_words = []

    @ui.in_background
    def load_definition(self, word: str):
        """Fetch the definition of a word and render its HTML template."""
        template = jinja2env.get_template('definition.html')
        d = define.define(word)
        html = template.render(**d)
        self['webcontainer']['html_definition'].load_html(html)
        if d['definitions'] and not vocab.get_notes(word):
            # only save the word to history if there are definitions for it
            row = vocab.set_word(word)
            if row:
                lookup_view['table'].insert_rows([row])

    def action_share(self, sender):
        """Open the iOS share dialog to export a word or its notes."""
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

    def action_search(self, sender):
        """Open the search box on LookupView."""
        if container.current_layout == 'regular_narrow':
            ui.animate(container.show_menu)
        if container.current_layout == 'compact':
            for word in container.open_words:
                container.nav_column.pop_view()
        lookup_view['search_field'].begin_editing()

    def action_open_in_safari(self, sender):
        """Open a given word in WordNik."""
        word = self['word'].text
        webbrowser.get('safari').open('https://wordnik.com/words/' + word)

    def action_switch_modes(self, sender):
        """Switch modes. This is a wrapper for WordView.switch_modes()."""
        self.switch_modes()

    def switch_modes(self, animate=True):
        """Switch between viewing the notes and the definitions."""
        def switch_webview():
            self['textview'].end_editing()
            self['webcontainer'].alpha = 1.0
            self['textview'].alpha = 0.0

        def switch_textview():
            self['webcontainer'].alpha = 0.0
            self['textview'].alpha = 1.0

        animations = (switch_textview, switch_webview)
        index = self['segmentedcontrol1'].selected_index
        if animate:
            ui.animate(animations[index])
        else:
            animations[index]()


class AboutView(ui.View):
    """This is the view for the "about" view."""

    def did_load(self):
        """Initialize the buttons and HTML data."""
        html = jinja2env.get_template('about.html')
        self['webview1'].load_html(html.render())
        self['webview1'].delegate = WebDelegate()
        mode = ui.RENDERING_MODE_ORIGINAL
        img = ui.Image.named('wordnik_badge_a1.png').with_rendering_mode(mode)

        def action_wordnik(sender):
            webbrowser.get('safari').open('https://wordnik.com/')

        def action_close(sender):
            self.close()
        self['wn_logo'].image = img
        self['wn_logo'].action = action_wordnik
        self['wn_logo'].title = ''
        done_button = ui.ButtonItem(title='Done', action=action_close)
        self.right_button_items = [done_button]


class AdaptiveView(ui.View):
    """This view renders one or two columns depending on display size.

    This acts as a wrapper for two main views. It adapts to layout changes,
    such as putting an app in split-screen, and it rearranges the two views
    accordingly. It has two main modes: regular and compact. Regular is the
    "iPad" view. Compact is the "iPhone" view. (Although compact can be shown
    in split-screen on iPad.)
    """

    def __init__(self, nav_column, content_column):
        """Initialize the view with the two view columns."""
        # Putting content_column inside a NavigationView is a hack to make its
        # title bar visible. We never invoke the NavigationView methods.
        self.add_subview(nav_column)
        self.add_subview(ui.NavigationView(content_column))
        self.content_column = content_column
        self.nav_column = nav_column
        # open_words will probably always just have one item, but it's
        # technically possible to have more than one open.
        self.open_words = []
        self.current_layout = None
        # background color is used as a border between the columns.
        self.background_color = 'lightgrey'

    def layout(self):
        """Call when the layout changes."""
        # 678 is the width of an iPad pro app in 1/2 split mode.
        if self.width >= 678 and self.current_layout != 'regular':
            self.regular()
        elif self.width < 678 and self.current_layout != 'compact':
            self.compact()

    def compact(self):
        """Render the view in compact mode.

        This collapses open content into the left column's NavigationView.
        """
        nav, content = self.subviews
        nav.x = self.x
        nav.width = self.width
        nav.height = self.height
        nav.flex = 'WH'
        content.hidden = True
        for word in self.open_words:
            compact_word_view.load_word(word)
            nav.push_view(compact_word_view, False)
        self.current_layout = 'compact'

    def regular(self):
        """Render the view in regular, two-column mode."""
        nav, content = self.subviews
        nav.width = 320
        nav.height = self.height
        nav.flex = 'H'
        nav.x = self.x
        content.hidden = False
        content.flex = 'WHR'
        content.x = nav.width + 1
        content.width = self.width - nav.width - 1
        content.height = self.height
        if self.current_layout == 'compact':
            for word in self.open_words:
                nav.pop_view(False)
                self.content_column.load_word(word)
        self.content_column.left_button_items = []
        self.current_layout = 'regular'

    def regular_narrow(self):
        """Render a view halfway between regular and compact.

        This features a menu that slides out with a button. It's currently not
        implemented because I don't like the way it looks, and it doesn't
        completely work the way users would expect.
        """
        nav, content = self.subviews
        nav.width = 320
        nav.height = self.height
        nav.flex = 'H'
        nav.x = -nav.width
        content.hidden = False
        content.flex = 'WHR'
        content.x = self.x
        content.width = self.width
        content.height = self.height

        def toggle_menu(sender):
            if nav.x < self.x:
                ui.animate(self.show_menu)
            else:
                ui.animate(self.hide_menu)
        toggle_img = ui.Image.named('iob:navicon_32')
        toggle_button = ui.ButtonItem(image=toggle_img, action=toggle_menu)
        self.content_column.left_button_items = [toggle_button]
        if self.current_layout == 'compact':
            for word in self.open_words:
                nav.pop_view(False)
                self.content_column.load_word(word)
        if lookup_view['search_field'].delegate.is_editing:
            self.show_menu()
        self.current_layout = 'regular_narrow'

    def show_menu(self):
        """Show the menu in a regular_narrow view."""
        nav, content = self.subviews
        nav.x = self.x
        content.x = nav.width + 1

    def hide_menu(self):
        """Hide the menu in a regular_narrow view."""
        nav, content = self.subviews
        nav.x = -nav.width
        content.x = self.x
        lookup_view['search_field'].end_editing()

# ---- View Delegates


class TableViewDelegate:
    """The delegate class to handle the vocabulary table."""

    def tableview_did_select(self, tableview, section, row):
        """Call when the user selects a table row.

        For some reason, setting the `action` attribute in the UI designer
        passes an empty ui.ListDataSource as the sender. This method fixes it.
        """
        tableview.superview['search_field'].end_editing()
        if tableview.editing:
            tableview.superview['editbar']['delete'].enabled = True
            tableview.superview['editbar']['share'].enabled = True
        else:
            item = vocab.tableview_cell_for_row(tableview,
                                                section, row)
            load_word_view(item.text_label.text)

    def tableview_did_deselect(self, tableview, section, row):
        """Call when the user deselects a table row."""
        if not tableview.selected_rows and tableview.editing:
            tableview.superview['editbar']['delete'].enabled = False
            tableview.superview['editbar']['share'].enabled = False


class WebDelegate:
    """This is the delegate class for the WebViews."""

    def webview_should_start_load(self, webview, url, nav_type):
        """Call when the user taps a link.

        Links to suggested words will load in a fresh WordView.
        Links to external sites will load in Safari.
        There's one special rule for changing the API key.
        """
        if nav_type == 'link_clicked':
            parsed_url = urlparse(url)
            if parsed_url.scheme == 'wordroom':
                wv = webview.superview.superview
                if parsed_url.netloc == 'word':
                    wv.load_word(unquote(parsed_url.path[1:]))
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
    """This is the delegate class for the TextViews."""

    def textview_did_end_editing(self, textview):
        """Save text when user finishes editing."""
        word = textview.superview['word'].text
        notes = textview.text
        row = vocab.set_word(word, notes)
        if row:
            lookup_view['table'].insert_rows([row])
        row = vocab.del_dup_word(word, notes)
        if row:
            lookup_view['table'].delete_rows([row])


class SearchDelegate:
    """The delegate class for the search TextFields."""

    def __init__(self):
        """Init the class."""
        self.is_editing = False  # used to show/hide the "Cancel" button

    def textfield_did_change(self, textfield):
        """Search the vocabulary as the user types."""
        vocab.set_query(textfield.text)
        if textfield.text.find('#') != -1:
            # Typing a #hashtag automaticaly activates fulltext search
            textfield.superview['segmentedcontrol1'].selected_index = 1
            action_switch_search(textfield.superview['segmentedcontrol1'])
        if not self.is_editing:
            # This is called just to activate the animation.
            self.textfield_did_end_editing(textfield)
        textfield.superview['table'].reload()

    def textfield_should_return(self, textfield):
        """Search the vocabulary."""
        if textfield.text:
            load_word_view(textfield.text.strip())
        textfield.end_editing()
        return True

    def textfield_did_begin_editing(self, textfield):
        """Animate the "Cancel" button."""
        self.is_editing = True
        view = textfield.superview
        cancel = view['cancel']

        def animation():
            textfield.width -= cancel.width + 6
            cancel.x = view.width - cancel.width - 6
        if not textfield.text:
            ui.animate(animation)
            cancel.enabled = True

    def textfield_did_end_editing(self, textfield):
        """Animate the "Cancel" button."""
        self.is_editing = False
        view = textfield.superview
        cancel = view['cancel']

        def animation():
            textfield.width = view.width - 12
            cancel.x = view.width + 6
        if not textfield.text:
            ui.animate(animation)
            cancel.enabled = False


if __name__ == '__main__':
    vocab = Vocabulary(data_file=VOCABULARY_FILE)
    jinja2env = Environment(loader=FileSystemLoader(HTML_TEMPLATE_DIR))
    lookup_view = ui.load_view('lookup')
    nav_view = ui.NavigationView(lookup_view, flex='WH')
    word_view = ui.load_view('word')
    compact_word_view = ui.load_view('word')
    about_view = ui.load_view('about')
    container = AdaptiveView(nav_view, word_view)
    container.name = 'WordRoom'
    container.present('fullscreen', hide_title_bar=True)
    # if appex.is_running_extension():
    #    load_word_view(appex.get_text())
