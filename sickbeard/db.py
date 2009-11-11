# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.



import os.path
import sqlite3

import sickbeard

from lib.tvdb_api import tvdb_api

class DBConnection:
		def __init__(self):
			self.connection = sqlite3.connect(os.path.join(sickbeard.PROG_DIR, "sickbeard.db"), 20)
			self.connection.row_factory = sqlite3.Row
		
		def checkDB(self):
			# Create the table if it's not already there
			try:
				sql = "CREATE TABLE tv_shows (show_id INTEGER PRIMARY KEY, location TEXT, show_name TEXT, tvdb_id NUMERIC, network TEXT, genre TEXT, runtime NUMERIC, quality NUMERIC, predownload NUMERIC, airs TEXT, status TEXT, seasonfolders NUMERIC);"
				self.connection.execute(sql)
				self.connection.commit()
			except sqlite3.OperationalError as e:
				if str(e) != "table tv_shows already exists":
					raise

			# Create the table if it's not already there
			try:
				sql = "CREATE TABLE tv_episodes (episode_id INTEGER PRIMARY KEY, showid NUMERIC, tvdbid NUMERIC, name TEXT, season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, hastbn NUMERIC, status NUMERIC, location TEXT);"
				self.connection.execute(sql)
				self.connection.commit()
			except sqlite3.OperationalError as e:
				if str(e) != "table tv_episodes already exists":
					raise

			# Create the table if it's not already there
			try:
				sql = "CREATE TABLE info (last_backlog NUMERIC, last_tvdb NUMERIC);"
				self.connection.execute(sql)
				self.connection.commit()
			except sqlite3.OperationalError as e:
				if str(e) != "table info already exists":
					raise
