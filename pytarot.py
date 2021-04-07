"""Launch Tk GUI for a Tarot card reading."""

# File: pytarot.py. Author: Joe Lewis-Bowen. Updated: 2021-04-07.

# Usage: pythonw pytarot.py; or: r-click 'Open with' pythonw.exe

# NB: needs to be run in the same folder as pytarot_cards.csv.

# History: 2020-11-28: First step getting GUI layout working, 
#   stubs for functions, tips: realpython.com/python-gui-tkinter/ etc.
# 2020-11-29: Add spread choice drop-down, stub save to .csv on exit.
# 2020-11-30: Load card keywords from file to deck, shuffle, text to canvas.
# 2020-12-01: Refine layout, start help popup, progress .csv save.
# 2020-12-16: Debug: layout (Canvas size, padding), reading notes.
# 2021-04-07: Update license comment for GPL on GitHub; simple help popup.

# Copyright: 2020, 2021 Joe Lewis-Bowen <https://github.com/Loosebone/>.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# IMPORTS

# Use csv.DictReader for deck of cards, plain .Writer to save log.
import csv

# Use os.path.dirname() to find current folder for default save location.
import os

# Need to randomly shuffle the deck and reverse some cards.
import random

# Use sys.exit() to quit the application, called after tk's destroy().
import sys

# Use time.sleep() to add dramatic pauses; will format datetime string too.
import time

# Need Tk for the GUI, with standard dialogue boxes (but not font);
# font tips for canvas: stackoverflow.com/questions/43500149 (OS specific?).
import tkinter as tk
from tkinter import filedialog, simpledialog, font as tkfont


# CONFIGURATION

# Tags to indicate help text line format - no formatting yet.
TXT_HELP = """Please enjoy PyTarot, inspired by druidry.org.

This digital computer program simulates the esoteric practice of reading the
Tarot. A deck of 78 playing cards (which includes 4 suits of 14 cards and 22
trump or major arcana cards) is described in a file on your computer. This
deck is shuffled according to the date and time of the reading, as well as a
short sentence for your query. The cards are then dealt using the chosen
spread for your reading. Notes indicate the significance of each card, by its
position in the spread and by keywords for its associated meanings. You may
click on the cards to add additional notes, then save the reading to a file
when you quit the program.

Tarot readings can give insight into events in your life and your attitudes
about them. Whilst readings may tell stories that indicate possible future
paths, they do not predict what will happen and do not rely on supernatural
forces. However, the practice of divination for inspiration is compatible with
a nature-based spirituality such as Druidry, as taught by the Order of Bards,
Ovates and Druids (OBOD) at https://druidry.org. Have fun, and remember to be
kind to yourself and others!"""

# Spread lists card positions on notional grid; also define key phrases.
# TODO: add: my 5 card orientation spread, 6 card triangle, 12 card square?
SPREAD_DEFN = {
    '3 Card Simple Quick' : [
        (0, 1.5, "1. Past"),
        (1.5, 1.5, "2. Present"),
        (3, 1.5, "3. Future")],
    '10 Card Celtic Cross': [
        (1, 1, "1. Situation's heart, atmosphere"),
        (1, 2, '2. Crossing challenges'),
        (1, 0, '3. Crowning ideal or goal'),
        (1, 3, '4. Root foundation'),
        (0, 1.5, '5. Past influence'),
        (2, 1.5, '6. Near future'),
        (3, 3, '7. Attitude facing concerns'),
        (3, 2, "8. Environment's effects"),
        (3, 1, '9. Deep desires, fears'),
        (3, 0, '10. Culmination, outcome')]}
# Also set spread selection drop-down list order and default option.
# (Don't like repeating spread names but easier than fixing .keys sorted.)
SPREAD_OPTION = ['3 Card Simple Quick', '10 Card Celtic Cross']
SPREAD_DEFAULT = '10 Card Celtic Cross'

