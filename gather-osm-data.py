#!/bin/python

"""
I'm not saying this code is clean.
But I am saying that it works.
Requires OSMPythonTools package to be installed:
https://github.com/mocnik-science/osm-python-tools
"""


from OSMPythonTools.api import Api
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from OSMPythonTools.nominatim import Nominatim
import json
import os

edges = dict()
nodes = dict()

"""
edges {
    997009917: 50,
    997009918: 40,
    ...
}
"""
"""
nodes {
    9206246933: [997009917,997009918],
    9206246932: [997009917,997009918],
}
"""

def calc_capacity(entry):
    weight = 0
    multiplier = 1
    if 'maxspeed' in entry['tags'].keys():
        weight += int(entry['tags']['maxspeed'].split(' ')[0])
    else:
        weight += 25
    if 'lanes' in entry.keys():
        weight += entry['lanes'] * 10
    else:
        weight += 20
    if entry['tags']['highway'] == 'primary':
        multiplier = 2
    elif entry['tags']['highway'] == 'secondary':
        multiplier = 1.5
    return round(weight * multiplier * 2) / 2


# Get the majority of roads in the Blacksburg area

api = Api()
nominatim = Nominatim()
areaId = nominatim.query("Blacksburg, Virginia").areaId()
overpass = Overpass()
query = overpassQueryBuilder(area=areaId, elementType='way', selector='"highway"~"^(primary|secondary|residential|tertiary)$"', out='body')
result = overpass.query(query)


# Parse the JSON response
# Create initial nodes and edges
for elem in result._elements:
    if elem._json['id'] not in edges.keys():
        edges[elem._json['id']] = calc_capacity(elem._json)
    for node in elem._json['nodes']:
        if node not in nodes.keys():
            nodes[node] = set()
            nodes[node].add(elem._json['id'])
        else:
            nodes[node].add(elem._json['id'])

# Delete nodes that are only connected to one edge
# These are irrelevant data points along a road
# Like bus stops, etc.
# Or alternately, useless points on a dead end
nodecopy = dict(nodes)
for elem in nodecopy:
    if len(nodecopy[elem]) < 2:
        del nodes[elem]
nodecopy = dict(nodes)
for elem in nodecopy:
    nodes[elem] = list(nodecopy[elem])


# A single road may connect multiple nodes
# Count how many nodes lie on a single edge
# If it's more than 2, we need to split the edge into smaller edges
edgecount = dict()
for elem in nodes:
    for elem2 in nodes[elem]:
        if elem2 not in edgecount.keys():
            edgecount[elem2] = 1
        else:
            edgecount[elem2] += 1

bad_edges = [x for x in edgecount if edgecount[x] > 2]

# Given these misbehaving edges, break it into smaller chunks
# The new edge labels are just multiplied by 10 plus a constant
# Nodes in the original result are usually in order up/down a street
# So physical reality shouldn't be altered too much
# Re-attach nodes to these newly split edge pieces.
for edge in bad_edges:
    lastnode = ""
    tmp = [result._elements[x]._json for x in range(0, len(result._elements)) if result._elements[x]._json['id'] == edge][0]
    counter = 0
    nodeused = False
    last_valid_node = ""
    for i in range(0, len(tmp['nodes'])):
        this_node = tmp['nodes'][i]
        
        if this_node not in nodes.keys():
            continue
        if edge not in nodes[this_node]:
            continue
        last_valid_node = nodes[this_node]
        nodes[this_node].remove(edge)

        nodes[this_node].append(edge * 10 + counter)
        edges[edge * 10 + counter] = edges[edge]
        
        if counter == 0:
            counter += 1
            continue
        else:
            counter += 1
            nodes[this_node].append(edge * 10 + counter)
    del(edges[edge])
        
# Check again, just to be safe
edgecount = dict()
for elem in nodes:
    for elem2 in nodes[elem]:
        if elem2 not in edgecount.keys():
            edgecount[elem2] = 1
        else:
            edgecount[elem2] += 1

bad_edges = [x for x in edgecount if edgecount[x] > 2]

print(len(bad_edges))

# Check if the procedure has created any more orphaned nodes, and remove
nodecopy = dict(nodes)
for elem in nodecopy:
    if len(nodecopy[elem]) < 2:
        del nodes[elem]
nodecopy = dict(nodes)
for elem in nodecopy:
    nodes[elem] = list(nodecopy[elem])

# Begin dumping to file.
# One file for nodes, one for edges, and another combined representation.
fh = open("nodes.json", "w")
json.dump(nodes, fh)
fh.close()

fh = open("edges.json", "w")
json.dump(edges, fh)
fh.close()
print(len(edges))

tuples = dict()
for node in nodes:
    for edge in nodes[node]:
        stuff = [x for x in nodes if edge in nodes[x]]
        if len(stuff) == 1:
            continue
        pair = [x for x in stuff if x != node][0]
        #print(pair)
        
        if node < pair:
            x = (node, pair, edge)
        else:
            x = (pair, node, edge)
        tuples[x] = ""
fh =  open("node-edge-pairs.json", "w")
json.dump(list(tuples.keys()), fh)
fh.close()