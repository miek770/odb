#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import sqlite3
import sys
import os
import select
import re
import subprocess as sub
from random import randint
from time import sleep

import vfd
import alsaaudio
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import mutagen.id3


# Variables
DATABASE = "library.db"
LIBRARY_PATH = "/partage/Music"
VOLUME_INCREMENT = 3
SLEEP_DELAY = 0.01


class Player:
  def __init__(self, database, library_path):
    # Connection ou création de la base de données
    self.database = database
    self.library_path = library_path
    self.conn = sqlite3.connect(self.database)
    self.c = self.conn.cursor()
#    self.mixer = alsaaudio.Mixer()
#    self.vfd = vfd.Vfd("/dev/ttyS0", 19200)

    # Mode de lecture
    self.random = True
    self.stopped = False
    self.paused = False

    sql = "SELECT track.*, album.id, artist.id FROM track JOIN album ON track.album=album.id JOIN artist ON album.artist=artist.id"
    try:
      self.track_list = self.c.execute(sql).fetchall()
    except sqlite3.OperationalError:
      self.rescan()
      self.track_list = self.c.execute(sql).fetchall()
    self.tracks = len(self.track_list)
    self.current_track = None
    self.last_tracks = []
    self.next()
    
    while True:
      sleep(SLEEP_DELAY)
      if not self.stopped and self.p.poll():
        self.next()
      if self.isData():
        c = sys.stdin.read(1)
        if c == "s": # s = Stop/Play
          self.stopped = not self.stopped
          if self.stopped:
            self.stop()
        elif c == "h": # h = Help (commands)
          print "h : Help (this menu)"
          print "i : System information"
          print "q : Quit"
          print "r : Rescan"
          print "s : Stop"
          print "n : Next"
          print "b : Back"
          print "p : Pause/resume"
          print "d : Random"
          print "+ : Volume +"
          print "- : Volume -"
        elif c == "i": # i = System information
          self.info()
        elif c == "q": # q = Quit
          self.stop()
          sys.exit()
        elif c == "r": # r = Rescan
          self.rescan()
        elif c == "n": # n = Next
          self.next()
        elif c == "b": # b = Back (previous)
          self.back()
        elif c == "p": # p = Pause/resume
          if not self.stopped:
            self.p.stdin.write("p")
            self.paused = not self.paused
            if self.paused:
              print "Pause"
            else:
              print "Reprise"
        elif c == "d": # d = random
          self.random = not self.random
          if self.random:
            print "Mode aléatoire"
          else:
            print "Mode continu"
        elif c == "=" or c == "+": # + = Raise volume
          new_vol = int(self.mixer.getvolume()[0]) + VOLUME_INCREMENT
          if new_vol > 100:
            self.mixer.setvolume(100)
          else:
            self.mixer.setvolume(new_vol)
          print "Volume:", self.mixer.getvolume()[0], "%"
        elif c == "-": # - = Lower volume
          new_vol = int(self.mixer.getvolume()[0]) - VOLUME_INCREMENT
          if new_vol < 0:
            self.mixer.setvolume(0)
          else:
            self.mixer.setvolume(new_vol)
          print "Volume:", self.mixer.getvolume()[0], "%"

  def info(self):
    out = os.popen("sensors | grep °C").read()
    print out
    print "Artistes :", len(self.c.execute("SELECT id FROM artist").fetchall())
    print "Albums :", len(self.c.execute("SELECT id FROM album").fetchall())
    print "Chansons :", len(self.c.execute("SELECT id FROM track").fetchall())

  def back(self):
    # Retour à la toune précédente
    try:
      self.last_tracks[-1][0]
      self.current_track = self.last_tracks.pop()
      self.reload()
    except TypeError:
      pass
    except IndexError:
      pass

  def next(self):
    # Mode aléatoire
    if self.random == True:
      self.last_tracks.append(self.current_track)
      # Pour éviter que la liste grossisse à l'infini
      if len(self.last_tracks)>10:
        self.last_tracks.pop(0)
      # Éventuellement il va falloir s'assurent de changer d'artiste à chaque fois
      try:
        while self.last_tracks[-1][6] == self.current_track[6]:
          self.current_track = self.track_list[randint(0, self.tracks-1)]
      except TypeError:
        self.current_track = self.track_list[randint(0, self.tracks-1)]
      self.reload()

    # Mode continu
    else:
      self.last_tracks.append(self.current_track)
      # Pour éviter que la liste grossisse à l'infini
      if len(self.last_tracks)>10:
        self.last_tracks.pop(0)
      try:
        sql = "SELECT track.*, album.id, artist.id FROM track JOIN album ON " + \
              "track.album=album.id JOIN artist ON album.artist=artist.id WHERE album=" + \
              str(self.last_tracks[-1][2]) + " ORDER BY number"
        album_tracks = self.c.execute(sql).fetchall()
        i = 0
        for track in album_tracks:
          if track[1] == self.last_tracks[-1][1]:
            try:
              self.current_track = album_tracks[i+1]
            except IndexError:
              self.current_track = album_tracks[0]
            break
          i+=1
      except TypeError:
        self.current_track = self.track_list[randint(0, self.tracks-1)]
      self.reload()
    
  def reload(self):
    try:
      self.p.kill()
    except OSError:
      pass # Le procédé est déjà arrêté
    except AttributeError:
      pass # La variable n'est pas encore attribuée
    self.current_album = self.c.execute("SELECT * FROM album WHERE id=" +
                                        str(self.current_track[2])).fetchone()
    self.current_artist = self.c.execute("SELECT * FROM artist WHERE id=" +
                                         str(self.current_album[2])).fetchone()
    self.p = sub.Popen(["python", "play.py", self.current_track[3]],
                       stdout=sub.PIPE, stdin=sub.PIPE, stderr=sub.PIPE)
    print self.current_artist[1].capitalize(),
    print "-", self.current_album[1].capitalize(),
    print "-", self.current_track[4],
    print "-", self.current_track[1].capitalize()
  
  def isData(self):
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

  def stop(self):
    try:
      self.p.kill()
    except OSError:
      pass # Le procédé est déjà arrêté
    except AttributeError:
      pass # La variable n'est pas encore attribuée

  def rescan(self):
    self.stop()
    # Création des tables de données
    self.c.execute("""CREATE TABLE IF NOT EXISTS artist (
      id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE)""")

    self.c.execute("""CREATE TABLE IF NOT EXISTS album (
      id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
      name TEXT NOT NULL,
      artist INTEGER NOT NULL,
      FOREIGN KEY (artist) REFERENCES artist(id))""")

    self.c.execute("""CREATE TABLE IF NOT EXISTS track (
      id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
      name TEXT NOT NULL,
      album INTEGER NOT NULL,
      path TEXT NOT NULL UNIQUE,
      number INTEGER,
      FOREIGN KEY (album) REFERENCES album(id))""")

    self.conn.commit()

    # Retrait des chansons introuvables
    track_list = self.c.execute("SELECT * FROM track").fetchall()
    for track in track_list:
      try:
        with open(track[3]) as f: pass
      except IOError:
        print "Chanson introuvable :", track[1].capitalize()
        self.c.execute("DELETE FROM track WHERE id=" + str(track[0]))
        self.conn.commit()

    # Retrait des albums vides
    album_list = self.c.execute("SELECT * FROM album").fetchall()
    for album in album_list:
      if not len(self.c.execute("SELECT * FROM track WHERE album=" +
                 str(album[0])).fetchall()):
        print "Album vide :", album[1].capitalize()
        self.c.execute("DELETE FROM album WHERE id=" + str(album[0]))
        self.conn.commit()

    # Retrait des artistes vides
    artist_list = self.c.execute("SELECT * FROM artist").fetchall()
    for artist in artist_list:
      if not len(self.c.execute("SELECT * FROM album WHERE artist=" +
                 str(artist[0])).fetchall()):
        print "Artiste vide :", artist[0].capitalize()
        self.c.execute("DELETE FROM artist WHERE id=" + str(artist[0]))
        self.conn.commit()

    # Ajout des nouvelles chansons
    file_list = os.popen("find -L \"" + self.library_path +
                         "\" -type f -iname \"*.mp3\"").read().split("\n")[0:-1]
    for file in file_list:
      file = unicode(file, "UTF-8", "strict")

      # Épuration des tags de la chanson
      try:
        ROtags = MP3(file, ID3=EasyID3).tags
      except mutagen.mp3.HeaderNotFoundError, msg:
        print u"Fichier ignoré,", msg, ":", file
        continue

      tags = dict()
      if ROtags is not None:
        try:
          try:
            tags["artist"] = unicode(ROtags["artist"][0].replace("\"", "").lower(),
                                     "UTF-8", "strict")
          except TypeError:
            tags["artist"] = ROtags["artist"][0].replace("\"", "").lower()
          try:
            tags["album"] = unicode(ROtags["album"][0].replace("\"", "").lower(),
                                    "UTF-8", "strict")
          except TypeError:
            tags["album"] = ROtags["album"][0].replace("\"", "").lower()
          try:
            tags["title"] = unicode(ROtags["title"][0].replace("\"", "").lower(),
                                    "UTF-8", "strict")
          except TypeError:
            tags["title"] = ROtags["title"][0].replace("\"", "").lower()
          s = ROtags["tracknumber"][0]
          tags["tracknumber"] = unicode(int(s[:re.search(r"[^0-9]", s).start()]))
        except AttributeError:
