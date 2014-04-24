# Author: Rene Adler <rene.adler@electric-force.net>
# URL: https://github.com/adlerre/Sick-Beard
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

import urllib
import email.utils
import datetime
import re
import os
import traceback

from lib.bs4 import BeautifulSoup

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

import sickbeard
import generic

from sickbeard import classes
from sickbeard import helpers
from sickbeard import show_name_helpers
from sickbeard import scene_exceptions
from sickbeard import encodingKludge as ek

from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex, AuthException

class BinSearchProvider(generic.NZBProvider):

    def __init__(self):
        
        generic.NZBProvider.__init__(self, "BinSearch")

        self.urls = {
            'download': 'https://www.binsearch.info/fcgi/nzb.fcgi?q=%s',
            'detail': 'https://www.binsearch.info%s',
            'search': 'https://www.binsearch.info/index.php?%s',
        }
        
        self.supportsBacklog = false

    def imageName(self):
        
        if ek.ek(os.path.isfile, ek.ek(os.path.join, sickbeard.PROG_DIR, 'data', 'images', 'providers', self.getID() + '.png')):
            return self.getID() + '.png'
        return 'binsearch.png'
    
    def isEnabled(self):
        
        return sickbeard.BINSEARCH
    
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
   
    def _get_title_and_url(self, item):
        title = item['title']
        if title:
            title = title.replace(' ', '.')

        url = item['url']
        if url:
            url = url.replace('&amp;', '&')

        return (title, url)
    
    def _doSearch(self, search_string, show=None, max_age=0):
        
        params = {"q":search_string,
                  "m": "n",
                  "max": 400,
                  "minsize": 100,
                  "adv_sort": "date",
                  "adv_col": "on",
                  "adv_nfo": "on",
                  "adv_age": sickbeard.USENET_RETENTION}

        # if max_age is set, use it, don't allow it to be missing
        if max_age or not params['adv_age']:
            params['adv_age'] = max_age

        searchURL = self.urls["search"] % urllib.urlencode(params)

        logger.log(u"Search url: " + searchURL)
        
        data = self.getURL(searchURL)
        
        if not data:
            logger.log(u"No data returned from " + searchURL, logger.ERROR)
            return []
        
        res_items = []
        
        try:
            html = BeautifulSoup(data)
            main_table = html.find('table', attrs={'id':'r2'})

            if not main_table:
                return []

            items = main_table.find_all('tr')

            for row in items:
                title = row.find('span', attrs={'class':'s'})

                if not title: continue

                nzb_id = row.find('input', attrs={'type':'checkbox'})['name']
                info = row.find('span', attrs={'class':'d'})

                def extra_check(item):
                    parts = re.search('available:.(?P<parts>\d+)./.(?P<total>\d+)', info.text)
                    total = tryInt(parts.group('total'))
                    parts = tryInt(parts.group('parts'))

                    if (total / parts) < 0.95 or ((total / parts) >= 0.95 and not ('par2' in info.text.lower() or 'pa3' in info.text.lower())):
                        logger.log('Wrong: \'%s\', not complete: %s out of %s' % (item['name'], parts, total), logger.WARNING)
                        return False

                    if 'requires password' in info.text.lower():
                        logger.log('Wrong: \'%s\', passworded' % (item['name']), logger.WARNING)
                        return False

                    return True

                res_items.append({
                    'id': nzb_id,
                    'title': title.text,
                    'url': self.urls['download'] % nzb_id,
                    'extra_check': extra_check
                })

        except:
            logger.log('Failed to parse HTML response from BinSearch: %s' % traceback.format_exc(), logger.ERROR)
        
        results = []
        
        for curItem in res_items:
            (title, url) = self._get_title_and_url(curItem)
            if title and url and curItem['extra_check']:
                logger.log(u"Adding item from BinSearch to results: " + title, logger.DEBUG)
                results.append(curItem)
            else:
                logger.log(u"The HTML returned from the " + self.name + " incomplete, this result is unusable", logger.DEBUG)

        return results

provider = BinSearchProvider()
