#!/usr/bin/python2
# Copyright (c) 2013 Joel Wright, Richard Genoud
#
# GNU General Public Licence (GPL)
# 
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA

import datetime as d
import dbus
import gobject
import gtk
import math
import os
import sys
import threading
import time
from dbus.mainloop.glib import DBusGMainLoop
from HTMLParser import HTMLParser

# Config params
message_timeout = 30
change_timeout = 10
status_pipe = '/home/jjw/.xmonad/pipes/status'
messge_pipe = '/home/jjw/.xmonad/pipes/messge'
change_pipe = '/home/jjw/.xmonad/pipes/change'

# Status dict
status = {
   1: 'Offline',
   2: 'Available',
   3: 'Unavailable',
   4: 'Invisible',
   5: 'Away',
   6: 'Extended Away',
   7: 'Mobile',
   8: 'Tune',
   }


class PerodicTimer:
   def __init__(self, timeout, function):
      self.last = d.datetime.now()
      self.last_active = False
      self.value = timeout
      self.function = function
      self.counter = self.value
      gobject.timeout_add_seconds(1, self.callback)

   def callback(self):
      self.counter -= 1
      if (self.counter <= 0):
         self.perform_action(self.function)
      return True

   def perform_action(self, f, *args):
      if self.last_active: 
         self.function(*args)

   def reset(self):
      self.counter = self.value
      self.last = d.datetime.now()
      self.last_active = True

   def get_last(self):
      return self.last

   def deactivate(self):
      self.last_active = False


class HTMLStripper(HTMLParser):
   def __init__(self):
      self.reset()
      self.fed = []

   def handle_data(self, d):
      self.fed.append(d)

   def get_data(self):
      return ''.join(self.fed)


def strip_tags(html):
   s = HTMLStripper()
   s.feed(html)
   return s.get_data()

def show_message(account, sender, message, conversation, flags):
   message_timer.reset()
   messge_pipe_file = open(messge_pipe, 'w', 0)
   messge_pipe_file.write("%s%s%s\n" % (sender, " : ", strip_tags(message)))
   messge_pipe_file.close()
   change_timer.reset()
   last_changed()

def status_changed(account, old, new):
   status_pipe_file = open(status_pipe, 'w', 0)
   current_status = get_current_status()
   status_pipe_file.write("%s\n" % current_status)
   status_pipe_file.close()

def last_changed():
   # Calculate last changed time
   last = change_timer.get_last()
   td = d.datetime.now() - last
   timedelta = int(math.floor(td.total_seconds() / 60))
   change_pipe_file = open(change_pipe, 'w', 0)
   if timedelta < 1:
      change_pipe_file.write(" \n")
   else:
      change_pipe_file.write("%sm\n" % timedelta)
   change_pipe_file.close()

def pidgin_quitting():
   # Set status to not running, clear last message timer and message
   status_pipe_file = open(status_pipe, 'w', 0)
   status_pipe_file.write("%s\n" % "Pidgin not running")
   status_pipe_file.close()
   change_pipe_file = open(change_pipe, 'w', 0)
   change_pipe_file.write(" \n")
   change_pipe_file.close()
   clear_message()
   message_timer.deactivate()
   change_timer.deactivate()

def pidgin_starting(account):
   status_pipe_file = open(status_pipe, 'w', 0)
   current_status = get_current_status()
   status_pipe_file.write("%s\n" % current_status)
   status_pipe_file.close()

def clear_message():
   messge_pipe_file = open(messge_pipe, 'w', 0)
   messge_pipe_file.write(" \n")
   messge_pipe_file.close()
   message_timer.reset()

def signed_on(account):
   status = ""
   return status

def get_current_status():
   current_status = None
   try:
      bus = dbus.SessionBus()
      obj = bus.get_object("im.pidgin.purple.PurpleService", "/im/pidgin/purple/PurpleObject")
      purple = dbus.Interface(obj, "im.pidgin.purple.PurpleInterface")
      current_status_code = purple.PurpleSavedstatusGetType(purple.PurpleSavedstatusGetCurrent())
      current_status = get_current_status = status[current_status_code]
   except Exception as e:
      current_status = "Pidgin not running"
   return current_status   

def main():
   dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
   bus = dbus.SessionBus()

   clear_message()
   last_changed()

   # start listening for events
   s = get_current_status()
   status_pipe_file = open(status_pipe, 'w', 0)
   status_pipe_file.write("%s\n" % s)
   status_pipe_file.close()

   # Add the events we always want to handle
   # some other events can be added here.
   # (see http://developer.pidgin.im/wiki/DbusHowto for more signals)
   bus.add_signal_receiver(show_message,
                           dbus_interface="im.pidgin.purple.PurpleInterface",
                           signal_name="ReceivedImMsg")
   
   bus.add_signal_receiver(show_message,
                           dbus_interface="im.pidgin.purple.PurpleInterface",
                           signal_name="ReceivedChatMsg")

   bus.add_signal_receiver(status_changed,
                           dbus_interface="im.pidgin.purple.PurpleInterface",
                           signal_name="AccountStatusChanged")

   bus.add_signal_receiver(pidgin_quitting,
                           dbus_interface="im.pidgin.purple.PurpleInterface",
                           signal_name="Quitting")

   bus.add_signal_receiver(pidgin_starting,
                           dbus_interface="im.pidgin.purple.PurpleInterface",
                           signal_name="AccountSignedOn")

   loop = gobject.MainLoop()
   loop.run()

message_timer = PerodicTimer(message_timeout, clear_message)
change_timer = PerodicTimer(change_timeout, last_changed)

if __name__ == "__main__":
   main()
