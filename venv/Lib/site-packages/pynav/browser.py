#!/usr/bin/env python3
"""
This file is part of Pynav.

Pynav is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Pynav is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with Pynav. If not, see <http://www.gnu.org/licenses/lgpl.html>.

Copyright 2009-2018 Sloft http://bitbucket.org/sloft/pynav
"""

import os
import re
import time
import random
import socket
import urllib.request
import urllib.parse
import urllib.error
import urllib.robotparser
from urllib.parse import urlparse
import http.client
import http.cookiejar
from datetime import datetime
import pickle

from .response import Response
from . import useragent


class Browser(object):
    """Programmatic web browser to fetch data and test web sites"""

    def __init__(self):
        self.version = '1.0'
        self.verbose = False
        self.temps_min = 0
        self.temps_max = 0
        self.max_page_size = 500000
        self.max_history = 200
        self.headers = {}
        self.user_agent = useragent.firefox_windows
        self._handle_referer = False
        self._cookie_jar = http.cookiejar.CookieJar()
        handler = urllib.request.HTTPCookieProcessor(self._cookie_jar)
        self._url_opener = urllib.request.build_opener(handler)
        self.history = []
        self.current_page = -1
        self.allowed_content_types = []
        self.root_url = None
        self.response = self.r = Response #Type aliase
        self._timeout = None
        self._proxy = None
        self.handle_robots = True
    
    def set_http_auth(self, base_url, username, password):
        """Define parameters to set HTTP Basic Authentication"""
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, base_url, username, password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        self._url_opener.add_handler(handler)
    
    def set_page_delay(self, temps_min=0, temps_max=0):
        """Define the time between pages, random seconds, min and max"""
        self.temps_min = temps_min
        if temps_min > temps_max:
            self.temps_max = temps_min
        else:
            self.temps_max = temps_max
        if self.verbose:
            print('temps_min: {self.temps_min}, temps_max: {self.temps_max}'.format(self=self))

    def go(self, url, values={}, read=True) -> Response:
        """Open an url with optional post values, return a Response object"""
        url = urllib.parse.quote(url, ';/?:@&=+$,') #URI Reserved characters not escaped, RFC 2396
        handle = self.open(url, values)
        
        if self.handle_robots:
            url = self._filter_url(url)
            if not self._robots_can_fetch(url):
                print('Robots are not allowed to access this url:', url)
                return None
        
        if handle:
            self.real_url = handle.geturl()
            self.response = self.r = Response(self, read)
            
            if len(self.history) > self.max_history - 1:
                del self.history[0]
            self.current_page = self.current_page + 1
            self.history.append({'url':url, 'post':values, 'response':self.response})
            
            if self.current_page > len(self.history) - 1:
                self.current_page = len(self.history) - 1
            
            up = urlparse(self.real_url)
            self.root_url = "{scheme}://{netloc}/".format(scheme=up.scheme, netloc=up.netloc)
            return self.response
        else:
            return None
    
    def download(self, url, destination=None):
        """Download the file at an url to a file or destination"""
        download_path = os.getcwd()
        if not destination:
            destination = download_path
        
        url = self._filter_url(url)        
        filename, filesize = self._extract_file_infos(url)
        if filename is '':
            filename = url.split('/')[-1]

        #Case root url (http://example.com)
        if filename is '':
            filename = 'root.html'

        if not os.path.isdir(destination):
            os.makedirs(destination)
        
        if destination[-1] in ('/', '\\'):
            destination = destination + filename
        else:
            destination = destination + '/' + filename

        if self.verbose:
            print("Downloading {filename} ({filesize}) to: {destination}".format(filename=filename, filesize=filesize, destination=destination))
        return urllib.request.urlretrieve(url, destination)
    
    def open(self, url, values={}) -> http.client.HTTPResponse:
        """Open an url with http protocol. The page is not read. Could be used to only read http header
            Return: http.client.HTTPResponse"""
        self._init_request(url, values)
        
        handle = None
        try:
            handle = self._url_opener.open(self.req)
        except urllib.error.HTTPError as exception:
            if exception.code == 404:
                print('(404) Page not found !')
            else:           
                print('HTTP request failed with error {exception.code:d} ({exception.msg})'.format(exception=exception))
        except urllib.error.URLError as exception:
            print('Opening URL failed because: {exception.reason}'.format(exception=exception))
        except http.client.BadStatusLine as exception:
            print(exception.line) #print nothing...
            print("BadStatusLine Error! Httplib issue, can't get this page, sorry...")
        
        if handle is not None:
            handle.values = values
            self.handle = handle
        return handle
    
    def is_404(self, url, values=None):
        self._init_request(url, values)
        
        try:
            self._url_opener.open(self.req)
        except urllib.error.HTTPError as exception:
            if exception.code == 404:
                return True
        except urllib.error.URLError as exception:
            print('Opening URL failed because: {exception.reason}'.format(exception=exception))
        except http.client.BadStatusLine as exception:
            print(exception.line) #print nothing...
            print("BadStatusLine Error! Httplib issue, can't get this page, sorry...")

        return False

    def check_new_resource(self, url, last_datetime, values={}):
        """Check the datetime of a resource by reading only HTTP header Last-Modified
            Return True if a new resource is available, False otherwise"""
        h = self.open(url, values)
        str_last_modified = h.headers['Last-Modified']
        if isinstance(str_last_modified, str):
            last_modified = datetime.strptime(str_last_modified, '%a, %d %b %Y %H:%M:%S GMT')
            return last_modified > last_datetime
        else:
            print('This resource has no HTTP header Last-Modified')

    def allow_html_only(self):
        """Browser accepts only txt/html content type"""
        self.allowed_content_types = ['text/html']
    
    def allow_all_content_types(self):
        """Browser accepts all content type"""
        self.allowed_content_types = []
    
    def allow_content_type(self, content_type):
        """Browser accepts the specified content_type, add it to the allowed_content_types list"""
        if content_type not in self.allowed_content_types:
            self.allowed_content_types.append(content_type)
    
    def save_history(self, file_name):
        """Save history in a file"""
        with open(file_name, 'w') as f:
            pickle.dump(self.history, f)
    
    def load_history(self, file_name):
        """Load history from a file"""
        try:
            with open(file_name, 'r') as f:
                self.history = pickle.load(f)
        except IOError:
            print("ERROR: file {file_name} doesn't exist".format(file_name=file_name))
    
    def replay(self, begining=0, end=None, print_url=False, print_post=False, print_response=False):
        """Replay history, can be used after loading history from a file"""
        history, self.history = self.history, []
        if not end:
            end = len(history)
        for page in history[begining:end]:
            self.go(page['url'], page['post'])
            if print_url:
                print(page['url'])
            if print_post:
                print(page['post'])
            if print_response:
                print(page['response'])
        return False
    
    def get_cookies(self, url=None):
        """Return a cookies dict of the specified url, current url by default"""
        if not url:
            netloc = urlparse(self.root_url).netloc
        else:
            netloc = urlparse(url).netloc
        if netloc in self._cookie_jar._cookies:
            return self._cookie_jar._cookies[netloc]['/']

    @property
    def cookies(self):
        """Return a cookies dict of the current url: {'cookie_name':Cookie instance, ...}
           To test if a cookie exists: if 'cookie_name' in browser.cookies: ..."""
        return self.get_cookies()

    @property
    def user_agent(self) -> str:
        """Return the current user agent """
        return self.headers['User-Agent']

    @user_agent.setter
    def user_agent(self, user_agent: str):
        self.headers['User-Agent'] = user_agent

    @property
    def referer(self):
        """Decorator to get the referer, the previous visited page"""
        if 'Referer' in self.headers:
            return self.headers['Referer']
        else:
            return None
    
    @referer.setter
    def referer(self, referer):
        """Decorator to define a referer, the previous visited page"""
        self.headers['Referer'] = referer
    
    @property
    def handle_referer(self):
        """Decorator to get the status of the handle_referer attribute"""
        return self._handle_referer
    
    @handle_referer.setter
    def handle_referer(self, boolean):
        """Decorator to set the handle_referer boolean value"""
        self._handle_referer = boolean
        if not boolean:
            if 'Referer' in self.headers:
                self.headers.pop('Referer')

    @property
    def timeout(self):
        """Return the timeout in seconds"""
        return self._timeout
    
    @timeout.setter
    def timeout(self, seconds):
        """Set timeout in seconds"""
        self._timeout = seconds
        socket.setdefaulttimeout(seconds)
    
    @property
    def proxy(self):
        """Return th proxy string """
        return self._proxy
    
    @proxy.setter
    def proxy(self, proxy):
        """Set a proxy: 'ip:port' or 'domain:port'"""
        if proxy not in (None, ''):
            self._proxy = proxy
            handler = urllib.request.ProxyHandler({'http': self._proxy})
            self._url_opener.add_handler(handler)

    def _init_request(self, url, values):
        """Private method to initialize some attributes"""
        sleep_time = random.randint(self.temps_min, self.temps_max)
        if self.verbose and sleep_time > 0:
            print('waiting {sleep_time} secs'.format(sleep_time=sleep_time))
        if sleep_time:
            time.sleep(sleep_time)
        if self._handle_referer:
            if len(self.history) > 0:
                self.referer = self.history[self.current_page]['url']
        
        url = self._filter_url(url)
        
        if values:
            data = urllib.parse.urlencode(values)
            self.req = urllib.request.Request(url, data, self.headers)
        else:
            self.req = urllib.request.Request(url, headers=self.headers)
        
        self.response = None
    
    def _filter_url(self, url):
        """Private method to correct the url"""
        if not re.search('://', url):
            url = 'http://' + url
        if url.count('/') < 3:
            url = url + '/'
        return url
    
    def _robots_can_fetch(self, url):
        rp = urllib.robotparser.RobotFileParser()
        robots_url = "http://{root_url}/robots.txt".format(root_url=urlparse(url).netloc)
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(useragent='*', url=url)
       
    def _extract_file_infos(self, url):
        filename = ''
        filesize = ''
        h = self.open(url)
        if 'Content-disposition' in h.headers:
            content_disposition = h.headers['Content-disposition']
            res = re.findall('"(.+?)"', content_disposition, re.S)
            if len(res) == 1:
                filename = res[0]
        if 'Content-Length' in h.headers:
            content_length = h.headers['Content-Length']
            filesize = self._humanize_bytes(content_length)
        return filename, filesize
    
    def _humanize_bytes(self, nb_bytes, precision=1):
        """Return an humanized string representation of a number of bytes"""
        abbrevs = (
            (1<<50, 'PB'),
            (1<<40, 'TB'),
            (1<<30, 'GB'),
            (1<<20, 'MB'),
            (1<<10, 'KB'),
            (1, 'bytes')
        )
        nb_bytes = float(nb_bytes)
        if nb_bytes == 1:
            return '1 byte'
        for factor, suffix in abbrevs:
            if nb_bytes >= factor:
                break
        if suffix=='bytes':
            precision = 0
        return '{0:.{1}f} {2}'.format(nb_bytes / factor, precision, suffix)
