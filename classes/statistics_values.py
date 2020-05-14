import xml.etree.ElementTree
import numpy
import os
from .logger import Logger
import json

import collections
import sys

from sumolib import checkBinary  # noqa
import traci  # noqa


class StatisticsValues:
  def __init__(self, folder, trip_path, trip_file, alg, ev=0):
    self.__folder = folder
    self.__trip_file = trip_file
    self.__trip_path = trip_path
    self._logger = Logger(self.__class__.__name__).get()
    self.__algorithm = alg

    xml_file = xml.etree.ElementTree.parse(self.__folder+'/osm.passenger.trips.xml').getroot()

    self.ev = ev
    check_ev = xml_file.findall('trip[@id="'+self.ev+'"]')

    if len(check_ev) <= 0:
      sys.exit("ERROR: EV not found in trip file")

    
    xml_file = xml.etree.ElementTree.parse(self.__folder+'/osm.net.xml').getroot()

    tl_logics = xml_file.findall('tlLogic')
    self.__tl_logics = len(tl_logics)


    self.was_teleported = False
    self.n_of_teleporteds = set()

    self.crossed_tls_by_ev = 0

    self.vehicles_affected_by_ev = set()

    self.n_when_ev_enter = -1
    self.n_when_ev_left = -1

    self.ev_start = -1
    self.ev_end = -1

    self.distance_travelled = -1
    
    self.number_of_vehicles = 0

    self.final_time = -1

    self.cars_by_time = collections.OrderedDict()

    self.ev_ttt = -1
    self.ev_timeloss = -1

    self.ev_avg_speed = 0

  def update_vehicles_affected_by_ev(self):
    ev_edge = traci.vehicle.getRoadID(self.ev)
    vehicles = traci.edge.getLastStepVehicleIDs(ev_edge)
    for veh in vehicles:
      if veh != self.ev:
        self.vehicles_affected_by_ev.add(veh)    

  def update_vehicles_affected_by_ev_dispatch(self):
    ev_route = traci.vehicle.getRoute(self.ev)

    for edge in ev_route:
      vehicles = traci.edge.getLastStepVehicleIDs(edge)
      for veh in vehicles:
        if veh != self.ev:
          self.vehicles_affected_by_ev.add(veh)

  def update_vehicles_on_tl(self):
    for tlarray in traci.vehicle.getNextTLS(self.ev):
      if tlarray[2] <= 500:
        links = traci.trafficlight.getControlledLinks(tlarray[0])
        for link in links:
          vehicles = traci.edge.getLastStepVehicleIDs(traci.lane.getEdgeID(link[0][0]))
          for veh in vehicles:
            if veh != self.ev:
              self.vehicles_affected_by_ev.add(veh)          

  def update_cars_by_time(self,time,count):
    self.cars_by_time[time] = count
    
  def print_tuple(self, label, provided_list):
    size = len(provided_list)
    modified_list = numpy.array(provided_list).astype(numpy.float)
    avg = numpy.mean(modified_list)
    var = numpy.var(modified_list)
    std = numpy.std(modified_list)
    msg = '{0}\t\t{1}\t\t{2:.2f}\t\t{3:.2f}\t\t{4:.2f}'
    self._logger.info(msg.format(label, size, avg, var, std))

  def get_results(self, ev, final_time):
    self.final_time = final_time
    xml_file = xml.etree.ElementTree.parse(self.__trip_file).getroot()
    tripsinfo = xml_file.findall('tripinfo')
    self.number_of_vehicles = len(tripsinfo)
    ev_trip = [x for x in tripsinfo if x.attrib['id'] == ev][0]
    self.ev_ttt = ev_trip.attrib['duration']
    self.ev_timeloss = ev_trip.attrib['timeLoss']
    self.ev_avg_speed = float(self.distance_travelled)/float(self.ev_ttt)    
    self._logger.info('###RESULTS - Algorithm =>'+str(self.__algorithm)+'###')
    self._logger.info("Number of TL " + str(self.__tl_logics))
    self._logger.info('total number of vehicles:'+str(self.number_of_vehicles))
    self._logger.info('EV Total travel time: '+str(self.ev_ttt))
    self._logger.info('EV Time loss: '+str(self.ev_timeloss))
    self._logger.info('number of tls crossed by ev: '+str(self.crossed_tls_by_ev))
    self._logger.info('Label\t\t#\t\tAvg\t\tVar\t\tStd')
    other_trip_time = [x.attrib['duration'] for x in tripsinfo if x.attrib['id'] != ev]
    self.print_tuple('Other vehicles - Total Trip Time', other_trip_time)
    other_time_loss = [x.attrib['timeLoss'] for x in tripsinfo if x.attrib['id'] != ev]
    self.print_tuple('Other vehicles - Time Loss', other_time_loss)
    self._logger.info('Final time of simulation:'+str(self.final_time))
    self._logger.info('Times EV - enter: '+str(self.ev_start)+' left:'+str(self.ev_end))
    self._logger.info('Number of vehicles - enter: '+str(self.n_when_ev_enter)+' left:'+str(self.n_when_ev_left))
    self._logger.info('Number of teleported vehicles: '+str(len(self.n_of_teleporteds)))
    self._logger.info('Number of vehicles affected by ev: '+str(len(self.vehicles_affected_by_ev)))
    self._logger.info('Ev was teleported: '+str(self.was_teleported))
    self._logger.info('Distance travelled: '+str(self.distance_travelled))
    self._logger.info('EV Avg Speed: '+str(self.ev_avg_speed))
    self._logger.info('###RESULTS###')

  def print_summary(self,ev):
    self._logger.info(str(ev)+' had entered when t='+str(self.ev_start)+' left the network when t='+str(self.ev_end))
    self._logger.info('was teleported: '+str(self.was_teleported))
    self._logger.info('ids teleporteds: '+str(self.n_of_teleporteds))
    self._logger.info('crossed tls: '+str(self.crossed_tls_by_ev))
    self._logger.info('n# when ev enter: '+str(self.n_when_ev_enter))
    self._logger.info('n# when ev left: '+str(self.n_when_ev_left))
    self._logger.info('distance travelled: '+str(self.distance_travelled))

  def skip_because_json_file(self, override, skip, filename):
    if skip:
      return False

    json_name = self.__trip_path+"/"+filename+".json"
    if not override and os.path.isfile(json_name):
      self._logger.info(json_name+' exists and override='+str(override)+', skipping...')
      return True
    else:
      self._logger.info(json_name+' does not exists and override='+str(override)+', procceding...')
      return False


  def generate_json(self,skip, filename):
    if skip:
      return

    xml_file = xml.etree.ElementTree.parse(self.__trip_file).getroot()
    tripsinfo = xml_file.findall('tripinfo')

    other_trip_time = [x.attrib['duration'] for x in tripsinfo if x.attrib['id'] != self.ev]
    modified_list = numpy.array(other_trip_time).astype(numpy.float)
    other_ttt_avg = float(numpy.mean(modified_list))
    other_ttt_var = float(numpy.var(modified_list))
    other_ttt_std = float(numpy.std(modified_list))

    other_time_loss = [x.attrib['timeLoss'] for x in tripsinfo if x.attrib['id'] != self.ev]
    modified_list = numpy.array(other_time_loss).astype(numpy.float)
    other_timeloss_avg = float(numpy.mean(modified_list))
    other_timeloss_var = float(numpy.var(modified_list))
    other_timeloss_std = float(numpy.std(modified_list))

    other_affected_trip_time = [x.attrib['duration'] for x in tripsinfo if x.attrib['id'] in self.vehicles_affected_by_ev]
    modified_list = numpy.array(other_affected_trip_time).astype(numpy.float)
    other_affected_ttt_avg = float(numpy.mean(modified_list))
    other_affected_ttt_var = float(numpy.var(modified_list))
    other_affected_ttt_std = float(numpy.std(modified_list))    

    other_affected_time_loss = [x.attrib['timeLoss'] for x in tripsinfo if x.attrib['id'] in self.vehicles_affected_by_ev]
    modified_list = numpy.array(other_affected_time_loss).astype(numpy.float)
    other_affected_timeloss_avg = float(numpy.mean(modified_list))
    other_affected_timeloss_var = float(numpy.var(modified_list))
    other_affected_timeloss_std = float(numpy.std(modified_list)) 

    other_speed_list = [float(x.attrib['routeLength'])/float(x.attrib['duration']) for x in tripsinfo if x.attrib['id'] != self.ev]
    modified_list = numpy.array(other_speed_list).astype(numpy.float)
    other_speed_avg = float(numpy.mean(modified_list))
    other_speed_var = float(numpy.var(modified_list))
    other_speed_std = float(numpy.std(modified_list)) 

    other_affected_speed_list = [float(x.attrib['routeLength'])/float(x.attrib['duration']) 
                                for x in tripsinfo if x.attrib['id'] in self.vehicles_affected_by_ev]
    modified_list = numpy.array(other_affected_speed_list).astype(numpy.float)
    other_affected_speed_avg = float(numpy.mean(modified_list))
    other_affected_speed_var = float(numpy.var(modified_list))
    other_affected_speed_std = float(numpy.std(modified_list))        

    density_array = []
    for k, v in self.cars_by_time.items():
      density_array.append([k,v])

    data = {
      'summary': {
        'instance': filename,
        'tls': self.__tl_logics,
        'n_vehicles': self.number_of_vehicles,
        'when_enter': self.ev_start,
        'when_left': self.ev_end,
        'n_when_enter': self.n_when_ev_enter,
        'n_when_left': self.n_when_ev_left,
        'final_time': self.final_time,
        'n_teleported': len(self.n_of_teleporteds),
        'ev_was_teleported': self.was_teleported,
        'crossed_tls': self.crossed_tls_by_ev,
        'distance': self.distance_travelled,
        'ev': self.ev,
        'ttt-ev': self.ev_ttt,
        'timeloss-ev': self.ev_timeloss,
        'timeloss-ev/ttt-ev': float(self.ev_timeloss)/float(self.ev_ttt),
        'ttt-other': other_ttt_avg,
        'timeloss-other': other_timeloss_avg,
        'ttt-other-var': other_ttt_var,
        'timeloss-other-var': other_timeloss_var,
        'ttt-other-std': other_ttt_std,
        'timeloss-other-std': other_timeloss_std,
        'ttt-other-affected': other_affected_ttt_avg,
        'timeloss-other-affected': other_affected_timeloss_avg,
        'ttt-other-affected-var': other_affected_ttt_var,
        'timeloss-other-affected-var': other_affected_timeloss_var,
        'ttt-other-affected-std': other_affected_ttt_std,
        'timeloss-other-affected-std': other_affected_timeloss_std,
        'ev-speed-avg': self.ev_avg_speed,
        'other-speed-avg': other_speed_avg,
        'other-speed-var': other_speed_var,
        'other-speed-std': other_speed_std,
        'other-affected-speed-avg': other_affected_speed_avg,
        'other-affected-speed-var': other_affected_speed_var,
        'other-affected-speed-std': other_affected_speed_std,               
      },
      'Car density': density_array
    }

    file_tmp = open(self.__trip_path+"/"+filename+".json",'w+')
    file_tmp.write(json.dumps(data))
    file_tmp.close()    

