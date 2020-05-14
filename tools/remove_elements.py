import random
import xml.etree.ElementTree
from pyexcel_ods3 import get_data # noqa
import math

if __name__ == "__main__":
  locations = ['sp', 'ny']
  base_folder = '../docker-sumo-interscity-spres-ev-scenarios/defined'

  random.seed(42)

  for location in locations:
    print(location)

    file_tmp = open(location+'-evs.txt','r')
    evs = [ ev.split()[0] for ev in file_tmp.readlines() ]
    file_tmp.close()   

    partial_data = get_data(location+'-scenarios-size.ods')

    veh_types = ['passenger', 'truck', 'motorcycle']

    
    for i in range(1,5):
      col = 1
      for v in veh_types:
        print(v)
        print(i)
        print(col)
        n_vehs_5 = float(partial_data['Sheet1'][5][col])
        print(n_vehs_5)
        n_vehs_i = float(partial_data['Sheet1'][i][col])
        print(n_vehs_i)
        col = col + 1

        vehs_to_remove = math.ceil((1-(n_vehs_i/n_vehs_5))*n_vehs_5)

        scenario_folder = base_folder+'/'+location+'/'+location+'-'+str(i)

        xml_file = xml.etree.ElementTree.parse(scenario_folder+'/osm.'+v+'.trips.xml')
        root = xml_file.getroot()
        els = [ el.attrib['id'] for el in xml_file.findall('trip') if el.attrib['id'] not in evs]
        els = random.sample(els,vehs_to_remove)
        #print(els)

        remove_els = [ el for el in xml_file.findall('trip') if el.attrib['id'] in els]
        for el in remove_els:
          root.remove(el)
        xml_file.write(scenario_folder+'/osm.'+v+'.trips.xml')


        xml_file = xml.etree.ElementTree.parse(scenario_folder+'/osm.'+v+'.rou.xml')
        root = xml_file.getroot()
        remove_els = [ el for el in xml_file.findall('vehicle') if el.attrib['id'] in els ]
        for el in remove_els:
          root.remove(el)
        xml_file.write(scenario_folder+'/osm.'+v+'.rou.xml')


      



