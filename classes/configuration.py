from sumolib import checkBinary  # noqa
import traci  # noqa

from classes.logger import Logger

import xml.etree.ElementTree
import numpy as np

class Configuration():

  @property
  def edges(self):
    return self._edges

  @property
  def edges_order(self):
    return self._edges_order

  @property
  def edges_with_tl(self):
    return self._edges_with_tl

  @property
  def tls(self):
    return [self._edges[edge]['tl']['name'] for edge in self._edges_with_tl]

  def set_staticdynamic(self):
    self.staticdynamic = True

  def __init__(self, ev, folder):
    self._folder = folder
    self._ev = ev
    self._logger = Logger(self.__class__.__name__).get()

    self._net_file = xml.etree.ElementTree.parse(self._folder+'/osm.net.xml').getroot()

    self._edges_order = []
    self._edges_with_tl = []
    self.edges_to_reroute = []
    self.compute_adj = False
    self.staticdynamic = False
    #self.compute_values()

  def update_values(self):
    old = np.array(self._edges_order)

    new = np.array(traci.vehicle.getRoute(self._ev))    
    
    if not np.array_equiv(old,new):
      if self.staticdynamic:
        routes_xml = xml.etree.ElementTree.parse(self._folder+'/osm.passenger.rou.xml').getroot()

        new_route_el = routes_xml.find('./vehicle[@id="{}"]/route'.format(self._ev))

        if new_route_el != None:
          new_route = new_route_el.get('edges').split(' ')
          traci.vehicle.setRoute(self._ev,new_route)

      new = np.array(traci.vehicle.getRoute(self._ev))

      self._logger.debug('old')
      self._logger.debug(old)
      self._logger.debug('new')
      self._logger.debug(new)

      self._edges_order = traci.vehicle.getRoute(self._ev)
      self.compute_values()
      return True

    return False

  def compute_values(self):
    self.edges_to_reroute = [ e.get('id') for e in self._net_file.findall('./edge[@type="highway.motorway"]') + \
                            self._net_file.findall('./edge[@type="highway.primary"]') + \
                            self._net_file.findall('./edge[@type="highway.secondary"]') + \
                            self._net_file.findall('./edge[@type="highway.tertiary"]') ]

    self._edges_with_tl = []

    self._edges = {}
    self._tls = set()

    self._logger.debug(self._edges_order)

    tls_already_used = {}

    index = traci.vehicle.getRouteIndex(self._ev)

    my_type = traci.vehicle.getTypeID(self._ev)

    for i in range(index,len(self._edges_order)):
      edge_name = self._edges_order[i]
      self._edges[edge_name] = {}
      current_edge = self._edges[edge_name]
      lane = edge_name+'_0'

      current_edge['vmax'] = traci.lane.getMaxSpeed(lane)
      current_edge['length'] = traci.lane.getLength(lane)


      self._logger.debug(str(edge_name) + ' ' + str(current_edge['vmax']) + ' ' + str(current_edge['length']))

      j=i+1
      path = './connection[@from="'+ str(edge_name) + '"]'

      if j < len(self._edges_order):
        path += '[@to="'+ str(self._edges_order[j]) + '"]'

      self._logger.debug(path)
      connections = self._net_file.findall(path)

      tl = None
      link_index = -1
      lane_in = None
      lane_out = None
      input_links_edge = []
      for connection in connections:
        if tl is not None:
          break

        tls = connection.get('tl')
        if tls and j < len(self._edges_order):
          controlled_links = traci.trafficlight.getControlledLinks(tls)
          for li in range(len(controlled_links)):
            link_tuple = controlled_links[li]
            if edge_name in link_tuple[0][0]:
              input_links_edge.append(li)

            if edge_name in link_tuple[0][0] and self._edges_order[j] in link_tuple[0][1] and \
               my_type.split('_')[1] in traci.lane.getAllowed(link_tuple[0][0]):
              tl = tls
              link_index = li
              lane_in = link_tuple[0][0]
              lane_out = link_tuple[0][1]

      if tl != None:
        if tl in tls_already_used:
          edge_in_use = [ edge for edge in self._edges if 'tl' in self._edges[edge] and self._edges[edge]['tl']['name'] == tl ][0]
          self._edges[edge_in_use]['tl']['cluster'] = True

          controlled_links = traci.trafficlight.getControlledLinks(tl)
          for li in range(len(controlled_links)):
            link_tuple = controlled_links[li]
            if edge_name in link_tuple[0][0] and self._edges_order[j] in link_tuple[0][1]:
              if my_type.split('_')[1] in traci.lane.getAllowed(link_tuple[0][0]):
                self._edges[edge_in_use]['tl']['other_link_indeces'].append(li)
                all_indeces = self._edges[edge_in_use]['tl']['other_link_indeces']
                g_index = self._edges[edge_in_use]['tl']['g']['index']

                all_programs = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl)
                my_program = [ program for program in all_programs if program.programID == current_program ][0]
                lights = my_program.phases[g_index].state
                if lights[li].upper() == 'G':
                  break
                else:
                  for p in range(0,len(my_program.phases)):
                    state = my_program.phases[p].state.upper()
                    all_green = True
                    for x in all_indeces:
                      if state[x] != 'G':
                        all_green = False
                        break
                    
                    if all_green:
                      self._edges[edge_in_use]['tl']['g']['index'] = p
                      self._edges[edge_in_use]['tl']['g']['duration'] = my_program.phases[p].duration
                      break


          continue

        tls_already_used[tl] = edge_name
        self._edges_with_tl.append(edge_name)
        self._tls.add(tl)
        current_edge['tl'] = {}
        current_edge['tl']['name'] = tl
        current_edge['tl']['cluster'] = False
        current_edge['tl']['lane_in'] = lane_in
        current_edge['tl']['lane_out'] = lane_out
        current_edge['tl']['link_index'] = link_index
        current_edge['tl']['other_link_indeces'] = []
        current_edge['tl']['other_link_indeces'].append(link_index)
        current_edge['tl']['adjs'] = {}


        current_program = traci.trafficlight.getProgram(tl)

        all_programs = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl)
        my_program = [ program for program in all_programs if program.programID == current_program ][0]
        self._logger.debug(my_program.phases[0].duration)
        
        right_index = int(link_index)
        lights_sequence = list(map((lambda ls: ls.state[right_index].upper()), my_program.phases))

        green_phase_index = lights_sequence.index('G')
        count_g = my_program.phases[green_phase_index].state.upper().count('G')
        
        edge_g = 0

        for l_index in range(len(lights_sequence)):
          count_edge_g = 0
          for x in input_links_edge:
            if my_program.phases[l_index].state[x].upper() == 'G':
              count_edge_g = count_edge_g + 1

          if (lights_sequence[l_index].upper() == 'G' and count_edge_g > edge_g) or \
            (count_edge_g == edge_g and my_program.phases[l_index].state.upper().count('G') > count_g):
            #and my_program.phases[l_index].state.upper().count('G') > count_g:
            count_g = my_program.phases[l_index].state.upper().count('G')
            edge_g = count_edge_g
            green_phase_index = l_index       


        self.define_parameters(green_phase_index, lights_sequence, current_edge['tl'], current_edge, my_program)
 
    if self.compute_adj:
      self._logger.debug(self.tls)
      for edge in self._edges_with_tl:
        if edge != self._edges_with_tl[-1]:
          tl_info = self._edges[edge]['tl']        
          tl_name = tl_info['name']
          self._logger.debug(tl_name)

          controlled_links = traci.trafficlight.getControlledLinks(tl_name)       

          tls = self.get_recursive_adj(controlled_links, edge, 0, tl_name)

          self._logger.debug(tls)

          self.add_adj(tls, tl_info)

        #stack_edges.append(edge_out)

        #while len(stack_edges) > 0:
        #  curr_edge = stack_edges.pop()
          
        #  if curr_edge in checked_edges:
        #    continue

        #  path = './connection[@to="'+ str(curr_edge) + '"]'
        #  connections = self._net_file.findall(path)

          #check all connections recursively

        #  should_break = False
        #  for connection in connections:
        #    tl = connection.get('tl')

        #    if tl is not None and tl not in self._tls and tl not in tl_info['adjs']:
        #      self.add_adj(tl, tl_info)
        #      should_break = True
        #    elif tl is None:
        #      new_edge = connection.get('from')

        #      if new_edge not in stack_edges:
        #        stack_edges.append(new_edge)

        #  checked_edges.add(curr_edge)

        #  if should_break:
        #    break

  def is_not_car_allowed(self,alloweds):
    not_cars = ['tram', 'rail_urban', 'rail', 'rail_electric', 'ship']

    return len([a for a in not_cars if a in alloweds]) > 0

  def get_recursive_adj(self, controlled_links, curr_edge, level, curr_tl):
    tls = set()
    if controlled_links is not None:
      unique_links_in = set()
      for link in controlled_links:
        alloweds = traci.lane.getAllowed(link[0][0])
        if not self.is_not_car_allowed(alloweds):
          splitted_name = link[0][0].split('_')
          edge_name = '_'.join(splitted_name[0:len(splitted_name)-1])
          if ':' not in edge_name and edge_name != curr_edge:
            unique_links_in.add(edge_name)

      for link in unique_links_in:
        tls.update(self.get_recursive_adj(None, link, level+1, curr_tl))
    else:
      if level >= 5:
        return tls

      path = './connection[@to="'+ str(curr_edge) + '"]'
      connections = self._net_file.findall(path)

      unique_edges = set()
      unique_connections = set()

      for c in connections:
        from_conn = c.get('from')
        if ':' not in from_conn and from_conn not in unique_edges:
          unique_edges.add(from_conn)
          unique_connections.add(c)

      for connection in unique_connections:
        edge_from = connection.get('from')
        tl = connection.get('tl')

        self._logger.debug('tl: {} from: {} to: {} tl: {} level: {}'.format(curr_tl,edge_from,curr_edge,tl,level))

        #if len(unique_connections) > 1 and tl is None:
        #  break

        if tl != curr_tl:
          if tl is not None and tl not in self._tls:
            cl_of_tl = traci.trafficlight.getControlledLinks(tl)
            edges_input_of_tl_splitted = [link[0][0].split('_') for link in cl_of_tl]
            edges_input = ['_'.join(link[0:len(link)-1]) for link in edges_input_of_tl_splitted]
            edges_out_of_route = [edge for edge in edges_input if edge in self.edges_order]
            if len(edges_out_of_route) <= 0:
              tls.add(tl)
            break
          else:
            new_edge = connection.get('from')

            if new_edge is not None and new_edge not in self._edges:
              new_tls = self.get_recursive_adj(None, new_edge, level+1, curr_tl)

              if len(new_tls) > 0:
                tls.update(new_tls)
                break

    return tls

            

  def add_adj(self, tls, tl_info):
    for tl in tls:
      all_programs = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl)
      current_program = traci.trafficlight.getProgram(tl)
      my_program = [ program for program in all_programs if program.programID == current_program ][0]
      tl_adj = {}
      self.define_durations(tl_adj,my_program)
      tl_info['adjs'][tl] = tl_adj


  def define_parameters(self, green_phase_index, lights_sequence, tl_info, current_edge, my_program):
    safe_phase_index = (green_phase_index - 2) % len(lights_sequence)
    red_phase_index = (green_phase_index - 1) % len(lights_sequence)
    self._logger.debug(str(green_phase_index)+' '+str(safe_phase_index)+' '+str(red_phase_index))

    tl_info['g'] = {}
    tl_info['g']['index'] = green_phase_index
    tl_info['g']['duration'] = my_program.phases[green_phase_index].duration

    tl_info['y'] = {}
    tl_info['y']['index'] = safe_phase_index
    tl_info['y']['duration'] = my_program.phases[safe_phase_index].duration

    tl_info['r'] = {}
    tl_info['r']['index'] = red_phase_index
    tl_info['r']['duration'] = my_program.phases[red_phase_index].duration

    self.define_durations(tl_info, my_program)

    tl_time = tl_info['y']['duration'] + tl_info['r']['duration'] + tl_info['g']['duration']

    self._logger.debug(current_edge['vmax'])
    self._logger.debug(tl_time)

    tl_info['s_detection'] = float(current_edge['vmax'])*float(tl_time)

    tl_info['vmax'] = current_edge['vmax']
    tl_info['length'] = current_edge['length']

    self._logger.debug(current_edge['tl'])

  def define_durations(self, tl_info, my_program):
    tl_info['ps_duration'] = []
    tl_info['phases'] = []
    tl_info['durations'] = []

    for t in range(len(my_program.phases)):
      tl_info['phases'].append(my_program.phases[t].state)
      tl_info['durations'].append(my_program.phases[t].duration)
      if t == 0:
        tl_info['ps_duration'].append(my_program.phases[t].duration)
      else:
        tl_info['ps_duration'].append(tl_info['ps_duration'][t-1] + my_program.phases[t].duration)