# Hardcoded local filename to read card definitions from.
CARD_FILE = 'pytarot_cards.csv'
# Configure pause when shuffle and between dealing cards (in seconds).
DEAL_PAUSE = 1 #5
# Equal chance of card reversal for random number of cards in range given;
# assume: MAX_REV <= number of cards in deck.
MIN_REV, MAX_REV = 0, 39
# Might want to change reversed indicator e.g. to "Rev" or use lowercase.
REV_WORD = 'Reversed'

# Global constants for GUI geometry: button character width;
BTN_WIDTH = 12
BTN_SQUEEZE = 18
# canvas dimensions on 4*4 grid of notional cells to place cards/ text on;
CELL_SZ = [240, 150]
CELL_PAD = 10
CNV_SZ = [4 * i_sz for i_sz in CELL_SZ]
# Canvas size 960x600 appears as 1440x900 - Windows 10 Display 150% scaling;
# see stackoverflow.com/questions/61150615/ (can fix DPI awareness),
# check difference e.g. for card image in Photos app vs Paint (unscaled).

# font height to use for added lines' y-axis pixel offset from previous.
#FONT_HEIGHT = 12


# UTILITY FUNCTIONS

def datetime_str():
    """Return a string with date and time almost in ISO 8601 form."""
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))


# CLASS DEFINITIONS

class TrCard:
    """Tarot card structure for name and divinatory keywords."""

    def __init__(self, cnm='', ccd='', kwu='', kwr =''):
        """Create a card from strings for name and keywords."""
        self.card_name = cnm
        self.card_code = ccd
        self.keywd_up = kwu
        self.keywd_rev = kwr
        # By default card is upright (shuffling may change this).
        self.is_rev = False
        # Cards may have a (x,y) coordinate spread position defined.
        self.min_coord = (None, None)
        self.max_coord = (None, None)
        # May also have notes for the reading filled in by user.
        self.rdg_note = ''


    def __str__(self):
        """String for a card is its name, maybe noted as reversed."""
        if self.is_rev:
            return '%s %s' % (self.card_name, REV_WORD)
        else:
            return self.card_name


class TrDeck:
    """Tarot deck operations on a list of TrCard objects."""

    def __init__(self):
        """Create an empty deck."""
        # The deck is just an array of TrCard instances.
        self.deck = []
        print('TrDeck() constructor called.')


    def fill_deck(self, file_name):
        """Reads a deck of divinatory cards'  definitions from a CSV file."""
        # Construct TrCard from .csv rows; fix issue of hidden characters
        # Excel UTF-8 save tip: stackoverflow.com/questions/49543139/.
        with open(file_name, newline='', encoding='utf-8-sig') as file_deck:
            rdr_deck = csv.DictReader(file_deck)
            for i_row in rdr_deck:
                #if self.deck == []:
                #    print('TrDeck csv header: %s' % (i_row.keys()))
                i_card = TrCard(cnm=i_row['Card'], ccd=i_row['Code'],
                    kwu=i_row['Keyword'], kwr=i_row['Reversed'])
                self.deck.append(i_card)
        print('TrDeck.fill_deck() read %d cards.' % (len(self.deck)))


    def shuffle(self, qry_hash):
        """Shuffle the deck with a query string as the random seed."""
        # Default seed v2 can take string, needn't hash to int first.
        random.seed(qry_hash)
        # Equal chance distrbution over range inclusive of min and max.
        n_rev = random.randint(MIN_REV, MAX_REV)

        # Shuffle initial ordered deck, reverse cards from top, reshuffle.
        random.shuffle(self.deck)
        for i_card in range(n_rev):
            # If card already reversed, will become upright.
            self.deck[i_card].is_rev = not self.deck[i_card].is_rev
        random.shuffle(self.deck)
        print('TrDeck.shuffle() query: "%s"; reversed: %d cards.' %
            (qry_hash, n_rev))


