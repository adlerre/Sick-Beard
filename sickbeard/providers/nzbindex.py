# Author: Rene Adler <rene.adler@electric-force.net>
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

import datetime
import time
import gzip
import os
import re
import socket
import StringIO
import traceback
import urllib
import urllib2
import zlib

from httplib import BadStatusLine

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

import sickbeard
import generic

from sickbeard.common import USER_AGENT

from sickbeard import classes
from sickbeard import helpers
from sickbeard import show_name_helpers
from sickbeard import encodingKludge as ek

from sickbeard import logger
from sickbeard import tvcache

class NZBIndexProvider(generic.NZBProvider):

    def __init__(self):
        generic.NZBProvider.__init__(self, "NZBIndex")

        self.cache = NZBIndexCache(self)

        self.max_retries = 10
        self.url = 'https://www.nzbindex.nl/'
        self.rss = 'rss/?'
        
        self.supportsBacklog = True

    def imageName(self):
        if ek.ek(os.path.isfile, ek.ek(os.path.join, sickbeard.PROG_DIR, 'data', 'images', 'providers', self.getID() + '.png')):
            return self.getID() + '.png'
        return 'nzbindex.png'
    
    def isEnabled(self):
        return sickbeard.NZBINDEX
    
    def getURL(self, url, post_data=None, headers=[]):
        """
        Returns a byte-string retrieved from the url provider.
        """
    
        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', USER_AGENT), ('Accept-Encoding', 'gzip,deflate')]
        for cur_header in headers:
            opener.addheaders.append(cur_header)
    
        try:
            usock = opener.open(url, post_data)
            url = usock.geturl()
            encoding = usock.info().get("Content-Encoding")
    
            if encoding in ('gzip', 'x-gzip', 'deflate'):
                content = usock.read()
                if encoding == 'deflate':
                    data = StringIO.StringIO(zlib.decompress(content))
                else:
                    data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(content))
                result = data.read()
    
            else:
                result = usock.read()
    
            usock.close()
    
        except urllib2.HTTPError, e:
            logger.log(u"HTTP error " + str(e.code) + " while loading URL " + url, logger.WARNING)
            return {"errorCode": e.code}
    
        except urllib2.URLError, e:
            logger.log(u"URL error " + str(e.reason) + " while loading URL " + url, logger.WARNING)
            return None
    
        except BadStatusLine:
            logger.log(u"BadStatusLine error while loading URL " + url, logger.WARNING)
            return None
    
        except socket.timeout:
            logger.log(u"Timed out while loading URL " + url, logger.WARNING)
            return None
    
        except ValueError:
            logger.log(u"Unknown error while loading URL " + url, logger.WARNING)
            return None
    
        except Exception:
            logger.log(u"Unknown exception while loading URL " + url + ": " + traceback.format_exc(), logger.WARNING)
            return None
    
        return result

    def _get_season_search_strings(self, show, season=None):

        if not show:
            return [{}]
        
        to_return = [];
        
        search_strings = show_name_helpers.makeSceneSeasonSearchString(show, season);

        if show.rls_require_words:
            for word in show.rls_require_words.split(','):
                for search_string in search_strings:
                    to_return.append(search_string + " " + word.strip())
                    
            return to_return
        else:        
            return [x for x in search_strings]

    def _get_episode_search_strings(self, ep_obj):
        
        if not ep_obj:
            return [{}]

        to_return = [];
        
        search_strings = show_name_helpers.makeSceneSearchString(ep_obj);

        if ep_obj.show.rls_require_words:
            for word in ep_obj.show.rls_require_words.split(','):
                for search_string in search_strings:
                    to_return.append(search_string + " " + word.strip())
                    
            return to_return
        else:        
            return [x for x in search_strings]
   
    def _doSearch(self, search_string, show=None, max_age=0):
        params = {"q":search_string,
                  "max": 100,
                  "hidespam": 1,
                  "minsize":100,
                  "nzblink":1,
                  "complete": 1,
                  "sort": "agedesc",
                  "age": sickbeard.USENET_RETENTION}

        # if max_age is set, use it, don't allow it to be missing
        if max_age or not params['age']:
            params['age'] = max_age

        searchURL = self.url + self.rss + urllib.urlencode(params)

        logger.log(u"Search url: " + searchURL)

        retry = 0
        while True:
            logger.log(u"Sleeping 3 seconds to respect NZBIndex's rules")
            time.sleep(3)
            
            data = self.getURL(searchURL)
        
            if not data:
                logger.log(u"No data returned from " + searchURL, logger.ERROR)
                return []

            if type(data) == type({}) and data['errorCode']:
                if retry < self.max_retries:
                    logger.log(u"Retry " + str(retry+1) + " from " + str(self.max_retries) + "...", logger.WARNING)
                    retry += 1
                else:
                    logger.log(u"Max retries reached!", logger.ERROR)
                    return []
            else:
                break
        
        parsedXML = helpers.parse_xml(data)

        if parsedXML is None:
            logger.log(u"Error trying to load " + self.name + " XML data", logger.ERROR)
            return []
        
        if parsedXML.tag == 'rss':
            items = parsedXML.findall('.//item')
        results = []

        for curItem in items:
            (title, url) = self._get_title_and_url(curItem)
            if title and url:
                logger.log(u"Adding item from RSS to results: " + title, logger.DEBUG)
                results.append(curItem)
            else:
                logger.log(u"The XML returned from the " + self.name + " RSS feed is incomplete, this result is unusable", logger.DEBUG)

        return results


    def findPropers(self, date=None):

        results = []

        for curResult in self._doSearch("(PROPER,REPACK)"):

            (title, url) = self._get_title_and_url(curResult)

            pubDate_node = curResult.getElementsByTagName('pubDate')[0]
            pubDate = helpers.get_xml_text(pubDate_node)
            dateStr = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', pubDate).group(1)
            if not dateStr:
                logger.log(u"Unable to figure out the date for entry " + title + ", skipping it")
                continue
            else:
                resultDate = datetime.datetime.strptime(dateStr, "%a, %d %b %Y %H:%M:%S")

            if date == None or resultDate > date:
                results.append(classes.Proper(title, url, resultDate))

        return results


class NZBIndexCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll NZBIndex every 25 minutes max
        self.minTime = 25


    def _getRSSData(self):
        # get all records since the last timestamp
        url = self.provider.url + self.provider.rss

        urlArgs = {'q': '',
                   'max': 500,
                   'sort': 'agedesc',
                   'hidespam': 1,
                   'minsize':100,
                   'nzblink':1,
                   'complete': 1,
                   "age": sickbeard.USENET_RETENTION}

        url += urllib.urlencode(urlArgs)

        logger.log(u"NZBIndex cache update URL: " + url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data


provider = NZBIndexProvider()
