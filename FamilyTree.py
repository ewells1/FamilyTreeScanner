import requests
import bs4
import re
import json

from private import username, password, root_person_link
CURRENT_YEAR = 2017


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
        # print(self.root_person)  # debug
        tree.close()

    '''Scrapes Ancestry.com, starting at root_person_link, to build family tree'''
    def generate_tree(self, root_person, user, pw):
        self.session = requests.session()
        self.people = {}
        login_data = {'username': user, 'password': pw, 'submit': 'loginButton'}
        self.session.post('https://www.ancestry.com/secure/login?signUpReturnUrl=https%3A%2F%2Fwww.ancestry.com%2Fcs%2Foffers%2Fsubscribe%3Fsub%3D1', data=login_data)

        self.add_person(root_person)

    '''Adds people recursively, starting with the given root person
       Stores information about each person and adds relatives not already in the tree'''
    def add_person(self, person_link):
        person = {}
        source = self.session.get(person_link)
        soup = bs4.BeautifulSoup(source.text, 'lxml')

        self.people[get_id_from_url(person_link)] = {}
        person['name'] = re.search(r'>(.+)<', str(soup('h1', attrs={'class': 'userCardTitle'}))).group(1)
        print(person['name'])  # debug

        person['parents'] = []
        person['siblings'] = []
        person['spouses'] = []
        person['children'] = []
        family = [str(member) for member in soup.find_all('a', {'class': 'factItemFamily'})]
        # print(family)  # debug
        for member in family:
            link = get_url_from_html(member)
            person_id = get_id_from_url(link)
            if 'ResearchParent' in member:
                person['parents'].append(person_id)
            elif 'ResearchSibling' in member:
                person['siblings'].append(person_id)
            elif 'ResearchSpouse' in member:
                person['spouses'].append(person_id)
            elif 'ResearchChild' in member:
                person['children'].append(person_id)
            else:
                # If we get here, I've made a bad assumption about my input
                print('problem with add person', person['name'], member)
            if person_id not in self.people:
                self.add_person(link)

        birth = soup.find('span', attrs={'class': 'birthDate'})
        if birth:
            person['birth_year'] = extract_year(str(birth))
        else:
            person['birth_year'] = 'Unknown'

        death = soup.find('span', attrs={'class': 'deathDate'})
        if death:
            person['death_year'] = extract_year(str(death))
        else:
            living = soup.find('span', attrs={'class': 'livingText'})
            if living:
                person['death_year'] = 'Living'
            else:
                person['death_year'] = 'Unknown'

        person['sex'] = str(soup.find(string=['Female', 'Male']))

        # print(person)  # debug
        self.people[get_id_from_url(person_link)] = person

    '''Saves the current family tree as a json file'''
    def save(self):
        family_tree = open('FamilyTree.json', 'w')
        json.dump(self.people, family_tree, indent=4)
        family_tree.close()

    '''Returns the number of total people in the tree'''
    def num_people(self):
        return len(self.people)

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


'''Extracts a person's ID from the URL for their profile'''
def get_id_from_url(url):
    person_id = re.search(r'person/(\d+)', url).group(1)
    return person_id


'''Extracts the URL for a person from a piece of html returned from bs4'''
def get_url_from_html(html):
    href = re.search(r'href="(.+?)"', html)
    return href.group(1)


'''Extracts a year from a piece of html returned from bs4'''
def extract_year(html):
    year = re.search(r'\d{4}', html)
    if year:
        return int(year.group(0))
    else:
        print('problem in extract year', html)  # debug - to see if this is something that requires more error handling


if __name__ == '__main__':
    # print(get_id_from_url(root_person_link))  # debug - to check if this function works correctly
    ft = FamilyTree()
    # ft.generate_tree(root_person_link, username, password)
    ft.load_tree()
    print(ft.num_people(), 'people in this tree\n')
    # ft.save()
    ft.sanity_check()
