from logger import Logger
from sumolib import checkBinary  # noqa
import traci  # noqa
 
class DefaultWorker():
    def __init__(self, evList, distance_to_tl, prefix):
        self._prefix = prefix
        self._evList = evList
        self._distance_to_tl = distance_to_tl
        self._tls_of_evs = {}
        self._blocking_tls_of_evs = {}
        self._logger = Logger(self.__class__.__name__).get()

    def preConfig(self):
      return True

    @property
    def tls_of_evs(self):
      return self._tls_of_evs

    @property
    def blocking_tls_of_evs(self):
      return self._blocking_tls_of_evs   

    def doMore(self):
        pass

    def actInBlockingTL(self, tl_id, ev_id, lane_index):
        pass

    def shouldNotifyTL(self, ev_id, tls_ids):
        pass               

    def doSimulationStep(self):
        self._logger.debug(self._evList)
        vs = traci.vehicle.getIDList()

        activeEVs = [x for x in vs if x in self._evList]

        for ev_id in activeEVs:
            traci.vehicle.setColor(ev_id, (255,0,0,255))
            tls = traci.vehicle.getNextTLS(ev_id)
            tls_ids = [tl[0] for tl in tls]
            self._logger.info('tls of ' + str(ev_id))
            self._logger.info(tls_ids)
            self.shouldNotifyTL(ev_id, tls_ids)

            if tls and tls[0] and tls[0][2] and tls[0][2] <= self._distance_to_tl:
                tl_id = tls[0][0]
                lanes = traci.trafficlight.getControlledLanes(tl_id)
                links = traci.trafficlight.getControlledLinks(tl_id)

                #check next links
                #tls[1]??

                lane_id = traci.vehicle.getLaneID(ev_id)
                self._logger.info("EV: "+ev_id+" TL: "+tl_id)
                self._logger.info(lanes)
                self._logger.info(links)
                self._logger.info(lane_id)

                self._logger.info("index: "+str(traci.vehicle.getLaneIndex(ev_id)))

                self._logger.debug("LANE ID: "+lane_id)
                self._logger.debug("LANE INDEX: "+str(traci.vehicle.getLaneIndex(ev_id)))

                if lane_id in lanes:
                    self._logger.debug(lanes)
                    self._logger.debug(lane_id)
                    self._logger.info("lanes: "+str(len(lanes)) + " " + "index: "+ str(lanes.index(lane_id))+ " offset: " + str(traci.vehicle.getLaneIndex(ev_id)))

                    #obter lane_id sem _
                    edge_id = traci.lane.getEdgeID(lane_id)
                    self._logger.info("Edge: "+str(edge_id))

                    route = traci.vehicle.getRoute(ev_id)

                    self._logger.info("route "+str(route))
                    self._logger.info(route)

                    #obter next route (route+1)
                    next_edge_index = route.index(edge_id)+1 
                    
                    if next_edge_index >= len(route):
                      next_edge_index = next_edge_index - 1

                    next_edge = route[next_edge_index]

                    self._logger.info('lanes:: '+str(lanes))
                    self._logger.info('links:: '+str(links))

                    self._logger.info("Next Edge: " + str(next_edge))

                    #obter qual link que sai de lane_id e vai pra route+1
                    right_index = [ links.index(link) for link in links if link[0][0] == lane_id and next_edge in link[0][1] ]
                    self._logger.info("Right index: " + str(right_index[0]))
                    #pegar o index


                    #lane_index = lanes.index(lane_id) + traci.vehicle.getLaneIndex(ev_id)
                    #lane_index = lanes.index(lane_id)
                    #lane_index = traci.vehicle.getLaneIndex(ev_id)
                    lane_index = right_index[0]
                    self._logger.debug(lane_index)

                    if ev_id not in self._tls_of_evs:
                        self._tls_of_evs[ev_id] = set([])

                    tls_set = self._tls_of_evs[ev_id]
                    tls_set.add(tl_id)

                    self._logger.debug('here')
                    self._logger.debug(tls_set)

                    if traci.trafficlight.getRedYellowGreenState(tl_id)[lane_index].upper() in ['Y','R']:
                        # blocking Traffic Light, may we should do something...
                        self.actInBlockingTL(tl_id, ev_id, lane_index)

                        if ev_id not in self._blocking_tls_of_evs:
                            self._blocking_tls_of_evs[ev_id] = set([])

                        blocking_tls_set = self._blocking_tls_of_evs[ev_id]
                        blocking_tls_set.add(tl_id)

                        self._logger.debug('blocking')
                        self._logger.debug(blocking_tls_set)

                        tlPhase = traci.trafficlight.getPhase(tl_id)
                    else:
                        self._logger.info(str(tl_id) + ' not blocking for ' + str(ev_id) )

                else:
                    self._logger.info(lane_id + ' not controlled by '+tl_id)

        self.doMore()

        self._logger.debug(activeEVs)        
    