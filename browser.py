#!/usr/bin/env python3
# browser.py
# This script requires a third-party library: requests
# To install this library on Ubuntu 14.04::
# sudo apt-get update; sudo apt-get install python3-requests
#
import requests, re, random, time, threading, sys
from urllib.parse import urlparse

class Browser(threading.Thread):
    '''
    A virtual Web user that browses a given Python list of Web sites
    more or less randomly
    '''
    # A list of user-agents from which Browser agents will pick
    # randomly to identify themselves in the HTTP headers of
    # their GET requests 
    uas = ['"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:44.0) Gecko/20100101 Firefox/44.0"', '"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:43.0) Gecko/20100101 Firefox/43.0"','"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36"','"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:44.0) Gecko/20100101 Firefox/44.0"','"Mozilla/5.0 (Windows NT 6.1; rv:43.0) Gecko/20100101 Firefox/43.0"']
    # The range of values from which the time period
    # for a short siesta between agent activities
    # will be chosen
    min_delay = 5
    max_delay = 20
    ### The set of probabilities (that must add up to 1.0)
    ### for each of the options available to Browser agents
    ### for next steps after browsing to a Web site
    # Option 1: Choose randomly from among available navigation
    #           links, if any, to follow from  the current page
    prob_next = 0.4
    # Option 2: Sit this round out by "staying on the current page"
    prob_wait = prob_next + 0.2
    # Option 3: Like hitting the browser back button, visit the
    #           the previous page in the Browser's history
    prob_back = prob_wait + 0.2
    # Option 4: Randomly select one of the available URLs and
    #           visit the index page
    prob_new = prob_back + 0.2
    
    def __init__(self, urls, rank, group=None, run=False):
        if urls == None or not isinstance(urls, list):
            print('ERROR: No Web sites to browse!')
            sys.exit(1)
        threading.Thread.__init__(self, group)
        self.urls = urls[:]
        self.whoami = 'browser_' + str(rank)
        self.stopEvent = threading.Event()
        # Pick a user-agent
        self.ua = random.choice(Browser.uas)
        # The Browser's "history"
        self.history = []

    def stop(self):
        '''
        This method will be called by the driver script
        when Ctrl-c is pressed
        '''
        self.stopEvent.set()

    def run(self):
        '''
        This method is called when the driver script calls
        the Browser thread's start() method
        '''
        # Pick a random URL from the list
        domain = random.choice(self.urls)
        if 'http' not in domain:
            url = 'http://' + domain + '/'
        else:
            url = domain
        wait = False
        # Check whether the stopEvent has been set
        # each time through the loop
        while not self.stopEvent.is_set():
            # Take a break (to read the current page)
            siesta = random.randint(Browser.min_delay, Browser.max_delay)
            # If a wait is probablistically selected, double
            # the timeout period chosen above
            if wait:
                wait = False
                siesta *= 2
            time.sleep(siesta)
            # These lists will hold embedded and
            # navigation links found on the Web page
            # to be visited
            self.csslinks = []
            self.imagelinks = []
            self.scriptlinks = []
            self.navlinks = []
            # Grab the selected page
            doc_type = 'html'
            headers = self.build_headers(self.ua, doc_type)
            print('{} {:>10}: "Getting {}'.format(time.strftime("%H:%M:%S"), self.whoami, url))
            try:
                # Using a Session object, rather than
                # grabbing the page directly, gives
                # us the opportunity to reuse its
                # TCP session to request the embedded
                # links, such as images, CSS, etc.
                session = requests.Session()
                r = session.get(url, headers=headers)
                # Break the page into lines for processing
                html = r.text.split('\n')
                self.gatherlinks(html)
                # Now go and request all the embedded links
                self.visitlinks(url, session, self.csslinks, self.imagelinks, self.scriptlinks)
            except Exception as e:
                print('{} {:>10s}: Error: {}'.format(time.strftime("%H:%M:%S"), self.whoami, e))

            # Okay, we've done this page. Now what?
            # Pick a number between 0 and 1.0
            chance = random.random()
            # The goal here is to not repeat a page
            # load because the current path is '/' or ' '
            # and index.html is in the navlinks
            try:
                o = urlparse(url)
                if o.path in (' ', '/'):
                    path = 'index.html'
                else:
                    path = o.path
            except:
                pass
            # Now decide what to do based on the number we picked above
            # Do we visit a link found on the current page?
            if chance <= Browser.prob_next and len(self.navlinks) > 0:
                # Don't choose the page we're currently on
                if path in self.navlinks:
                    self.navlinks.remove(path)
                pick = random.choice(self.navlinks)
                if 'http' not in pick:
                    o = urlparse(url)
                    new_url = o.netloc + '/' + pick
                else:
                    new_url = pick
                # Now, pick a link to visit
                new_url = random.choice(self.navlinks)
                # This is for local links, to add the FQDN
                # in front of the new path
                if 'http' not in new_url:
                    new_url = o.netloc + '/' + new_url
            # Do we just hang out on the current page?
            elif chance <= Browser.prob_wait:
                wait = True
                # If so, pick a new site to visit
                # when we wake up. Otherwise, we'll
                # just end up right back where we are
                new_url = self.get_new_url(url)
            # Do we hit the 'back' button?
            elif chance <= Browser.prob_back and len(self.history) > 0:
                new_url = self.history[-1]
            # Or do we pick another site to visit?
            else:
                new_url = self.get_new_url(url)
            # Whatever we chose, put the current
            # URL at the end of our history
            self.history.append(url)
            url = new_url
            # Add the scheme up front for local links
            if 'http' not in url:
                url = 'http://' + url
        # If we've left the loop, it's time to go home
        print('{} {:>10s}: Stop event has been set. I\'m outta here!'.format(time.strftime("%H:%M:%S"), self.whoami))

    # Find a new site to visit
    def get_new_url(self, url):
        while True:
            new_url = random.choice(self.urls)
            if new_url not in url:
                return new_url
            
    # Build a dictionary of HTTP headers to make
    # the Browser look more like a real boy.
    # Some of these depend on what sort of
    # document we're going to get
    def build_headers(self, user_agent, doctype, url=None):
        headers = {}
        headers['User-Agent'] = user_agent
        if doctype == 'html':
            accept_string = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        elif doctype == 'image':
            accept_string = 'image/png,image/*;q=0.8,*/*;q=0.5'
        elif doctype == 'css':
            accept_string = 'text/css,*/*;q=0.1'
        else:
            accept_string = '*/*'
        headers['Accept'] = accept_string
        headers['Accept-Language'] = 'en-US,en;q=0.5'
        headers['Accept-Encoding'] = 'gzip, deflate'
        headers['DNT'] =  '1'
        # For embedded links
        if url:
            headers['Referer'] = url
        headers['Connection'] = 'keep-alive'
        return headers
    # Get the actual path, based on the link type.
    # Currently supporting css, nav, img and js.
    # Everything not css or nav is assumed to be
    # img or js.
    def get_link(self, link_type, line):
        if link_type in ('css', 'nav'):
            l = re.search('href( )*=( )*["\'][^"\']+["\']',line)
        elif link_type in ('image', 'script'):
            l = re.search('src( )*=( )*["\']+[^"\']+["\']', line)
        else:
            pass
        if l:
            link = re.search('["\'][^"\']+["\']', l.group(0))
            return link.group(0)[1:-1]
        return None

    def visitlinks(self, url, session, csslinks, imagelinks, scriptlinks):
        'Get embedded links: css, etc'
        # Get the CSS
        headers =  self.build_headers(self.ua, 'css', url)
        o = urlparse(url)
        for link in csslinks:
            link = link.replace('../', '')
            if 'https://' in link or 'http://' in link:
                continue
            my_url = 'http://' + o.netloc + '/' + link
            #s = requests.get(my_url, headers=headers)
            s = session.get(my_url, headers=headers)
        # Now the images
        headers =  self.build_headers(self.ua, 'image', url)
        for link in imagelinks:
            link = link.replace('../', '')
            if 'https://' in link or 'http://' in link:
                continue
            my_url = 'http://' + o.netloc + '/' + link
            #s = requests.get(my_url, headers=headers)
            s = session.get(my_url, headers=headers)
        # Now the js
        headers =  self.build_headers(self.ua, 'script', url)
        stop = False
        for link in scriptlinks:
            link = link.replace('../', '')
            if 'https://' in link or 'http://' in link:
                continue            
            my_url = 'http://' + o.netloc + '/' + link
            #s = requests.get(my_url, headers=headers)
            s = session.get(my_url, headers=headers)

    def gatherlinks(self, html):
        'Parse the input and gather all the embedded and clickable links'
        for line in html:
            line = line.strip()
            # Ignore HTML comments
            if re.search('<!--', line):
                continue
            # CSS links
            c = re.search('<link(.)+rel( )*=( )*["\']stylesheet', line)
            # Navigation links
            n = re.search('<a(.)+href( )*=( )*["\'][^#"\']+["\']', line)
            # Image links
            i = re.search('<img(.)+src', line)
            # JS scripts
            s = re.search('<script(.)+src( )*=( )*["\']',line)
            if c:
                link = self.get_link('css', line)
                if link:
                    self.csslinks.append(link)
            if n:
                link = self.get_link('nav', line)
                # Turn relative into absolute links
                link = link.replace('../', '')                
                # One hopes these sorts of links will soon be gone from BetaPort sites
                if link and link not in self.navlinks and 'javascript' not in link and 'google' not in link:
                    self.navlinks.append(link)
            if i:
                link = self.get_link('image', line)
                if link:
                    self.imagelinks.append(link)
            if s:
                link = self.get_link('script', line)
                if link:
                    self.scriptlinks.append(link)
