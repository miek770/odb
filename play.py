#!/usr/bin/env python
#-*- coding: utf-8 -*-

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
