#!/usr/bin/env python
#-*- coding: utf-8 -*-

# Copyright 2011-2012 Michel Lavoie
# miek770(at)gmail.com

# This file is part of Odb.

# Odb is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Odb is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Odb. If not, see <http://www.gnu.org/licenses/>.

import sys, select, mad, ao#, alsaaudio

def isData():
  return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

# Chargement de la toune et de l'audio
mf = mad.MadFile(sys.argv[1])
dev = ao.AudioDevice("alsa", rate=mf.samplerate())

# Variables
paused = False

while True:
  if isData():
    c = sys.stdin.read(1)
    if c == "p": # Pause
      paused = not paused
      if paused: print "Pause"
      else: print "Resume"

  # Joue la toune
  if not paused:
    buf = mf.read()
    if buf is None:
      sys.exit()
    dev.play(buf, len(buf))
