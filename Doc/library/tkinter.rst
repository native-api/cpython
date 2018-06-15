:mod:`tkinter` --- Python interface to Tcl/Tk
=============================================

.. module:: tkinter
   :synopsis: Interface to Tcl/Tk for graphical user interfaces

.. moduleauthor:: Guido van Rossum <guido@Python.org>

**Source code:** :source:`Lib/tkinter/__init__.py`

--------------

The :mod:`tkinter` package ("Tk interface") is the standard Python interface to
the Tcl/Tk GUI toolkit. Tcl/Tk and Tkinter are available on most Unix
platforms, including macOS, as well as on Windows systems.

Running ``python -m tkinter`` from the command line should open a window
demonstrating a simple Tk interface, letting you know that Tkinter is
properly installed on your system, and also showing what version of Tcl/Tk is
installed, so you can read the Tcl/Tk documentation specific to that version.

Tkinter supports a range of Tcl/Tk versions, built either with or
without thread support. The official Python binary release bundles Tcl/Tk 8.6
threaded. See the source code for the :mod:`_tkinter` module
for more information about supported versions.

Tkinter is not a thin wrapper, but adds a fair amount of its own logic to
make the experience more pythonic. This documentation will concentrate on these
additions and changes, and refer to the official Tcl/Tk documentation for
details that are unchanged.


Architecture
------------

Tcl/Tk is not a single library but rather consists of a few distinct
modules, each with a separate functionality and its own official
documentation. Python's binary releases also ship an add-on module
together with it.

Tcl
   Tcl is a dynamic interpreted programming language, just like Python. Though
   it can be used on its own as a general-purpose programming language, it is
   most commonly embedded into C applications as a scripting engine or an
   interface to the Tk toolkit. The Tcl library has a C interface to
   create and manage one or more instances of a Tcl interpreter, run Tcl
   commands and scripts in those instances, and add custom commands
   implemented in either Tcl or C. Each interpreter has an event queue,
   and there are facilities to send events to it and process them.
   Tcl's execution model is very different from Python, and Tkinter bridges
   this difference (see `Threading model`_ for details).

   Each :class:`Tk` object embeds its own Tcl interpreter instance.
   
   Though :mod:`_tkinter` allows to execute entire Tcl scripts, Python
   bindings typically only run a single command at a time.


Tk
   Tk is a Tcl package implemented in C that adds custom commands to create and
   manipulate GUI widgets. The interpreter's event queue is used to generate
   and process GUI events for all widgets created by it.
   Tk also has its own C interface.

   Tcl can be used without Tk (and Tk needs to be explicitly loaded to make it
   available; Tkinter does this automatically), though they are
   typically provided together, and "Tcl/Tk" is the name for the bundle.

   Since version 8.5, Tk also implements the
   `Themed Tk (Ttk) <https://www.tcl.tk/man/tcl8.6/TkCmd/ttk_intro.htm>`_
   family of widgets. They feature much better, consistent and native look
   across different platforms.
   Ttk widgets are recommended for use in new code, with their regular
   counterparts mostly reserved for legacy code and special cases.

Tix
   `Tix <https://core.tcl.tk/jenglish/gutter/packages/tix.html>`_ is an older
   third-party Tcl package, an add-on for Tk that adds several new widgets.
   It's deprecated in favor of Ttk.


Tkinter Modules
^^^^^^^^^^^^^^^

:mod:`tkinter` has the core functionality and bindings for regular Tk
widgets.

:mod:`tkinter.ttk` has bindings for Themed Tk (Ttk) widgets, and
:mod:`tkinter.tix` for ones from the Tix add-on.

:mod:`_tkinter` is a C module that directly interfaces with Tcl/Tk via their C
interface. It's not supposed to be called directly by user code
save for a few functions.

Threading model
---------------

Tkinter strives to allow any calls to its API from any Python threads, without
any limitations, as expected from a Python module. Due to Tcl's architectural
restrictions, however, that stem from its vastly different threading model, this is not always possible.

Tcl's execution model is based on cooperative multitasking. Control is passed
between multiple interpreter instances by sending events (see `event-oriented
programming -- Tcl/Tk wiki <https://wiki.tcl.tk/1772>`_ for details).

A Tcl interpreter instance has only one stream of execution and, unlike many
other GUI toolkits, Tcl/Tk doesn't provide a blocking event loop. Instead, Tcl
code is supposed to pump the event queue by hand at strategic moments (save for
events that are generated explicitly in the same OS thread -- these are handled
immediately by simply passing control from sender to the handler). As such, all
Tcl commands are designed to work without an event loop running -- only the
event handlers will not fire until the queue is processed.