class TrSpread(TrDeck):
    """Card spread specialises Deck for subset of dealt cards."""

    def __init__(self, spnm=''):
        # Make sure Deck array of cards is set up.
        TrDeck.__init__(self)
        # Only other attribute of the spread is it's name (set later).
        self.sprd_name = spnm
        print('TrSpread() constructor called.')


    def add_card(self, ref_card, min_x, min_y, max_x, max_y):
        """Add details of a card to the list for this spread."""
        self.deck.append(ref_card)
        ref_card.min_coord = (min_x, min_y)
        ref_card.max_coord = (max_x, max_y)
        print('TrSpread.add_card() added %s.' % (ref_card))


class WinTr(tk.Frame):
    """GUI application window to display and perform reading."""

    def __init__(self, master=None):
        """Create deck, then GUI's buttons and display area."""
        # Attributes for shuffled cards, user entered query, formatted date.
        self.tr_deck = TrDeck()
        self.tr_deck.fill_deck(CARD_FILE)
        # Don't fill in default query - e.g. "What's going on?"
        self.tr_qry = ''
        self.tr_datetime = datetime_str()
        # Will fill a spread with cards too, save index of one clicked on.
        self.tr_sprd = TrSpread(SPREAD_DEFAULT)
        self.at_card_ix = None

        # Tkinter basics: call parent constructor, set title and layout:
        # a row of horizontal buttons over a canvas frame (spans all columns).
        tk.Frame.__init__(self, master)
        self.master = master
        master.title('Tarot Reading')
        self.grid()
        # Can only define font styles to use once Tkinter initialised.
        #print('Fonts: %s' % (tkfont.families()))
        self.font_defn = {
            'plain': tkfont.Font(family='System', size=10, weight='normal'),
            'bold': tkfont.Font(family='System', size=10, weight='bold')}
        # Also now define StingVar for spread entry and a popup's card notes.
        self.strv_sprd = tk.StringVar(self, SPREAD_DEFAULT)
        self.strv_note = tk.StringVar(self, '')

        # Leftmost GUI widget to pack is spread select drop-down (with label);
        # tips: stackoverflow.com/questions/45441885 (also /6178153 for colour);
        # geekforgeeks.org tkinter stringvar (will .get() later).
        self.lbl_sprd = tk.Label(self, text='Select Spread:',
            justify=tk.RIGHT, padx=2, pady=2)
        self.lbl_sprd.grid(column=1, row=0)
        # Need to unpack config list to arguments with * operation.
        self.opm_sprd = tk.OptionMenu(self, self.strv_sprd, *SPREAD_OPTION)
        self.opm_sprd.config(bg='WHITE')
        self.opm_sprd['menu'].config(bg='WHITE')
        self.opm_sprd.grid(column=2, row=0)

        # Command buttons go along top of window in order used;
        # button options: www.tutorialspoint.com/python/tk_button.htm.
        self.btn_query = tk.Button(self, text='Enter Query', padx=2, pady=2,
            width=BTN_WIDTH, command=self.prompt_qry)
        self.btn_query.grid(column=3, row=0)
        # Trick to call class method with argument to be defined later:
        # stackoverflow.com/questions/6920302 - use a lambda.
        self.btn_shuffle = tk.Button(self, text='Shuffle', padx=2, pady=2,
            width=BTN_WIDTH, command=self.popup_shuffle)
            # command=lambda: self.tr_deck.shuffle(self.tr_qry))
        self.btn_shuffle.grid(column=4, row=0)
        self.btn_spread = tk.Button(self, text='Deal Cards', padx=2, pady=2,
            width=BTN_WIDTH, command=self.show_spread)
        self.btn_spread.grid(column=5, row=0)
        # Save button disabled initially, update after dealt cards; tip:
        # stackoverflow.com/questions/16046743 (using tk const for states).
        self.btn_quit = tk.Button(self, text='Save & Close', padx=2, pady=2,
            state=tk.DISABLED, width=BTN_WIDTH, command=self.prompt_quit)
        self.btn_quit.grid(column=6, row=0)
        self.btn_help = tk.Button(self, text='Help', padx=2, pady=2,
            width=BTN_WIDTH, command=self.popup_help)
        self.btn_help.grid(column=7, row=0)

        # Empty padding labels left and right squeeze buttons to centre.
        self.lbl_lpad = tk.Label(self, text=' ', width=BTN_SQUEEZE)
        self.lbl_lpad.grid(column=0, row=0)
        self.lbl_rpad = tk.Label(self, text=' ', width=BTN_SQUEEZE)
        self.lbl_rpad.grid(column=8, row=0)
        # Canvas area notional 4x4 grid, cells 120x240 px, from config.
        print('WinTr() creating canvas size (%d, %d)' % (CNV_SZ[0], CNV_SZ[1]))
        self.cnv_spread = tk.Canvas(self, width=CNV_SZ[0], height=CNV_SZ[1], 
            bg='#ffff80')
        # Need to notice clicks on canvas; tip: stackoverflow.com 29211794.
        self.cnv_spread.bind('<Button-1>', self.on_click)
        self.cnv_spread.grid(columnspan=9, row=1)


    def on_click(self, event):
        """Check mouse button click on canvas to add card notes."""
        #print('WinTr.on_click() at (%d, %d).' % (event.x, event.y))
        # Want to check if click on a card's display area.
        for i_card_ix in range(len(self.tr_sprd.deck)):
            i_card = self.tr_sprd.deck[i_card_ix]
            # Assume cards don't overlap, possible only find True once.
            min_x, min_y = i_card.min_coord
            max_x, max_y = i_card.max_coord
            if event.x > min_x and event.x < max_x and \
                event.y > min_y and event.y < max_y:
                #print('WinTr.on_click() on card %s' % (i_card))
                # Set reading notes for card at this index in dialogue window.
                self.at_card_ix = i_card_ix
                self.popup_card_note()


    def popup_card_note(self):
        """Show dialogue window to get notes for card."""
        # Get ref to card at the spread's index clicked.
        at_card = self.tr_sprd.deck[self.at_card_ix]
        # Popup window as for shuffle, with text input box.
        self.pop_note = tk.Toplevel()
        self.pop_note.wm_title('Tarot Card Notes')
        
        # Minimum widget details: card name label and a text entry box.
        # (Help on padding: www.plus2net.com/python/tkinter-grid.php.)
        lbl_card_nm = tk.Label(self.pop_note, padx=CELL_PAD, pady=CELL_PAD,
            text=at_card.card_name)
        lbl_card_nm.grid(column=1, row=1, padx=CELL_PAD, pady=CELL_PAD)
        # Entry options: www.tutorialspoint.com/python/tk_entry.htm.
        ent_card_note = tk.Entry(self.pop_note,
            textvariable=self.strv_note, width=40)
        ent_card_note.grid(column=1, row=2)
        # Need a callback to read what user put in strv_note when close.
        btn_note_close = tk.Button(self.pop_note, 
            command=self.popup_note_close, 
            text='OK', width=BTN_WIDTH)
        btn_note_close.grid(column=1, row=3, padx=CELL_PAD, pady=CELL_PAD)

        # Use empty labels on grid for padding as on popup_shuffle().
        lbl_pad_left = tk.Label(self.pop_note, text='', width=2)
        lbl_pad_left.grid(row=1, rowspan=3, column=0)
        lbl_pad_right = tk.Label(self.pop_note, text='', width=2)
        lbl_pad_right.grid(row=1, rowspan=3, column=2)
        # TODO: fix this layout - it's still not good; 
        # NB: on close, write text on canvas; also save notes to CSV.
    
    
    def popup_help(self):
        """Show dialogue window with simple help text."""
        # Want formatted text (in scrollable box) with dismiss button.
        pop_hlp = tk.Toplevel()
        pop_hlp.wm_title('Tarot Help')
        tx_hlp = tk.Text(pop_hlp, height=20, width=80)
        # , bg='#FFFFFF', padx=CELL_PAD, pady=CELL_PAD, wrap=tk.WORD
        tx_hlp.grid(row=1, column=1, padx=CELL_PAD, pady=CELL_PAD)
        tx_hlp.insert(tk.END, TXT_HELP)
        btn_close = tk.Button(pop_hlp, command=pop_hlp.destroy, 
            text='OK', width=BTN_WIDTH)
        btn_close.grid(column=1, row=2, padx=CELL_PAD, pady=CELL_PAD)


    def popup_note_close(self):
        """Save popup card note text and close that dialogue."""
        # Save text in Entry widget's strv_note to note of the card
        # at the index clicked on, then close the dialogue.
        self.tr_sprd.deck[self.at_card_ix].rdg_note = self.strv_note.get()
        print('popup_note_close() wrote to %s: %s' % 
            (self.tr_sprd.deck[self.at_card_ix], self.strv_note.get()))
        # Write note to canvas based on spread card's coords.
        at_x, at_y = self.tr_sprd.deck[self.at_card_ix].min_coord
        self.cnv_spread.create_text(at_x, at_y + (CELL_SZ[1] / 2), 
            anchor=tk.NW, fill='#60A060', justify=tk.LEFT, 
            text=self.strv_note.get(), width=CELL_SZ[0] - (2 * CELL_PAD))
        self.pop_note.destroy()
        self.update()

        
    def popup_shuffle(self):
        """Show dialogue window while shuffle the deck."""
        # Update the reading's datetime and prepare message.
        self.tr_datetime = time.strftime('%Y-%m-%d %H:%M:%S',
            time.localtime(time.time()))
        txt_out = 'Shuffling the deck today, now:\n%s\n\n\n' % self.tr_datetime
        txt_out += 'Please keep your query in mind:\n\n"%s"\n' % self.tr_qry

        # Popup window with label of reading's setup: query and datetime;
        # tip: stackoverflow.com/questions/41946222.
        pop_shfl = tk.Toplevel()
        pop_shfl.wm_title('Tarot Shuffling')

        # Use empty labels on grid for padding (vs padx, pady with relief).
        lbl_pad_top = tk.Label(pop_shfl, text='')
        lbl_pad_top.grid(row=0, columnspan=3)
        lbl_pad_left = tk.Label(pop_shfl, text='', width=2)
        lbl_pad_left.grid(row=1, column=0)
        lbl_pad_right = tk.Label(pop_shfl, text='', width=2)
        lbl_pad_right.grid(row=1, column=2)

        # Main message goes in a white text area (not justify=tk.LEFT).
        lbl_shfl = tk.Label(pop_shfl, text=txt_out, background='#FFFFFF',
            padx=CELL_PAD, pady=CELL_PAD, relief=tk.GROOVE,
            wraplength=CELL_SZ[0])
        lbl_shfl.grid(row=1, column=1)

        # Button to dismiss is disabled while app takes time to shuffle.
        btn_shfl = tk.Button(pop_shfl, text='Okay', state=tk.DISABLED,
            command=pop_shfl.destroy)
        btn_shfl.grid(row=2, column=1, padx=10, pady=10)
        pop_shfl.update()
        time.sleep(DEAL_PAUSE)
        # Actual shuffle seeded on query and datetime strings.
        self.tr_deck.shuffle(self.tr_qry+ self.tr_datetime)
        btn_shfl.config(state=tk.NORMAL)


    def prompt_qry(self):
        """Prompt user for a query (used as hashable string)."""
        # Learnt of simpledialog from: runestone.academy thinkcspy.
        print('WinTr.prompt_qry() stub called.')
        self.tr_qry = simpledialog.askstring('Input',
            'Please enter a short description of your query.', parent=self)


    def prompt_quit(self):
        """Prompt user to save reading to .csv file before exit."""
        print('WinTr.prompt_quit() stub called.')

        # Prompt to open file; tips: www.homeandlearn.uk/save-text-file.html.
        f_name = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(os.path.realpath(__file__)),
            title="Save to File",
            filetypes=(('CSV files', '*.csv'), ('All files', '*.*')))
        # If nothing sensible returned from the dialogue, don't proceed.
        if f_name == '':
            print('WinTr.prompt_quit() aborted, no file to save to.')
            return

        #f_handle = open(f_name, 'w')
        #f_handle.write('PyTarot test text save\n')
        #f_handle.write('%s,%s,%s' % (self.strv_sprd.get(), self.tr_datetime))
        #f_handle.close()
        with open(f_name, 'w', newline='', encoding='utf-8-sig') as f_handle:
            f_writer = csv.writer(f_handle)
            f_writer.writerow(['PyTarot reading', self.strv_sprd.get(),
                self.tr_datetime, self.tr_qry])
            for i_card in range(len(sprd_config)):
                f_row = [sprd_config[i_card][2]]
                f_row.append(self.tr_deck.deck[i_card].card_name)
                if self.tr_deck.deck[i_card].is_rev:
                    f_row[1] = f_row[1] + ' ' + REV_WORD
                f_writer.writerow(f_row)

        print('WinTr.prompt_quit() completed.')
        # Use right way to exit tk app, rather than sys.exit()?
        self.destroy()
        sys.exit()


    def show_spread(self):
        """Show reading with dealt cards on canvas layout."""
         # Clear canvas; tip: stackoverflow.com/questions/15839491
        self.cnv_spread.delete("all")
        # Force wordwrap on placed text max width; sentence spacing fixed.
        px_max_txt = CELL_SZ[0] - (2 * CELL_PAD)
        # Text line separation fixed - experiment find approx font height.
        px_line_gap = CELL_SZ[1] / 8

        # Iterate over chosen spread's list of card positions.
        sprd_config = SPREAD_DEFN[self.strv_sprd.get()]
        self.tr_sprd.sprd_name = self.strv_sprd.get()
        print('WinTr.show_spread() called for %s.' % (self.strv_sprd.get()))
        for i_card in range(len(sprd_config)):
            # Need to refresh screen between pauses - see tip:
            # stackoverflow.com/questions/30057844.
            self.update()
            time.sleep(DEAL_PAUSE)

            # Text placement by in cell's position and grid's cell size;
            # tips: anzeljg.github.io/rin2/book2/2405/docs/tkinter/.
            i_x = (sprd_config[i_card][0] * CELL_SZ[0]) + CELL_PAD
            i_y = (sprd_config[i_card][1] * CELL_SZ[1]) + CELL_PAD
            # Can record card in spread on these coords.
            self.tr_sprd.add_card(self.tr_deck.deck[i_card], i_x, i_y,
                i_x + CELL_SZ[0] - (2 * CELL_PAD),
                i_y + CELL_SZ[1] - (2 * CELL_PAD))

            # First line for spread's card position notes.
            i_txt = sprd_config[i_card][2]
            print('WinTr.show_spread() at (%d, %d): %s' % (i_x, i_y, i_txt))
            self.cnv_spread.create_text(i_x, i_y, text=i_txt, fill='#A060C0',
                anchor=tk.NW, justify=tk.LEFT, width=px_max_txt)

            # Next line for card name from indexed position in deck.
            i_y += px_line_gap
            i_txt = str(self.tr_deck.deck[i_card])
            self.cnv_spread.create_text(i_x, i_y, text=i_txt, fill='#000000',
                anchor=tk.NW, justify=tk.LEFT, width=px_max_txt)
                # try: font=self.font_emph) # tkfont.Font(weight='bold'))

            # Show card meaning for indexed card (may be reversed).
            i_y += px_line_gap
            i_txt = self.tr_deck.deck[i_card].keywd_up
            if self.tr_deck.deck[i_card].is_rev:
                i_txt = self.tr_deck.deck[i_card].keywd_rev
            self.cnv_spread.create_text(i_x, i_y, text=i_txt, fill='#60A0A0',
                anchor=tk.NW, justify=tk.LEFT, width=px_max_txt)

        # Now dealt the cards, can enable save button.
        self.btn_quit.config(state=tk.NORMAL)


# MAIN PROGRAM

# Construct GUI; had skipped defining root, let master default None;
# can then set app_gui.master.title here, but better to include within WinTr()?
# Example: www.codegrepper.com python tkinter code example.
root = tk.Tk()
app_gui = WinTr(root)
#app_gui.master.title('Tarot Reading')
app_gui.mainloop()
print('PyTarot completed.')
