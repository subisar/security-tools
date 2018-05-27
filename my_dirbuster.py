from sys import argv
import argparse
from queue import Queue
import sys
import os
import threading
import curses
import requests
import re
import time
from collections import defaultdict

NUM_THREADS = 1
SLEEP_TIME = 0.1
CODES = defaultdict(int)

STATI = {
    200: 'OK',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    304: 'Not Modified',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    410: 'Gone',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    503: 'Service Unavailable',
    550: 'Permission denied',
}

for key, val in STATI.items():  # Populate some default values so it doesn't start off looking like trash
    CODES[key] = 0

class Buster():

    def __init__(self, **kwargs):
        super(Buster, self).__init__()
        self.target = kwargs.get('target', None)
        self.directory_list = kwargs.get('directory_list')
        self.results_file = kwargs.get('results_file')
        self.auth_user = kwargs.get('auth_user')
        self.auth_pwd = kwargs.get('auth_pwd')
        self.proxies = kwargs.get('proxies', {})
        self.cookies = kwargs.get('cookies', {})
        self.headers = kwargs.get('headers')
        self.lines = kwargs.get('lines')
        self.remaining = kwargs.get('remaining')
        self.verbose = kwargs.get('verbose', False)

    def do_request(self, host, stdscr):
        
        percent_complete = (self.remaining*100) /self.lines
        url = self.target + '/' + str(host.rstrip())

        stdscr.clear()
        stdscr.addstr(0, 0, "{} of {} remaining ({:0.2f}%) - {}\nMETHOD | COUNT".format(self.remaining, self.lines, percent_complete, url))

        out = ""
        for key, val in CODES.items():
            out += "\r{0:{fill}{align}7}".format(key, fill=" ", align="^")
            out += "|{0:{fill}{align}1} Results\n".format(val, fill=" ", align="<")

        stdscr.addstr(2, 0, out)
        stdscr.refresh()
        try: 
            response = requests.get(url, cookies=self.cookies, proxies=self.proxies, auth=(self.auth_user, self.auth_pwd), headers=self.headers)
            method = 'GET'
            code = response.status_code
            if code not in [404, 429]:
                out = '<a href="{}/{}">{}/{} {} returned {}'.format(self.target, host, self.target, host, method, code)
                self.write_result(out);

            CODES[code] += 1
            self.remaining -= 1

        except requests.ConnectionError as e:
            stdscr.addstr(1, 0, R + "\n ERROR: Connection Error - Check target is correct or exists" + W)

    def write_result(self, result):
        pid = os.getpid()
        with open('results_{}.txt'.format(pid), 'a') as results_file:
            results_file.write(result)

class ThreadUrl(threading.Thread):
    def __init__(self, queue, kwargs, stdscr):
        threading.Thread.__init__(self)
        self.queue = queue
        self.buster = Buster(**kwargs)
        self.stdscr = stdscr

    def run(self):
    
        while True:
            try:                                                                                                    # NEED TO EXIT THE THREADS AND SCRIPT BETTER
                host = self.queue.get()
                self.buster.do_request(host, self.stdscr)
                self.queue.task_done()
                time.sleep(SLEEP_TIME)
            except (SystemExit):
                stdscr.addstr(0, 0, R + '\n Shutting down! ' + W + '....' )


def main():

    stdscr = curses.initscr()
    kwargs = init(stdscr)
    with open(kwargs['directory_list']) as f:
        directories = f.readlines()

    queue = Queue()
    kwargs['remaining'] = len(directories)
    kwargs['lines'] = len(directories)

    for i in range(NUM_THREADS):

        t = ThreadUrl(queue, kwargs, stdscr)
        t.setDaemon(True)
        t.start()

    for host in directories:
        try:
            queue.put(host)
            queue.join()
        except (KeyboardInterrupt, SystemExit):
            stdscr.addstr(0, 0, '\n Ctrl+C Detected!\n Shutting down!')
            curses.nocbreak()
            stdscr.keypad(0)
            curses.echo()
            curses.endwin()
            sys.exit()

def init(stdscr):

    kwargs = defaultdict(None)
    parser = argparse.ArgumentParser(
                    description='A Python version of DirBuster',
                    epilog='Dir-Xcan is a multi threaded python application designed to brute force directories on web/application servers.')

    parser.add_argument('-s', action="store", help='Website Domain or IP')
    parser.add_argument('-d', action="store", help='Directory word list', default="directorylist.txt")
    parser.add_argument('-o', action="store", help='Output file name (HTML)', default="Dir-Xcan-results.html")
    # parser.add_argument('-n', action="store", help='Number of threads', default="5")
    parser.add_argument('-p', action="store_true", help='Proxy address and port (host:port)')
    parser.add_argument('-a', action="store", help='Authentication BasicHTTP(username:password)')
    parser.add_argument('-c', action="store", help='use a previously established sessions cookie', default=None)
    parser.add_argument('-u', action="store", help='User-Agent', default="Mozilla/5.0")
    parser.add_argument("-V", action="store_true", help="Output information about new data.")

    try:
        args = vars(parser.parse_args())

    except IOError as msg:
        parser.error(str(msg))

    if not args['s']:

        stdscr.addstr(0,0, "You need to specify a target url with -s")
        exit()
    kwargs['target'] = args['s']
    if not kwargs['target'].startswith("http"):
        print(R + ' Please include the http:// or https:// parts' + W)

    kwargs['directory_list'] = args['d']
    kwargs['results_file'] = args['o']
    kwargs['user_agent'] = args['u']
    if args['p']:
        kwargs['proxies'] = {
            "http": "http://sam.scheding1:winter@proxy.det.nsw.edu.au:8080",
            "https": "https://sam.scheding1:winter@proxy.det.nsw.edu.au:8080",
            }

    if args['a']:
        kwargs['auth_user'], kwargs['auth_pwd'] = args['a'].split(':', 1)
    if args['u']:
        kwargs['headers'] = { 'User-Agent': kwargs['user_agent'], }
    if args['c']:
        print("Cookie thing not implemented")
        exit()
    return kwargs

def mapcount(self, listing):
    lines = 0
    with open(listing) as f:
        lines = sum(1 for line in f)
    return lines

if __name__ == '__main__':
    main()