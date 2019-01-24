import requests
import re
import json

import bs4
import pandas

from private import *
CURRENT_YEAR = 2018


'''A Python representation of a family tree where people are represented as dictionaries and then accessed from the
   main dictionary with the ID ancestry assigns them. Relationships to other people in the tree are represented as
   lists of ID numbers like an adjancency list. Once a tree is created or loaded, it can be scanned for possible
   errors and inconsistencies.

   Stores the following information about each person:
       Name
       Parents
       Siblings
       Spouses
       Children
       Birth year
       Birth place
       Death year
       Sex
'''


class FamilyTree:
    def __init__(self):
        self.people = {}
        self.root_person = ''

    '''Loads a previously generated tree from a json file
       Assumes the json file was written by this program or at least has the same structure'''
    def load_tree(self, saved_tree='FamilyTree.json'):
        tree = open(saved_tree)
        self.people = json.load(tree)
        self.root_person = list(self.people.keys())[0]
        # print(self.people[self.root_person]['name'])  # debug
        # print(self.root_person)  # debug
        tree.close()

    '''Scrapes Ancestry.com, starting at root_person_link, to build family tree
       direct_ancestors_only ignores siblings for a smaller tree'''
    def generate_tree(self, root_person, user, pw, direct_ancestors_only=False):
        self.root_person = get_id_from_url(root_person)
        self.session = requests.session()
        self.people = {}
        login_data = {'username': user, 'password': pw, 'submit': 'loginButton'}
        self.session.post('https://www.ancestry.com/secure/login?signUpReturnUrl=https%3A%2F%2Fwww.ancestry.com%2Fcs%2Foffers%2Fsubscribe%3Fsub%3D1', data=login_data)

        self.add_person(root_person, direct_ancestors_only)

    '''Adds people recursively, starting with the given root person
       Stores information about each person and adds relatives not already in the tree'''
    def add_person(self, person_link, direct_ancestors_only=False):
        person = {}
        source = self.session.get(person_link)
        soup = bs4.BeautifulSoup(source.text, 'lxml')

        self.people[get_id_from_url(person_link)] = {}
        person['name'] = re.search(r'>(.+)<', str(soup('h1', attrs={'class': 'userCardTitle'}))).group(1)
        print(person['name'])  # debug

        person['parents'] = []
        person['spouses'] = []
        person['siblings'] = []
        person['children'] = []
        family = [str(member) for member in soup.find_all('a', {'class': 'factItemFamily'})]
        # print(family)  # debug
        for member in family:
            link = get_url_from_html(member)
            person_id = get_id_from_url(link)
            if 'ResearchParent' in member:
                person['parents'].append(person_id)
                if person_id not in self.people:
                    self.add_person(link, direct_ancestors_only)
            elif not direct_ancestors_only:
                if 'ResearchSibling' in member:
                    person['siblings'].append(person_id)
                elif 'ResearchSpouse' in member:
                    person['spouses'].append(person_id)
                elif 'ResearchChild' in member:
                    person['children'].append(person_id)
                else:
                    # If we get here, I've made a bad assumption about my input
                    print('problem with add person', person['name'], member)
                if person_id not in self.people:
                    self.add_person(link, direct_ancestors_only)

        birth = soup.find('span', attrs={'class': 'birthDate'})
        if birth:
            person['birth_year'] = extract_year(str(birth))
        else:
            person['birth_year'] = 'Unknown'
        birth_place = soup.find('span', attrs={'class': 'birthPlace'})
        if birth_place:
            person['birth_place'] = extract_text(str(birth_place))
            person['birth_coordinates'] = lat_and_long(person['birth_place'])
            # print(person['birth_place'])

        death = soup.find('span', attrs={'class': 'deathDate'})
        if death:
            person['death_year'] = extract_year(str(death))
        else:
            living = soup.find('span', attrs={'class': 'livingText'})
            if living:
                person['death_year'] = 'Living'
            else:
                person['death_year'] = 'Unknown'
        death_place = soup.find('span', attrs={'class': 'deathPlace'})
        if death_place:
            person['death_place'] = extract_text(str(death_place))
            person['death_coordinates'] = lat_and_long(person['death_place'])
            # print(person['death_place'])

        person['sex'] = str(soup.find(string=['Female', 'Male']))

        # print(person)  # debug
        self.people[get_id_from_url(person_link)] = person

    '''Saves the current family tree as a json file'''
    def save(self, outfile='FamilyTree.json'):
        family_tree = open(outfile, 'w')
        json.dump(self.people, family_tree, indent=4)
        family_tree.close()

    '''Returns the number of total people in the tree'''
    def num_people(self):
        return len(self.people)

    '''Returns the number of direct ancestors given a root person.
       If no root person given, assumes tree root person'''
    def num_direct_ancestors(self, root_person=None):
        if root_person is None:
            root_person = self.root_person
        # print(self.people[root_person]['name'])  # debug
        ret = 1
        for person in self.people[root_person]['parents']:
            ret += self.num_direct_ancestors(person)
        return ret

    '''Finds the length of the longest chain of ancestors from the root person'''
    def longest_line(self, root_person=None):
        if root_person is None:
            root_person = self.root_person
        # print(self.people[root_person]['name'])  # debug
        ret = 1
        for person in self.people[root_person]['parents']:
            ret += self.num_direct_ancestors(person)
        return ret

    '''Goes through people in tree checking for possible errors. Errors scanned for:
           Child born after a parent's death
           Child born before a parent is at least 14 or after mother turns 55
           People that lived over 100 years
           People born over 100 years ago marked as living
       Also want to add ability to find duplicates in spouses and children.
    '''
    def sanity_check(self):
        for person in self.people:
            name = self.people[person]['name'] + ' ' + str(self.people[person]['birth_year'])
            children = [self.people[child]['birth_year'] for child in self.people[person]['children']
                        if isinstance(self.people[child]['birth_year'], int)]

            if isinstance(self.people[person]['birth_year'], int):
                if len(children) > 0:
                    last_child = max(children)
                    first_child = min(children)
                    if self.people[person]['sex'] == 'Female' and last_child >= self.people[person]['birth_year'] + 55:
                        print(name, 'allegedly had a child at age',
                              int(last_child - self.people[person]['birth_year']))
                    if first_child <= self.people[person]['birth_year'] + 13:
                        print(name, 'allegedly had a child at age',
                              int(first_child - self.people[person]['birth_year']))

                if isinstance(self.people[person]['death_year'], int):
                    if self.people[person]['death_year'] - self.people[person]['birth_year'] >= 100:
                        print(name, 'allegedly lived', str(self.people[person]['death_year'] -
                                                           self.people[person]['birth_year']), 'years')
                    if len(self.people[person]['children']) > 0 and last_child > self.people[person]['death_year']:
                        print(name, 'allegedly had a child', int(last_child - self.people[person]['death_year']),
                              'years after their death')

                if self.people[person]['death_year'] == 'Living' and self.people[person]['birth_year'] <= CURRENT_YEAR - 100:
                    print(name, 'is allegedly still alive after', int(CURRENT_YEAR -
                                                                      self.people[person]['birth_year']), 'years')
            # TODO: Look for duplicates

    '''Returns a list of all lines that lead to the root person. Hopefully to be used for more mapping projects'''
    def family_paths(self, num_generations, root_person=None):
        if root_person is None:
            root_person = self.root_person
        ret = []
        parents = self.people[root_person]['parents']
        if num_generations > 1:
            for person in parents:
                for path in self.family_paths(num_generations - 1, person):
                    ret.append(path + [self.people[root_person]['birth_place']])
        if num_generations == 1 or len(parents) < 2:
            ret.append([self.people[root_person]['birth_place']])
        return ret

    '''Returns a dataframe with information about everyone in the tree excluding relationships to others in tree'''
    def dataframe(self, fields='all'):
        if fields == 'all':
            fields = ['name', 'birth_year', 'birth_place', 'death_year', 'sex']
        people = {field: [self.people[person][field] for person in self.people] for field in fields}
        print(people)
        ret = pandas.DataFrame(people)
        return ret

    '''Returns a dataframe specifically to be used for plotting birth places on a map'''
    def map_dataframe(self, num_generations, root_person=None):
        if root_person is None:
            root_person = self.root_person
        # latlong = lat_and_long(self.people[root_person]['birth_place'])
        latlong = self.people[root_person]['birth_coordinates']
        if latlong:
            row = pandas.DataFrame({'Name': self.people[root_person]['name'],
                                    'Generation': num_generations,
                                    'Lattitude': latlong[0],
                                    'Longitude': latlong[1]},
                                   index=[0])
        else:
            # print("Can't get coordinates for", self.people[root_person]['name'], "at",
            #       self.people[root_person]['birth_place'])  # debug - so I can go fix in my tree later
            row = pandas.DataFrame({})
        parents = self.people[root_person]['parents']
        if num_generations > 1:
            for parent in parents:
                row = pandas.concat([row, self.map_dataframe(num_generations-1, root_person=parent)])
        return row

    def get_people(self):
        return [person['name'] for person in self.people]

    def look_up_city(self, city):
        latlong = list(lat_and_long(city))
        for person in self.people.values():
            # print(person['name'], latlong, person['birth_coordinates'])
            if 'birth_coordinates' in person and person['birth_coordinates'] == latlong:
                print(person['name'], 'was born in', city, 'in', str(person['birth_year']))
            if 'death_coordinates' in person and person['death_coordinates'] == latlong:
                print(person['name'], 'died in', city, 'in', str(person['death_year']))

    def verify_with_book(self):
        pass


