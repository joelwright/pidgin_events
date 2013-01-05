Pidgin Events
=============

The python script pidgin_events.py listens for Pidgin messages and status
changes on DBUS and outputs those into FIFO queues that can be displayed
using xmobar's PipeReader (xmobarrc-bottom is the config file I use for xmobar)

Setup
-----

I use 3 FIFO queues for status, message and last message time. These can
be made using the "mkfifo" command. The whole setup can then be lauched
with the following commands:

> pidgin_events.py &
> xmobar /path/to/xmobarrc-bottom &

