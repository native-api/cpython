"""codecontext - display the block context above the edit window

Once code has scrolled off the top of a window, it can be difficult to
determine which block you are in.  This extension implements a pane at the top
of each IDLE edit window which provides block structure hints.  These hints are
the lines which contain the block opening keywords, e.g. 'if', for the
enclosing block.  The number of hint lines is determined by the maxlines
variable in the codecontext section of config-extensions.def. Lines which do
not open blocks are not shown in the context hints pane.

"""
import re
from sys import maxsize as INFINITY

import tkinter
from tkinter.constants import TOP, LEFT, X, W, SUNKEN

from idlelib.config import idleConf

BLOCKOPENERS = {"class", "def", "elif", "else", "except", "finally", "for",
                "if", "try", "while", "with", "async"}
UPDATEINTERVAL = 100 # millisec
FONTUPDATEINTERVAL = 1000 # millisec


def get_spaces_firstword(codeline, c=re.compile(r"^(\s*)(\w*)")):
    "Extract the beginning whitespace and first word from codeline."
    return c.match(codeline).groups()


def get_line_info(codeline):
    """Return tuple of (line indent value, codeline, block start keyword).

    The indentation of empty lines (or comment lines) is INFINITY.
    If the line does not start a block, the keyword value is False.
    """
    spaces, firstword = get_spaces_firstword(codeline)
    indent = len(spaces)
    if len(codeline) == indent or codeline[indent] == '#':
        indent = INFINITY
    opener = firstword in BLOCKOPENERS and firstword
    return indent, codeline, opener


class CodeContext:
    "Display block context above the edit window."

    bgcolor = "LightGray"
    fgcolor = "Black"

    def __init__(self, editwin):
        """Initialize settings for context block.

        editwin is the Editor window for the context block.
        self.text is the editor window text widget.
        self.textfont is the editor window font.

        self.label displays the code context text above the editor text.
          Initially None, it is toggled via <<toggle-code-context>>.
        self.topvisible is the number of the top text line displayed.
        self.info is a list of (line number, indent level, line text,
          block keyword) tuples for the block structure above topvisible.
          self.info[0] is initialized with a 'dummy' line which
          starts the toplevel 'block' of the module.

        self.t1 and self.t2 are two timer events on the editor text widget to
          monitor for changes to the context text or editor font.
        """
        self.editwin = editwin
        self.text = editwin.text
        self.textfont = self.text["font"]
        self.label = None
        self.topvisible = 1
        self.info = [(0, -1, "", False)]
        # Start two update cycles, one for context lines, one for font changes.
        self.t1 = self.text.after(UPDATEINTERVAL, self.timer_event)
        self.t2 = self.text.after(FONTUPDATEINTERVAL, self.font_timer_event)

    @classmethod
    def reload(cls):
        "Load class variables from config."
        cls.context_depth = idleConf.GetOption("extensions", "CodeContext",
                                       "maxlines", type="int", default=15)
