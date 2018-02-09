Reads in an ancestry.com family tree and builds a python representation of it. Once the tree is converted to a
FamilyTree object, it can be scanned for common errors and saved in json format.

Recently, I also added in the ability to put all the information in the tree into a pandas dataframe. There are two
functions for this, one with basic information stored in the tree and one with information for mapping birth places
in FamilyPaths.ipynb. Mapping requires a google maps geocoder api key and pixiedust.

In my implementation, people are represented as dictionaries and then accessed from the main dictionary with the ID
ancestry assigns them. Relationships to other people in the tree are represented as lists of ID numbers like an
adjancency list. The family tree is assumed to be a connected graph and traversal requires the ID of a root person to
start from, although it doesn't really matter which person this is since traversal goes in all directions when
direct_ancestors_only is turned off.

To run, a file named private.py is required with the variables username, password, and root_person_link to be set to the
username and password for an ancestry.com account and the url for the "Facts" page of a person the account has
permission to view. Google_api_key must also be set in order to use the map_dataframe method.

With my tree of over 1600 people, building the tree takes a little while but scanning is almost instant.