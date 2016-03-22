#!/usr/bin/env python

from netaddr import IPNetwork
from selenium import webdriver
from time import sleep
from bs4 import BeautifulSoup

# Install http://phantomjs.org/download.html
# pip install selenium beautifulsoup4 netaddr
# ipcheck.py -- checks and prints out ip reputation using mxtoolbox for specific subnet

NET = '52.70.21.0/24'
URL = 'http://mxtoolbox.com/SuperTool.aspx?action=blacklist%3a{ip}&run=toolpage'


def main():
    for ip in IPNetwork(NET):
        browser = webdriver.Firefox()
        browser.get(URL.format(ip=ip))
        sleep(3)
        page_source = browser.page_source
        browser.quit()
        soup = BeautifulSoup(page_source.encode('utf-8'))
        table = soup.find('table', 'tool-result-table')
        for td in table.find('td'):
            if 'OK' in td.parent.text or 'TIMEOUT' in td.parent.text:
                print ip, 'OK'
                continue
            print ip, 'FAIL'


if __name__ == '__main__':
    main()