##        cls.bgcolor = idleConf.GetOption("extensions", "CodeContext",
##                                     "bgcolor", type="str", default="LightGray")
##        cls.fgcolor = idleConf.GetOption("extensions", "CodeContext",
##                                     "fgcolor", type="str", default="Black")

    def __del__(self):
        "Cancel scheduled events."
        try:
            self.text.after_cancel(self.t1)
            self.text.after_cancel(self.t2)
        except:
            pass

    def toggle_code_context_event(self, event=None):
        """Toggle code context display.

        If self.label doesn't exist, create it to match the size of the editor
        window text (toggle on).  If it does exist, destroy it (toggle off).
        Return 'break' to complete the processing of the binding.
        """
        if not self.label:
            # Calculate the border width and horizontal padding required to
            # align the context with the text in the main Text widget.
            #
            # All values are passed through getint(), since some
            # values may be pixel objects, which can't simply be added to ints.
            widgets = self.editwin.text, self.editwin.text_frame
            # Calculate the required horizontal padding and border width.
            padx = 0
            border = 0
            for widget in widgets:
                padx += widget.tk.getint(widget.pack_info()['padx'])
                padx += widget.tk.getint(widget.cget('padx'))
                border += widget.tk.getint(widget.cget('border'))
            self.label = tkinter.Label(
                    self.editwin.top, text="",
                    anchor=W, justify=LEFT, font=self.textfont,
                    bg=self.bgcolor, fg=self.fgcolor,
                    width=1,  # Don't request more than we get.
                    padx=padx, border=border, relief=SUNKEN)
            # Pack the label widget before and above the text_frame widget,
            # thus ensuring that it will appear directly above text_frame.
            self.label.pack(side=TOP, fill=X, expand=False,
                            before=self.editwin.text_frame)
        else:
            self.label.destroy()
            self.label = None
        return "break"

    def get_context(self, new_topvisible, stopline=1, stopindent=0):
        """Return a list of block line tuples and the 'last' indent.

        The tuple fields are (linenum, indent, text, opener).
        The list represents header lines from new_topvisible back to
        stopline with successively shorter indents > stopindent.
        The list is returned ordered by line number.
        Last indent returned is the smallest indent observed.
        """
        assert stopline > 0
        lines = []
        # The indentation level we are currently in.
        lastindent = INFINITY
        # For a line to be interesting, it must begin with a block opening
        # keyword, and have less indentation than lastindent.
        for linenum in range(new_topvisible, stopline-1, -1):
            codeline = self.text.get(f'{linenum}.0', f'{linenum}.end')
            indent, text, opener = get_line_info(codeline)
            if indent < lastindent:
                lastindent = indent
                if opener in ("else", "elif"):
                    # Also show the if statement.
                    lastindent += 1
                if opener and linenum < new_topvisible and indent >= stopindent:
                    lines.append((linenum, indent, text, opener))
                if lastindent <= stopindent:
                    break
        lines.reverse()
        return lines, lastindent

    def update_code_context(self):
        """Update context information and lines visible in the context pane.

        No update is done if the text hasn't been scrolled.  If the text
        was scrolled, the lines that should be shown in the context will
        be retrieved and the label widget will be updated with the code,
        padded with blank lines so that the code appears on the bottom of
        the context label.
        """
        new_topvisible = int(self.text.index("@0,0").split('.')[0])
        if self.topvisible == new_topvisible:      # Haven't scrolled.
            return
        if self.topvisible < new_topvisible:       # Scroll down.
            lines, lastindent = self.get_context(new_topvisible,
                                                 self.topvisible)
            # Retain only context info applicable to the region
            # between topvisible and new_topvisible.
            while self.info[-1][1] >= lastindent:
                del self.info[-1]
        else:  # self.topvisible > new_topvisible: # Scroll up.
            stopindent = self.info[-1][1] + 1
            # Retain only context info associated
            # with lines above new_topvisible.
            while self.info[-1][0] >= new_topvisible:
                stopindent = self.info[-1][1]
                del self.info[-1]
            lines, lastindent = self.get_context(new_topvisible,
                                                 self.info[-1][0]+1,
                                                 stopindent)
        self.info.extend(lines)
        self.topvisible = new_topvisible
        # Last context_depth context lines.
        context_strings = [x[2] for x in self.info[-self.context_depth:]]
        showfirst = 0 if context_strings[0] else 1
        self.label["text"] = '\n'.join(context_strings[showfirst:])

    def timer_event(self):
        "Event on editor text widget triggered every UPDATEINTERVAL ms."
        if self.label:
            self.update_code_context()
        self.t1 = self.text.after(UPDATEINTERVAL, self.timer_event)

    def font_timer_event(self):
        "Event on editor text widget triggered every FONTUPDATEINTERVAL ms."
        newtextfont = self.text["font"]
        if self.label and newtextfont != self.textfont:
            self.textfont = newtextfont
            self.label["font"] = self.textfont
        self.t2 = self.text.after(FONTUPDATEINTERVAL, self.font_timer_event)


CodeContext.reload()


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main('idlelib.idle_test.test_codecontext', verbosity=2, exit=False)
