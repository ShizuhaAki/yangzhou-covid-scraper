# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from bs4 import BeautifulSoup
from urllib.request import urlopen
import re
import sys  # for sys.stderr


class Case:
  def __init__(self, case_id = -1, gender = -1, close_contact_id = -1, age = -1, address = '', trace = ''):
    self.case_id = case_id
    self.close_contact_id = close_contact_id
    self.gender = gender    # -1 for not specified, 0 for male, 1 for female, will add LGBTQIA support should the need arise
    self.age = age
    self.address = address
    self.trace = trace

  def __str__(self):
    return "Confirmed case #{}\n\tGender: {}\n\tAge: {}\n\tHome address: {}\n\tClose contact of case #{}\n\tActivities: {}\n".format \
     (self.case_id, self.gender, self.age, self.address, self.close_contact_id, self.trace)
  
  def csv(self):
    return '{},{},{},{},{},{}\n'.format(self.case_id, self.gender, self.age, self.address, self.close_contact_id, self.trace)

  def is_empty(self):
    return self.gender == -1 and self.close_contact_id == -1 and self.age == -1 and self.address == '' and self.trace == ''


def dbg_print(s, level = 'DEBUG'):
  """Debug information

  Args:
      s (string): information to print
      level (string): level of the message, defaults to 'DEBUG'
  """
  print('[{}] {}'.format(level, s), file = sys.stderr)
  

def create_soup(url):
  """Initiates a bs4 object

  Args:
      url (string): the URL to work with

  Returns:
      BeautifulSoup: a bowl of soup
  """
  html = urlopen(url)
  dbg_print('soup created for {}'.format(url))
  return BeautifulSoup(html.read(), 'html.parser')


def extract_number(s, i=0):
  """Extracts the i-th number from string s

  Args:
      s (string): the string to extract from
      i (int): the index of the number

  Returns:
      int: the integer extracted, or None if not found
  """
  d = re.search('[0-9]+', s)
  return int(d[i])


def find_cases(soup: BeautifulSoup):
  """Find COVID-19 confirmed cases

  Args:
      soup (BeautifulSoup): the soup to work with

  Returns:
      List: a list of all cases
  """
  all_cases = []
  spans = soup.find_all('span')
  dbg_cnt = 0
  dbg_found_cnt = 0
  flag = False
  for span in spans:
    dbg_cnt += 1
    text = span.get_text()
    if flag:
      all_cases[-1].trace = text
      flag = False
    if re.match('确诊病例[0-9]+', text):
      dbg_found_cnt += 1
      case = Case()
      case.case_id = extract_number(text)
      # === begin looking for close contacts
      ccres = re.search('[0-9]+密接', text)
      if ccres:
        ccnum = extract_number(ccres[0])
        case.close_contact_id = int(ccnum)
      else:
        dbg_print('no close contact found for {}'.format(case.case_id), 'WARN ')
        case.close_contact_id = -1  # no close contact
      # === end looking for close contact
      # === begin looking for gender
      gres = re.search('男|女', text)
      if not gres:
        dbg_print(
            'unexpected: did not find gender for {}, check source format?'.format(case.case_id), 'ERROR')
      else:
        if gres[0] == '男':
          case.gender = 0
        else:
          case.gender = 1
      # === end looking for gender
      # === begin looking for age
      ageres = re.search('[0-9]+岁', text)
      if not ageres:
        dbg_print(
            'unexpected: did not find age for {}, check source format?'.format(case.case_id), 'ERROR')
      else:
        age = extract_number(ageres[0])
        case.age = age
      # === end looking for age
      # === begin looking for home address
      ares = re.search('现住(.*?)。', text)
      if not ares:
        dbg_print(
            'unexpected: did not find address for {}, check source format?'.format(case.case_id), 'ERROR')
      else:
        address = ares[0][2:-1]
        case.address = address
      # === end looking for home address
      all_cases.append(case)
    if re.match('活动轨迹', text):
      flag = True  # the next span will be our activity
    
      
  dbg_print('Total {} spans iterated, found {}'.format(dbg_cnt, dbg_found_cnt))
  return all_cases
      
      
def compile_url_list(entry_url):
  """Compiles a URL list from entry_url

  Args:
      entry_url (string): the first url to visit

  Returns:
      List: all urls
  """
  urllist = []
  soup = create_soup(entry_url)
  for a in soup.find_all('a'):
#    print(a)
    text = a.get_text()
    if re.match('[0-9]+月[0-9]+日扬州', text):
      href = a['href']
      urllist.append(href)
  dbg_print('Generated url list: {}'.format(str(urllist)), 'INFO ')
  return urllist


if __name__ == "__main__":
  start_url = 'https://mp.weixin.qq.com/s/tDD81B2sG72wznffKQFmmQ'
  urls = compile_url_list(start_url)
  urls.append(start_url)
  all_cases = []
  for url in urls:
    dbg_print('Parsing {}'.format(url), 'INFO ')
    soup = create_soup(url)
    cases = find_cases(soup)
    for case in cases:
      all_cases.append(case)
  all_cases.sort(key=lambda case:case.case_id)
  for case in all_cases:
    if not case.is_empty():
      print(case)
  with open('result.csv', 'w') as writer:
    writer.write('case_id,gender,age,address,close_contact,trace\n')
    for case in all_cases:
      if not case.is_empty():
        writer.write(case.csv())
  dbg_print('result saved to result.csv', 'INFO ')
  pass