#          print u"Fichier ignoré, chemin invalide :", file
          continue
        except KeyError:
#          print u"Fichier ignoré, champ(s) manquant(s) :", tags
          continue
      else:
#       print u"Fichier ignoré, chemin invalide :", file
        continue

      # Traitement de l'artiste
      artist = self.c.execute("SELECT * FROM artist WHERE name=\"" + tags["artist"] +
                              "\"").fetchall()
      if not len(artist):
        print "Nouvel artiste :", tags["artist"].capitalize()
        self.c.execute("INSERT INTO artist (name) VALUES (\"" + tags["artist"] + "\")")
        self.conn.commit()
        artist = self.c.execute("SELECT * FROM artist WHERE name=\"" + tags["artist"] +
                                "\"").fetchall()

      # Traitement de l'album
      album = self.c.execute("SELECT * FROM album WHERE artist=" + str(artist[0][0]) +
                             " AND name=\"" + tags["album"] + "\"").fetchall()
      if not len(album):
        print "Nouvel album :", tags["album"].capitalize()
        self.c.execute("INSERT INTO album (name, artist) VALUES (\"" + tags["album"] +
                       "\", " + str(artist[0][0]) + ")")
        self.conn.commit()
        album = self.c.execute("SELECT * FROM album WHERE artist=" + str(artist[0][0]) +
                               " AND name=\"" + tags["album"] + "\"").fetchall()

      # Traitement de la chanson
      track = self.c.execute("SELECT * FROM track WHERE album=" + str(album[0][0]) +
                             " AND name=\"" + tags["title"] + "\"").fetchall()
      if not len(track):
        self.c.execute("INSERT INTO track (name, album, path, number) VALUES (\"" +
                       tags["title"] + "\", " + str(album[0][0]) + ", \"" + file +
                       "\", \"" + tags["tracknumber"] + "\")")
        self.conn.commit()


if __name__ == "__main__":
  p = Player(database=DATABASE, library_path=LIBRARY_PATH)