# Extracts a person's ID from the URL for their profile
def get_id_from_url(url):
    person_id = re.search(r'person/(\d+)', url).group(1)
    return person_id


# Extracts the URL for a person from a piece of html returned from bs4
def get_url_from_html(html):
    href = re.search(r'href="(.+?)"', html)
    return href.group(1)


# Extracts a year from a piece of html returned from bs4
def extract_year(html):
    year = re.search(r'\d{4}', html)
    if year:
        return int(year.group(0))
    else:
        print('problem in extract year', html)  # debug - to see if this is something that requires more error handling


# Extracts text from between html markup
def extract_text(html):
    loc = re.search(r'>(.+)</', html)
    if loc:
        return loc.group(1)
    else:
        print('problem in extract text', html)  # debug - to see if this is something that requires more error handling
        return 'Unknown'


# Uses google maps geocoder api to look up the lattitude and longitude of a city
def lat_and_long(address):
    url = 'http://open.mapquestapi.com/geocoding/v1/address'
    params = {'location': address, 'key': mapquest_key, 'inFormat': 'kvp', 'outFormat': 'json', 'thumbMaps': 'false'}
    r = requests.get(url, params=params)
    # print(r.json())
    results = r.json()['results']
    if len(results) > 0:
        loc = results[0]['locations'][0]['latLng']
        return loc['lat'], loc['lng']
    else:
        print(r.json())


if __name__ == '__main__':
    # print(get_id_from_url(root_person_link))  # debug - to check if this function works correctly
    ft = FamilyTree()
    # ft.generate_tree(root_person_link, username, password, direct_ancestors_only=True)
    ft.load_tree('FamilyTree.json')
    print(ft.num_people(), 'people in this tree\n')
    # print(ft.num_direct_ancestors(), 'direct ancestors\n')
    # ft.save()
    # ft.sanity_check()
    # paths = ft.family_paths(30)
    # print('Shortest path found:', min(len(p) for p in paths))
    # print('Longest path found:', max(len(p) for p in paths))
    # chart = ft.dataframe()
    # print(chart)
    # print(lat_and_long('Granby, Massachusetts, USA'))

    while True:
        city = input('Look up a city: ')
        if city.lower() == 'quit':
            break
        ft.look_up_city(city)
        print()
