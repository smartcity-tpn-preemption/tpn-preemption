import xml.etree.ElementTree
from operator import or_
import functools

if __name__ == "__main__":
  location = 'ny'
  base_scenario = '5'
  base_folder = '../interscity-spres-ev-scenarios/defined'


  scenario = base_folder+'/'+location+'/'+location+'-'+base_scenario

  osm_passenger_rou = xml.etree.ElementTree.parse(scenario+'/osm.passenger.rou.xml').getroot()
  net_file = xml.etree.ElementTree.parse(scenario+'/osm.net.xml').getroot()

  edges_with_tl = {}
  number_of_tls_x_evs = {}

  path = './connection[@tl]'

  connections = net_file.findall(path)

  for connection in connections:
    edge_from = connection.get('from')
    edge_to = connection.get('to')
    tl = connection.get('tl')

    if edge_from not in edges_with_tl:
      edges_with_tl[edge_from] = set()

    if edge_to not in edges_with_tl:
      edges_with_tl[edge_to] = set()

    edges_with_tl[edge_from].add(tl)
    edges_with_tl[edge_to].add(tl)

  for vehicle in osm_passenger_rou.findall('vehicle'):
    id = vehicle.attrib['id']
    my_tls = set()
    edges = vehicle.findall('route')[0].attrib['edges'].split(' ')
    for edge in edges:
      if edge in edges_with_tl:
        my_tls = my_tls.union(edges_with_tl[edge])

    tls_n = len(my_tls)

    if tls_n not in number_of_tls_x_evs:
      number_of_tls_x_evs[tls_n] = []

    number_of_tls_x_evs[tls_n].append(id)

  for i in [5, 20, 35, 50, 65]:
    print(number_of_tls_x_evs[i][ int(len(number_of_tls_x_evs[i])/2) ])
