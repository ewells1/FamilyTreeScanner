Reads in an ancestry.com family tree and builds a python representation of it. Once the tree is converted to a
FamilyTree object, it can be scanned for common errors and saved in json format.

In my implementation, people are represented as dictionaries and then accessed from the main dictionary with the ID
ancestry assigns them. Relationships to other people in the tree are represented as lists of ID numbers like an
adjancency list. The family tree is assumed to be a connected graph and traversal requires the ID of a root person to
start from, although it doesn't really matter which person this is since traversal goes in all directions.

To run, a file named private.py is required with the variables username, password, and root_person_link to be set to the
username and password for an ancestry.com account and the url for the "Facts" page of a person the account has
permission to view.

With my tree of over 1600 people, building the tree takes a little while but scanning is almost instant.