In multithreaded environments like Python, the common GUI execution model is
rather to use a blocking event loop and a dedicated OS thread (called the "UI
thread") to run it constantly. Usually, the main thread does this after doing
the initialization. Other threads send work items (events) to its event queue
when they need to do something in the GUI. Likewise, for any lengthy tasks, the
UI thread can launch worker threads that report back on their progress via the
same event queue.

Tkinter implements the multithreaded model as the primary one, but it supports
pumping events by hand instead of running the event loop, too.

Contrary to most GUI toolkits using the multithreaded model, Tkinter calls can
be made from any threads -- even worker threads. Conceptually, this can be seen
as the worker thread sending an event referencing an appropriate payload, and
waiting for its processing. The implementation, however, can sometimes take a
shortcut here.

* In threaded Tcl, an interpreter instance, when created, becomes tied to the
  creating OS thread. Any calls to this interpreter must come from this thread
  (apart from special inter-thread communication APIs). The upside is that
  calls to interpreters tied to different threads can run in parallel. Tkinter
  implements calls from outside the interpreter thread by constructing an event
  with an appropriate payload, sending it to the instance's queue via the
  inter-thread communication APIs and waiting for result. As a consequence:

  * To make any calls from outside the interpreter thread, :func:`Tk.mainloop`
    must be running in the interpreter thread. If it isn't, :class:`RuntimeError`
    is raised.

  * A few select functions can only be run in the interpreter thread.
    These are the functions that implement the event loop -- :func:`Tk.mainloop`,
    :func:`Tk.dooneevent`, :func:`Tk.update`, :func:`Tk.update_idletasks` --
    and :func:`Tk.loadTk` and :func:`Tk.destroy` that initialize and finalize Tk.

* For non-threaded Tcl, threads effectively don't exist. So, any Tkinter call is
  carried out in the calling thread, whatever it happens to be (see
  :func:`Tk.mainloop`'s entry on how it is implemented in this case). Since Tcl
  has a single stream of execution, all Tkinter calls are wrapped with a global
  lock to enforce sequential access. So, in this case, there are no restrictions
  on calls whatsoever, but only one call, to any interpreter, can be active at a
  time.

The last thing to note is that Tcl event queues are not per-interpreter but
rather per-thread. So, a running event loop will process events not only for its
own interpreter, but also for any others that share the same queue. This is
transparent for the code though because an event handler is invoked within the
context of the correct interpreter (and in the correct Python lexical context if
the handler has a Python payload). There's also no harm in trying to run an
event loop for two interpreters that may happen to share a queue: in threaded
Tcl, such a clash is flat-out impossible because they would have to both run in
the same OS thread, and in non-threaded Tcl, they would take turns processing
events.



Module contents
---------------


.. attribute:: TclVersion
.. attribute:: TkVersion

   Tcl and Tk library versions used, as floating-point numbers


.. function:: Tcl(screenName=None, baseName=None, className='Tk', useTk=0)

   A factory function which creates an instance of the :class:`Tk` class,
   except that it sets `useTk` to `0` by default, thus not initializing Tk
   and not creating the root window.
   This is useful for driving a Tcl interpreter when one doesn't want
   to create extraneous toplevel windows, or cannot
   (such as Unix/Linux systems without an X server).  The created object
   can have Tk initialized at a later time
   by calling its :meth:`Tk.loadtk`.
   
   All arguments are the same as in :class:`Tk` constructor.


.. class:: TclError

   An exception raised for an error returned by a Tcl interpreter.


.. attribute:: wantobjects = 1

   Whether Tcl call results in new Tk objects should be converted from Tcl
   types to Python types. An integer; any nonzero value means "true".
   If not set, string representations of Tcl objects are returned instead.


.. attribute:: READABLE
.. attribute:: WRITABLE
.. attribute:: EXCEPTION

   Constants used for the *mask* parameter of :func:`createfilehandler`.


.. class:: EventType

   A enumeration of known
   `Tk event types <https://www.tcl.tk/man/tcl8.6/TkCmd/bind.htm#M7>`_,
   used for :attr:`Event`'s *type* attribute.


.. class:: Event

   Container for the properties of a Tcl event.

   If a callback function is registered using :func:`bind`,
   :func:`bind_all`, :func:`bind_class`, or :func:`tag_bind`,
   the callback is called with an :class:`Event` as the first argument.

   Will have the same fields as the corresponding
   `Tk event <https://www.tcl.tk/man/tcl8.6/TkCmd/event.htm#M9>`_
   plus a *type* field that will contain an :class:`EventType`
   or a string with a number as returned by Tcl if the event type is unknown.


.. _default-root:   
   
.. function:: NoDefaultRoot()

   Unset the current default root window and do not use newly-created
   :class:`Tk` instances to set it.

   By default, when a :class:`Tk` instance has its root window created
   when the default root is unset, it becomes the default root,
   and stays it until it's destroyed.
   Whenever a :class:`Widget` or other entity that requires a parent/master
   widget is created without specifying one, the default root is used.
   If the default root is not set, such a call will fail.


Bound variables
^^^^^^^^^^^^^^^

Most Tk widgets can be *bound* to a global Tcl variable
by setting its `textvariable <https://tcl.tk/man/tcl8.6/TkCmd/options.htm#M-textvariable>`_
option (or another option for some widgets).
Then any change to the information in the widget will update the variable,
and vice versa.

   
.. class:: Variable(master=None, value=None, name=None)

   Base class that wraps a Tcl global variable of an arbitrary type.
   
   No processing is done on get and set values except the usual
   :ref:`tcl types` convertion.
   
   *master* is a :class:`Tk` or :class:`Widget` that specifies which Tcl interpreter
   instance to create the variable in. If omitted, the
   :ref:`default root <default-root>` is used.
   
   *value* is an optional initial value. If not, an empty string is used.
   
   *name* is an optional Tcl name for the variable. For instance, this
   allows to use an existing variable. If not specified,
   an autogenerated name is used.
   
   .. method:: __str__()
   
   Returns the underlying Tcl variable's name.

   .. method:: get()
   .. method:: set(value)
   
   Read or write the underlying Tcl variable.
   
   .. method:: trace_add(mode, callback)
   
      Define a trace callback for the variable.
      
      Delegates to `trace add variable <https://tcl.tk/man/tcl8.6/TclCmd/trace.htm#M14>`_.

      *mode* is one of ``"read"``, ``"write"``, ``"unset"``, or a list or
      tuple of these.

      *callback* must be a function which is called when the variable is
      read, written or unset. It will be called with three arguments as per the doc.
      Within the callback, the variable can be read or written without
      triggering another trace event.

      Returns an autogenerated name of the callback that can later be
      used in :meth:`trace_remove`.
      
   .. method:: trace_remove(mode, cbname)
   
      Delete the trace callback for a variable.
      
      Delegates to `trace remove variable <https://tcl.tk/man/tcl8.6/TclCmd/trace.htm#M22>`_.

      *mode* is one of ``"read"``, ``"write"``, ``"unset"``, or a list or
      tuple of these.  Must be same as were specified in :meth:`trace_add`.
      
      *cbname* is the callback name that was returned by :meth:`trace_add`.

   .. method:: trace_info()
   
      Delegates to `trace info variable <https://tcl.tk/man/tcl8.6/TclCmd/trace.htm#M26>`_.
      
      Returns a list of tuples.
      
   .. method:: trace_variable(mode, callback)
   .. method:: trace_vdelete(mode, callback)
   .. method:: trace_vinfo(mode, callback)
   .. method:: trace(mode, callback)
   
      Deprecated counterparts to :meth:`Variable.trace_add`,
      :meth:`Variable.trace_remove` and :meth:`Variable.trace_info`,
      correspondingly.
      :meth:`trace` is an alias to :meth:`trace_variable`.
      
      Delegate to likewise deprecated ``trace variable``, ``trace vdelete``
      and ``trace vinfo`` Tk commands.
      
   
.. class:: StringVar
.. class:: IntVar
.. class:: DoubleVar
.. class:: BooleanVar

   Classes that enforce converting the value to/from the specified Python type
   when getting/setting it.
   
   There's no type for a list variable, :class:`StringVar` can be used for that.
   It can accept a list as input but on reading, will return its Tcl's (Unicode)
   string representation that can be :func:`eval`'ed.
   
   :meth:`IntVar.get` falls back to :class:`float` if conversion to :class:`int` fails.


.. :func:: mainloop

   Run :meth:`Tk.mainloop` for the :ref:`default root <default-root>`.
   
   ?Deprecated?

.. :function:: getint(value)
.. :function:: getdouble(value)
.. :function:: getboolean(value)

   Convert a value received from Tcl to the corresponding Python type.
   
   ?Deprecated (it's unused by other code)? The corresponding methods of :mod:`_tkinter`
   are to be used instead.

   
Tk objects
^^^^^^^^^^   
   
.. class:: Tk(screenName=None, baseName=None, className='Tk', useTk=1, sync=0, use=None)

   The :class:`Tk` class encapsulates a Tcl interpreter,
   `Tk application and its root window <https://www.tcl.tk/man/tcl8.6/TkLib/Tk_Init.htm#M5>`_.
   
   Due to encapsulating a top-level widget,
   :class:`Tk` also has all the members of :class:`BaseWidget` and :class:`Wm`.   
   By the means of :meth:`object.__getattr__`, it also provides transparent access to all
   attributes of the underlying :attr:`Tk.tk` object.
   A :class:`Tk` instance is acceptable wherever a :class:`Widget` is expected.

   The following only lists methods specific to :class:`Tk` and inherited methods
   with changed semantics.

   The constructor delegates to `Tk_Init <https://www.tcl.tk/man/tcl8.6/TkLib/Tk_Init.htm>`_.

   All arguments are optional and are not needed in the vast majority of cases.
   
   *screenName* specifies an alternative X server screen to use by
   `assigning it <https://www.tcl.tk/man/tcl8.6/TclCmd/tclvars.htm#M5>`_ to the ``DISPLAY``
   environment variable in Tcl before Tk initialization.
   
   *className* is assigned to `argv0 <https://www.tcl.tk/man/tcl8.6/TclCmd/tclvars.htm#M47>`_.
   
   If *useTk* is set to 0, Tk is not loaded into the interpreter
   and the root window is not created.
   This can be done at a later time by calling :meth:`Tk.loadtk()`.
   
   *sync* and *use* add
   `-sync and -use options to Tcl's argv <https://www.tcl.tk/man/tcl8.6/UserCmd/wish.htm#M4>`_.

   After loading Tk (if that was requested), the constructor runs startup scripts
   unless :option:`-E` was specified. The startup scripts are searched for
   in ``$HOME`` or current directory if ``$HOME`` is unset, with names
   ``<className>.tcl``, ``<className>.py``, ``<baseName>.tcl`` and ``<baseName>.py``,
   in that order. Tcl scripts are executed in the underlying Tcl interpreter.
   Python scripts are executed in a private namespace that has all public
   :mod:`tkinter` members and ``self`` that references the current :class:`Tk` object.
   
   
   .. method:: Tk.loadtk()

   Initializes Tk in the underlying interpreter and creates the Tk root widget.
   If Tk has already been initialized, the method has no effect.
   
   
   .. method:: Tk.destroy()
   
   Destroys the Tk root window, all child widgets and the Tk application.
   All Tk Tcl commands in the interpreter are replaced with stubs that return an error,
   so any further calls that delegate to them will fail.
   
   Delegates to `destroy <https://www.tcl.tk/man/tcl8.6/TkCmd/destroy.htm>`_.
   
   With threaded Tcl, :meth:`Tk.destroy` can only be called from the interpreter
   thread, but its call can be arranged from another thread with
   :meth:`Widget.after`:
   
   >>> tk.after(0,tk.destroy())

   
   .. attribute:: Tk.tk
   
   The underlying :class:`_tkinter.tkapp` object.

   
   .. method:: report_callback_exception(type, value, traceback)
   
   A callback that is called from within exception handler
   if Python payload in an event handler
   raises an exception. The default implementation prints the
   exception to :attr:`sys.stderr`.
   
   (Re)raising an exception here will cause it to propagate
   ?where?.
   

Widgets
-------

These classes provide Python bindings for regular Tk widgets
as well as base classes for all other widget bindings.

All concrete widget classes (save for :class:`Tk`) derive from :class:`Widget`.
Some also derive from mixin classes that provide interfaces specific
to some categories of widgets.


Base classes
^^^^^^^^^^^^

BaseWidget
~~~~~~~~~~

.. class:: BaseWidget(master, cnf={}, kw={}, extra=())

   Base abstract class that wraps functionality common to all Tk widgets.
   
   Derived classes typically change the constructor signature,
   making *kw* into ``**kwargs`` and omitting *extra*,
   but use these arguments when calling the base constructor.
   
   *cnf* and *kw* are combined into a dictionary.
   A few special items, if present, are popped and used specially:
   
   * ``name`` becomes the Tk path name for the widget.
     If *master* already has a child widget with this name, it's destroyed.
     
   * Any key that is a :class:`type` is treated as a customizer:
     after creating the widget, each's
     ``configure`` method is called with ``self``
     and the item's value as arguments.

   
   .. attribute:: master
   
   Parent widget. Read-only. Since :class:`Tk`s are root widgets,
   for them, it is ``None``.
   
   
   .. attribute:: children
   
   A dictionary of (*Tk pathname*, *widget*). Read-only.
   
   
   .. attribute:: widgetName
   
   Tk name for this widget class (more specificlly, the Tcl command
   that was used to create the widget). Read-only.
   
   
   .. method:: destroy()
   
   Destroy the widget and all its children recursively.
   
   Delegates to `destroy <https://www.tcl.tk/man/tcl8.6/TkCmd/destroy.htm>`_.

   
   .. method:: tk_strictMotif(boolean=None)
   
   See `tk_strictMotif <https://www.tcl.tk/man/tcl8.6/TkCmd/tkvars.htm#M6>`_.
   
   
   .. method:: tk_bisque()
   
   See `tk_bisque <https://www.tcl.tk/man/tcl8.6/TkCmd/palette.htm>`_.
   
   
   .. method:: tk_setPalette(*args, **kwargs)
   
   See `tk_setPalette <https://www.tcl.tk/man/tcl8.6/TkCmd/palette.htm>`_.
   
   *args* and *kwargs* become regular and keyword arguments, respectively.
   
   
   .. method:: wait_variable(name='PY_VAR')
   
   Wait until the variable is modified. *name* is the name of the Tcl variable.
   Due to the way `Python-Tcl type conversion` works, a :class:`Variable` can
   be passed.
   
   Delegates to `tkwait variable <https://www.tcl.tk/man/tcl8.6/TkCmd/tkwait.htm>`_.
   
   
   .. method:: waitvar(name='PY_VAR')
   
   ?A deprecated alias to :meth:`wait_variable`.
   
   
   .. method:: wait_window(window=None)
   
   Wait until the *window* :class:`Widget` is destroyed;
   defaults to the current widget.
   
   Delegates to `tkwait window <https://www.tcl.tk/man/tcl8.6/TkCmd/tkwait.htm>`_.
   
   
   .. method:: wait_visibility(window=None)
   
   Wait until the *window* :class:`Widget` changes visibility state;
   defaults to the current widget.
   
   Delegates to `tkwait visibility <https://www.tcl.tk/man/tcl8.6/TkCmd/tkwait.htm>`_.
   
   .. warning::
   
      This function is vulnerable to race conditions if something
      (e.g. the user closing the window) can change the widget's visibility
      at any moment. Polling :meth:`Wm.winfo_visible`
      should be preferred in such cases.
      
      
   .. method:: getvar(name='PY_VAR')
   .. method:: setvar(name='PY_VAR', value='1')
    
   Get or set a Tcl variable *name*.
   Due to the way `Python-Tcl type conversion` works, a :class:`Variable` can
   be passed, too.


   .. method:: getint(s)
   .. method:: getdouble(s)
   .. method:: getboolean(s)
   
   Convert a :class:`_tkinter.Tcl_Obj`, a Tcl string
   representation or a compatible Python type
   to the corresponding Python type.
   Raises :class:`ValueError` if the conversion fails.
   
   ?Internal, deprecated (it's unused by other code)? The corresponding
   :class:`_tkinter.tkapp` methods should be used instead.
   
   
   .. method:: focus_get()
   .. method:: focus_displayof()
   .. method:: focus_lastfor()
   
   Delegate to `focus <https://www.tcl.tk/man/tcl8.6/TkCmd/focus.htm#M5>`_,
   `focus -displayof <https://www.tcl.tk/man/tcl8.6/TkCmd/focus.htm#M7>_,
   and `focus -lastfor <https://www.tcl.tk/man/tcl8.6/TkCmd/focus.htm#M9>`,
   correspondingly.
   
   Return ``None`` instead of empty string if there's no result.

   
   .. method:: focus_set()
   .. method:: focus()
   .. method:: focus_force()
   
   See `focus *window* <https://www.tcl.tk/man/tcl8.6/TkCmd/focus.htm#M6>`_,
   `focus -force <https://www.tcl.tk/man/tcl8.6/TkCmd/focus.htm#M8>`_.
   
   ? :meth:`focus` is a deprecated alias to :math:`focus_set`?
   
   
   .. method:: tk_focusFollowsMouse()

   See `tk_focusFollowsMouse <https://www.tcl.tk/man/tcl8.6/TkCmd/focusNext.htm>`_.

   
   .. method:: tk_focusNext()
   .. method:: tk_focusPrev()

   Delegate to `tk_focusNext and tk_focusPrev <https://www.tcl.tk/man/tcl8.6/TkCmd/focusNext.htm>`_.
   
   Return ``None`` instead of empty string if there's no result.
   
   
   .. method:: after(ms, func=None, *args)
   .. method:: after_idle(func, *args)
   .. method:: after_cancel(id)
   .. method:: bell(displayof=0)
   .. method:: clipboard_get(**kw)
   .. method:: clipboard_clear(**kw)
   .. method:: clipboard_append(string, **kw)
   .. method:: grab_current(self)
   .. method:: grab_release(self)
   .. method:: grab_set(self)
   .. method:: grab_set_global(self)
   .. method:: grab_status(self)
   .. method:: option_add(pattern, value, priority = None)
   .. method:: option_clear(self)
   .. method:: option_get(name, className)
   .. method:: option_readfile(fileName, priority = None)
   .. method:: selection_clear(**kw)
   .. method:: selection_get(**kw)
   .. method:: selection_handle(command, **kw)
   .. method:: selection_own(**kw)
   .. method:: selection_own_get(**kw)
   .. method:: send(interp, cmd, *args)
   .. method:: lower(belowThis=None)
   .. method:: tkraise(aboveThis=None)
   .. method:: lift(aboveThis=None)
   .. method:: winfo_atom(name, displayof=0)
   .. method:: winfo_atomname(id, displayof=0)
   .. method:: winfo_cells()
   .. method:: winfo_children()
   .. method:: winfo_class()
   .. method:: winfo_colormapfull()
   .. method:: winfo_containing(rootX, rootY, displayof=0)
   .. method:: winfo_depth()
   .. method:: winfo_exists()
   .. method:: winfo_fpixels(number)
   .. method:: winfo_geometry()
   .. method:: winfo_height()
   .. method:: winfo_id()
   .. method:: winfo_interps(displayof=0)
   .. method:: winfo_ismapped()
   .. method:: winfo_manager()
   .. method:: winfo_name()
   .. method:: winfo_parent()
   .. method:: winfo_pathname(id, displayof=0)
   .. method:: winfo_pixels(number)
   .. method:: winfo_pointerx()
   .. method:: winfo_pointerxy()
   .. method:: winfo_pointery()
   .. method:: winfo_reqheight()
   .. method:: winfo_reqwidth()
   .. method:: winfo_rgb(color)
   .. method:: winfo_rootx()
   .. method:: winfo_rooty()
   .. method:: winfo_screen()
   .. method:: winfo_screencells()
   .. method:: winfo_screendepth()
   .. method:: winfo_screenheight()
   .. method:: winfo_screenmmheight()
   
   See `winfo <https://www.tcl.tk/man/tcl8.6/TkCmd/winfo.htm>`_.
   The below only lists Tkinter-specific semantics.
   
   * :meth:`winfo_atom` returns an integer instead of a string.
   * :meth:`winfo_atom` None
   

   
   
Pack
Place
Grid
Widget
Misc
XView
YView
Wm
Toplevel
Button
Canvas
Checkbutton
Entry
Frame
Label
Listbox
Menu
Menubutton
Message
Radiobutton
Scale
Scrollbar
Text
OptionMenu
Image
PhotoImage
BitmapImage
image_names
image_types
Spinbox
LabelFrame
PanedWindow


Widgets
-------



Other modules that provide Tk support include:

:mod:`tkinter.scrolledtext`
   Text widget with a vertical scroll bar built in.

:mod:`tkinter.colorchooser`
   Dialog to let the user choose a color.

:mod:`tkinter.commondialog`
   Base class for the dialogs defined in the other modules listed here.

:mod:`tkinter.filedialog`
   Common dialogs to allow the user to specify a file to open or save.

:mod:`tkinter.font`
   Utilities to help work with fonts.

:mod:`tkinter.messagebox`
   Access to standard Tk dialog boxes.

:mod:`tkinter.simpledialog`
   Basic dialogs and convenience functions.

:mod:`tkinter.dnd`
   Drag-and-drop support for :mod:`tkinter`. This is experimental and should
   become deprecated when it is replaced  with the Tk DND.

:mod:`turtle`
   Turtle graphics in a Tk window.


The Window Manager
^^^^^^^^^^^^^^^^^^

.. index:: single: window manager (widgets)

In Tk, there is a utility command, ``wm``, for interacting with the window
manager.  Options to the ``wm`` command allow you to control things like titles,
placement, icon bitmaps, and the like.  In :mod:`tkinter`, these commands have
been implemented as methods on the :class:`Wm` class.  Toplevel widgets are
subclassed from the :class:`Wm` class, and so can call the :class:`Wm` methods
directly.

To get at the toplevel window that contains a given widget, you can often just
refer to the widget's master.  Of course if the widget has been packed inside of
a frame, the master won't represent a toplevel window.  To get at the toplevel
window that contains an arbitrary widget, you can call the :meth:`_root` method.
This method begins with an underscore to denote the fact that this function is
part of the implementation, and not an interface to Tk functionality.

Here are some examples of typical usage::

   import tkinter as tk

   class App(tk.Frame):
       def __init__(self, master=None):
           super().__init__(master)
           self.pack()

   # create the application
   myapp = App()

   #
   # here are method calls to the window manager class
   #
   myapp.master.title("My Do-Nothing Application")
   myapp.master.maxsize(1000, 400)

   # start the program
   myapp.mainloop()

   
Common semantics
================

Python-Tcl type conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^

In Tcl, on script level, `everything is a string <https://wiki.tcl.tk/3018>`_
and internally represented as a `Tcl_Obj <https://www.tcl.tk/man/tcl8.6/TclLib/Object.htm>`_.
Due to this, every discernible Tcl value has a string representation.
If a Tcl command expects a different type (even a compound one)

However, on C API level, a ``Tcl_Obj`` can be initialized directly from
all sorts of different C types, and Tkinter uses this when passing Python
objects to Tcl calls -- to avoid any inaccuracies
(e.g. when passing floating-point numbers)
and discrepancies between :func:`str` and Tcl string representations.

:class:`bool`, :class:`str`, :class:`bytes` and :class:`float` are
converted by the corresponding `Tcl_New*Obj <https://www.tcl.tk/man/tcl8.6/TclLib/contents.htm>`_.
For integer, different APIs are tried until one can accomodate the value.
Lists and tuples are `converted <https://www.tcl.tk/man/tcl8.6/TclLib/ListObj.htm>`_
to a Tcl `list <https://www.tcl.tk/man/tcl8.6/TclCmd/list.htm>`_.
:class:`str`s with wide Unicode characters would produce a :class:`TclError` if
the Tcl build doesn't support them. A :class:`_tkinter.Tcl_Obj` gives the
wrapped object, naturally.

For other objects, their :func:`str` is processed.

For the return value, the reverse conversion is done.
`Tcl_Obj->typePtr <https://www.tcl.tk/man/tcl/TclLib/Object.htm#M6>`
is used to detemine the type, so e.g. if a command is declared to return
0 or 1, it will not be converted to ``bool``.



.. index:: single: Tcl/Tk Data Types

anchor
   Legal values are points of the compass: ``"n"``, ``"ne"``, ``"e"``, ``"se"``,
   ``"s"``, ``"sw"``, ``"w"``, ``"nw"``, and also ``"center"``.

bitmap
   There are eight built-in, named bitmaps: ``'error'``, ``'gray25'``,
   ``'gray50'``, ``'hourglass'``, ``'info'``, ``'questhead'``, ``'question'``,
   ``'warning'``.  To specify an X bitmap filename, give the full path to the file,
   preceded with an ``@``, as in ``"@/usr/contrib/bitmap/gumby.bit"``.

boolean
   You can pass integers 0 or 1 or the strings ``"yes"`` or ``"no"``.

callback
   This is any Python function that takes no arguments.  For example::

      def print_it():
          print("hi there")
      fred["command"] = print_it

color
   Colors can be given as the names of X colors in the rgb.txt file, or as strings
   representing RGB values in 4 bit: ``"#RGB"``, 8 bit: ``"#RRGGBB"``, 12 bit"
   ``"#RRRGGGBBB"``, or 16 bit ``"#RRRRGGGGBBBB"`` ranges, where R,G,B here
   represent any legal hex digit.  See page 160 of Ousterhout's book for details.

cursor
   The standard X cursor names from :file:`cursorfont.h` can be used, without the
   ``XC_`` prefix.  For example to get a hand cursor (:const:`XC_hand2`), use the
   string ``"hand2"``.  You can also specify a bitmap and mask file of your own.
   See page 179 of Ousterhout's book.

distance
   Screen distances can be specified in either pixels or absolute distances.
   Pixels are given as numbers and absolute distances as strings, with the trailing
   character denoting units: ``c`` for centimetres, ``i`` for inches, ``m`` for
   millimetres, ``p`` for printer's points.  For example, 3.5 inches is expressed
   as ``"3.5i"``.

font
   Tk uses a list font name format, such as ``{courier 10 bold}``. Font sizes with
   positive numbers are measured in points; sizes with negative numbers are
   measured in pixels.

geometry
   This is a string of the form ``widthxheight``, where width and height are
   measured in pixels for most widgets (in characters for widgets displaying text).
   For example: ``fred["geometry"] = "200x100"``.

justify
   Legal values are the strings: ``"left"``, ``"center"``, ``"right"``, and
   ``"fill"``.

region
   This is a string with four space-delimited elements, each of which is a legal
   distance (see above).  For example: ``"2 3 4 5"`` and ``"3i 2i 4.5i 2i"`` and
   ``"3c 2c 4c 10.43c"``  are all legal regions.

relief
   Determines what the border style of a widget will be.  Legal values are:
   ``"raised"``, ``"sunken"``, ``"flat"``, ``"groove"``, and ``"ridge"``.

scrollcommand
   This is almost always the :meth:`!set` method of some scrollbar widget, but can
   be any widget method that takes a single argument.

wrap:
   Must be one of: ``"none"``, ``"char"``, or ``"word"``.


Bindings and Events
^^^^^^^^^^^^^^^^^^^

.. index::
   single: bind (widgets)
   single: events (widgets)

The bind method from the widget command allows you to watch for certain events
and to have a callback function trigger when that event type occurs.  The form
of the bind method is::

   def bind(self, sequence, func, add=''):

where:

sequence
   is a string that denotes the target kind of event.  (See the bind man page and
   page 201 of John Ousterhout's book for details).

func
   is a Python function, taking one argument, to be invoked when the event occurs.
   An Event instance will be passed as the argument. (Functions deployed this way
   are commonly known as *callbacks*.)

add
   is optional, either ``''`` or ``'+'``.  Passing an empty string denotes that
   this binding is to replace any other bindings that this event is associated
   with.  Passing a ``'+'`` means that this function is to be added to the list
   of functions bound to this event type.

For example::

   def turn_red(self, event):
       event.widget["activeforeground"] = "red"

   self.button.bind("<Enter>", self.turn_red)

Notice how the widget field of the event is being accessed in the
``turn_red()`` callback.  This field contains the widget that caught the X
event.  The following table lists the other event fields you can access, and how
they are denoted in Tk, which can be useful when referring to the Tk man pages.

+----+---------------------+----+---------------------+
| Tk | Tkinter Event Field | Tk | Tkinter Event Field |
+====+=====================+====+=====================+
| %f | focus               | %A | char                |
+----+---------------------+----+---------------------+
| %h | height              | %E | send_event          |
+----+---------------------+----+---------------------+
| %k | keycode             | %K | keysym              |
+----+---------------------+----+---------------------+
| %s | state               | %N | keysym_num          |
+----+---------------------+----+---------------------+
| %t | time                | %T | type                |
+----+---------------------+----+---------------------+
| %w | width               | %W | widget              |
+----+---------------------+----+---------------------+
| %x | x                   | %X | x_root              |
+----+---------------------+----+---------------------+
| %y | y                   | %Y | y_root              |
+----+---------------------+----+---------------------+


The index Parameter
^^^^^^^^^^^^^^^^^^^

A number of widgets require "index" parameters to be passed.  These are used to
point at a specific place in a Text widget, or to particular characters in an
Entry widget, or to particular menu items in a Menu widget.

Entry widget indexes (index, view index, etc.)
   Entry widgets have options that refer to character positions in the text being
   displayed.  You can use these :mod:`tkinter` functions to access these special
   points in text widgets:

Text widget indexes
   The index notation for Text widgets is very rich and is best described in the Tk
   man pages.

Menu indexes (menu.invoke(), menu.entryconfig(), etc.)
   Some options and methods for menus manipulate specific menu entries. Anytime a
   menu index is needed for an option or a parameter, you may pass in:

   * an integer which refers to the numeric position of the entry in the widget,
     counted from the top, starting with 0;

   * the string ``"active"``, which refers to the menu position that is currently
     under the cursor;

   * the string ``"last"`` which refers to the last menu item;

   * An integer preceded by ``@``, as in ``@6``, where the integer is interpreted
     as a y pixel coordinate in the menu's coordinate system;

   * the string ``"none"``, which indicates no menu entry at all, most often used
     with menu.activate() to deactivate all entries, and finally,

   * a text string that is pattern matched against the label of the menu entry, as
     scanned from the top of the menu to the bottom.  Note that this index type is
     considered after all the others, which means that matches for menu items
     labelled ``last``, ``active``, or ``none`` may be interpreted as the above
     literals, instead.


Images
^^^^^^

Images of different formats can be created through the corresponding subclass
of :class:`tkinter.Image`:

* :class:`BitmapImage` for images in XBM format.

* :class:`PhotoImage` for images in PGM, PPM, GIF and PNG formats. The latter
  is supported starting with Tk 8.6.

Either type of image is created through either the ``file`` or the ``data``
option (other options are available as well).

The image object can then be used wherever an ``image`` option is supported by
some widget (e.g. labels, buttons, menus). In these cases, Tk will not keep a
reference to the image. When the last Python reference to the image object is
deleted, the image data is deleted as well, and Tk will display an empty box
wherever the image was used.

.. seealso::

    The `Pillow <http://python-pillow.org/>`_ package adds support for
    formats such as BMP, JPEG, TIFF, and WebP, among others.

.. _tkinter-file-handlers:

File Handlers
-------------

Tk allows you to register and unregister a callback function which will be
called from the Tk mainloop when I/O is possible on a file descriptor.
Only one handler may be registered per file descriptor. Example code::

   import tkinter
   widget = tkinter.Tk()
   mask = tkinter.READABLE | tkinter.WRITABLE
   widget.tk.createfilehandler(file, mask, callback)
   ...
   widget.tk.deletefilehandler(file)

This feature is not available on Windows.

Since you don't know how many bytes are available for reading, you may not
want to use the :class:`~io.BufferedIOBase` or :class:`~io.TextIOBase`
:meth:`~io.BufferedIOBase.read` or :meth:`~io.IOBase.readline` methods,
since these will insist on reading a predefined number of bytes.
For sockets, the :meth:`~socket.socket.recv` or
:meth:`~socket.socket.recvfrom` methods will work fine; for other files,
use raw reads or ``os.read(file.fileno(), maxbytecount)``.


.. method:: Widget.tk.createfilehandler(file, mask, func)

   Registers the file handler callback function *func*. The *file* argument
   may either be an object with a :meth:`~io.IOBase.fileno` method (such as
   a file or socket object), or an integer file descriptor. The *mask*
   argument is an ORed combination of any of the three constants below.
   The callback is called as follows::

      callback(file, mask)


.. method:: Widget.tk.deletefilehandler(file)

   Unregisters a file handler.


.. data:: READABLE
          WRITABLE
          EXCEPTION

   Constants used in the *mask* arguments.

.. seealso::

   Tkinter documentation:

   `Python Tkinter Resources <https://wiki.python.org/moin/TkInter>`_
      The Python Tkinter Topic Guide provides a great deal of information on using Tk
      from Python and links to other sources of information on Tk.

   `TKDocs <http://www.tkdocs.com/>`_
      Extensive tutorial plus friendlier widget pages for some of the widgets.

   `Tkinter reference: a GUI for Python <https://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html>`_
      On-line reference material.

   `Tkinter docs from effbot <http://effbot.org/tkinterbook/>`_
      Online reference for tkinter supported by effbot.org.

   `Programming Python <http://learning-python.com/about-pp4e.html>`_
      Book by Mark Lutz, has excellent coverage of Tkinter.

   `Modern Tkinter for Busy Python Developers <https://www.amazon.com/Modern-Tkinter-Python-Developers-ebook/dp/B0071QDNLO/>`_
      Book by Mark Roseman about building attractive and modern graphical user interfaces with Python and Tkinter.

   `Python and Tkinter Programming <https://www.manning.com/books/python-and-tkinter-programming>`_
      Book by John Grayson (ISBN 1-884777-81-3).

   Tcl/Tk documentation:

   `Tk commands <https://www.tcl.tk/man/tcl8.6/TkCmd/contents.htm>`_
      Most commands are available as :mod:`tkinter` or :mod:`tkinter.ttk` classes.
      Change '8.6' to match the version of your Tcl/Tk installation.

   `Tcl/Tk recent man pages <https://www.tcl.tk/doc/>`_
      Recent Tcl/Tk manuals on www.tcl.tk, which also hosts core development.

   `ActiveState Tcl Home Page <https://www.activestate.com/tcl/>`_
      Precompiled binaries of current versions of Tcl/Tk.

   `Tcl and the Tk Toolkit <https://www.tcltk-book.com/>`_
      Book by John Ousterhout, the inventor of Tcl.

   `Practical Programming in Tcl and Tk <http://www.beedub.com/book/>`_
      Brent Welch's encyclopedic book.

