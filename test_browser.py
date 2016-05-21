#/usr/bin/env python3
import threading, sys, time
from browser import Browser
from argparse import ArgumentParser

def main(num_agents, urls):
    # The list of URLs for agents to visit. 
    if urls == []:
        with open('urls.txt') as f:
            for line in f.readlines():
                if line.startswith('#') or line.startswith(';'):
                    continue
                urls.append(line.strip())
    # A list of browsing-agent threads
    agents = []
    for i in range(1, num_agents + 1):
        try:
            print('{}: Spawning browser agent #{}'.format(time.strftime("%H:%M:%S"), i))
            agents.append(Browser(urls, i))
            agents[-1].start()
        except Exception as e:
            print('Error: unable to start thread for browser agent #{}: {}'.format(i, e))

    while True:
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print('{}: Received kill signal, so exiting'.format(time.strftime("%H:%M:%S")))
            for agent in agents:
                agent.stop()
            for agent in agents:
                agent.join()
            sys.exit(0)

if __name__=='__main__':
    parser = ArgumentParser(description='Randomly browse a given list of URLs using a number of probability-driven Browser agents')
    parser.add_argument('urls', nargs='*', default=None, help='A Python list of URLs to browse (default: %(default)s)')
    parser.add_argument('-n', '--num_agents', type=int, default=10, help='Number of browser agents (default: %(default)s)')
    args = parser.parse_args()
    main(args.num_agents, args.urls)
