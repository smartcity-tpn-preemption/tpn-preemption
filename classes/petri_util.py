from snakes.nets import *
from classes import tpn
snakes.plugins.load([tpn,"gv"], 'snakes.nets', 'nets')
from nets import *

class PetriUtil:
  def configure(self):
    self.black_token = BlackToken()
    self.token = Value(self.black_token)
    self.inhibitor_arc = Inhibitor(self.token)

  def build_initial_block(self):
    self.pn.add_place(Place('initialplace', [self.black_token]))
    self.pn.add_transition(Transition('initialtransition'))
    self.pn.add_input('initialplace','initialtransition',self.token)

  def build_final_block(self):
    self.pn.add_place(Place('finalplace', []))
    self.pn.add_transition(Transition('finaltransition'))
    self.pn.add_input('finalplace','finaltransition',self.token)        
    self.pn.add_output('finalplace','finaltransition',self.token)

  def build_cancelling_block(self):
    self.pn.add_place(Place('p20', []))
    self.pn.add_place(Place('p21', []))
    self.pn.add_place(Place('pt17', [self.black_token]))
    self.pn.add_transition(Transition('t17'))      
    self.pn.add_transition(Transition('t18'))      
    self.pn.add_transition(Transition('t21'))

    #t17
    #artifical place
    self.pn.add_input('pt17','t17',self.token)
    self.pn.add_output('p20', 't17', self.token)      
    self.pn.add_output('p21', 't17', self.token)

    #t18
    self.pn.add_input('p20','t18',self.token)

    #t21
    self.pn.add_input('p21','t21',self.token)
    self.pn.add_output('p21','t21',self.token) 

    print(self.pn)

  def build_places_and_transitions(self,tl_name,time_to_open_tls):
    self.pn.add_place(Place(get_place_name('t8',tl_name), [self.black_token]))

    for i in range(0,20):
      self.pn.add_place(Place(get_place_name(i,tl_name), []))

    for i in range(0,17):
      if i == 8:
        self.pn.add_transition(Transition(get_trans_name(i,tl_name)))
      elif i == 2:
        self.pn.add_transition(Transition(get_trans_name(i,tl_name), min_time=time_to_open_tls[tl_name]))
      else:
        self.pn.add_transition(Transition(get_trans_name(i,tl_name)))

    for i in range(19,24):
      if i != 21:
        self.pn.add_transition(Transition(get_trans_name(i,tl_name)))      

  def build_petri_net(self, conf, edges, curr_edge, time_to_open_tls):
    self.configure() 
    self.pn = PetriNet('SCPetriNet')

    self.build_initial_block()
    self.build_cancelling_block()
    self.build_final_block()

    prev_tl_name = ''
    first_edge = None
    for i in range(curr_edge,len(edges)):
      edge_id = edges[i]
      if edge_id in conf.edges_with_tl:
      #for edge_id in conf.edges_with_tl:
        tl_name = conf.edges[edge_id]['tl']['name']

        if first_edge == None:
          first_edge = edge_id

        self.build_places_and_transitions(tl_name,time_to_open_tls)   

        if(edge_id == first_edge):
          self.pn.add_output(get_place_name(0,tl_name),'initialtransition',self.token)
        elif(edge_id == conf.edges_with_tl[-1]):
          self.pn.add_output(get_place_name(0,tl_name),get_trans_name(1,prev_tl_name),self.token)          
          self.pn.add_output('finalplace',get_trans_name(1,tl_name),self.token)
        else:
          self.pn.add_output(get_place_name(0,tl_name),get_trans_name(1,prev_tl_name),self.token)

        #global t18 links
        self.pn.add_output(get_place_name(15,tl_name),'t18',self.token)
        self.pn.add_output(get_place_name(16,tl_name),'t18',self.token)
        self.pn.add_output(get_place_name(17,tl_name),'t18',self.token)
        self.pn.add_output(get_place_name(12,tl_name),'t18',self.token)
        self.pn.add_output(get_place_name(18,tl_name),'t18',self.token)
        self.pn.add_output(get_place_name(19,tl_name),'t18',self.token)                              


        #link transitions here
        #t0
        self.pn.add_input(get_place_name(0,tl_name),get_trans_name(0,tl_name),self.token)
        self.pn.add_input(get_place_name(18,tl_name),get_trans_name(0,tl_name),self.inhibitor_arc)
        self.pn.add_output(get_place_name(1,tl_name),get_trans_name(0,tl_name),self.token)
        self.pn.add_output(get_place_name(2,tl_name),get_trans_name(0,tl_name),self.token)

        #t1
        self.pn.add_input(get_place_name(1,tl_name),get_trans_name(1,tl_name),self.token)
        self.pn.add_input(get_place_name(18,tl_name),get_trans_name(1,tl_name),self.inhibitor_arc) 

        #t2     
        self.pn.add_input(get_place_name(2,tl_name),get_trans_name(2,tl_name),self.token)
        self.pn.add_input(get_place_name(18,tl_name),get_trans_name(2,tl_name),self.inhibitor_arc)
        self.pn.add_output(get_place_name(3,tl_name),get_trans_name(2,tl_name),self.token)
        self.pn.add_output(get_place_name(4,tl_name),get_trans_name(2,tl_name),self.token)

        #t3
        self.pn.add_input(get_place_name(3,tl_name),get_trans_name(3,tl_name),self.token)
        self.pn.add_input(get_place_name(4,tl_name),get_trans_name(3,tl_name),self.token)
        self.pn.add_output(get_place_name(5,tl_name),get_trans_name(3,tl_name),self.token)

        #t4
        self.pn.add_input(get_place_name(5,tl_name),get_trans_name(4,tl_name),self.token)
        self.pn.add_input(get_place_name(8,tl_name),get_trans_name(4,tl_name),self.token)
        self.pn.add_input(get_place_name(6,tl_name),get_trans_name(4,tl_name),self.inhibitor_arc)
        self.pn.add_output(get_place_name(6,tl_name),get_trans_name(4,tl_name),self.token)

        #t5
        self.pn.add_input(get_place_name(6,tl_name),get_trans_name(5,tl_name),self.token)
        self.pn.add_input(get_place_name(7,tl_name),get_trans_name(5,tl_name),self.inhibitor_arc)
        self.pn.add_output(get_place_name(7,tl_name),get_trans_name(5,tl_name),self.token)

        #t6
        self.pn.add_input(get_place_name(7,tl_name),get_trans_name(6,tl_name),self.token)
        self.pn.add_output(get_place_name(7,tl_name),get_trans_name(6,tl_name),self.token)

        #t7
        self.pn.add_input(get_place_name(9,tl_name),get_trans_name(7,tl_name),self.token)
        self.pn.add_input(get_place_name(18,tl_name),get_trans_name(7,tl_name),self.inhibitor_arc)
        self.pn.add_input(get_place_name(6,tl_name),get_trans_name(7,tl_name),self.inhibitor_arc)
        self.pn.add_input(get_place_name(7,tl_name),get_trans_name(7,tl_name),self.inhibitor_arc)
        self.pn.add_output(get_place_name(8,tl_name),get_trans_name(7,tl_name),self.token)

        #t8
        #artifical place
        self.pn.add_input(get_place_name('t8',tl_name),get_trans_name(8,tl_name),self.token)
        self.pn.add_input(get_place_name(10,tl_name),get_trans_name(8,tl_name),self.inhibitor_arc)
        self.pn.add_output(get_place_name(9,tl_name),get_trans_name(8,tl_name),self.token)
        self.pn.add_output(get_place_name(10,tl_name),get_trans_name(8,tl_name),self.token)

        #t9
        self.pn.add_input(get_place_name(9,tl_name),get_trans_name(9,tl_name),self.token)
        self.pn.add_input(get_place_name(19,tl_name),get_trans_name(9,tl_name),self.token)
        self.pn.add_output(get_place_name(11,tl_name),get_trans_name(9,tl_name),self.token)

        #t10
        self.pn.add_input(get_place_name(11,tl_name),get_trans_name(10,tl_name),self.token)
        self.pn.add_output(get_place_name(11,tl_name),get_trans_name(10,tl_name),self.token)

        #t11
        self.pn.add_input(get_place_name(12,tl_name),get_trans_name(11,tl_name),self.token)
        self.pn.add_input(get_place_name(6,tl_name),get_trans_name(11,tl_name),self.inhibitor_arc)
        self.pn.add_input(get_place_name(7,tl_name),get_trans_name(11,tl_name),self.inhibitor_arc)
        self.pn.add_input(get_place_name(8,tl_name),get_trans_name(11,tl_name),self.inhibitor_arc)
        self.pn.add_output(get_place_name(8,tl_name),get_trans_name(11,tl_name),self.token)

        #t12
        self.pn.add_input(get_place_name(1,tl_name),get_trans_name(12,tl_name),self.token)
        self.pn.add_input(get_place_name(17,tl_name),get_trans_name(12,tl_name),self.token)
        self.pn.add_output(get_place_name(13,tl_name),get_trans_name(12,tl_name),self.token)

        #t13
        self.pn.add_input(get_place_name(13,tl_name),get_trans_name(13,tl_name),self.token)
        self.pn.add_output(get_place_name(13,tl_name),get_trans_name(13,tl_name),self.token)

        #t14
        self.pn.add_input(get_place_name(0,tl_name),get_trans_name(14,tl_name),self.token)
        self.pn.add_input(get_place_name(16,tl_name),get_trans_name(14,tl_name),self.token)
        self.pn.add_output(get_place_name(14,tl_name),get_trans_name(14,tl_name),self.token)

        #t15
        self.pn.add_input(get_place_name(2,tl_name),get_trans_name(15,tl_name),self.token)
        self.pn.add_input(get_place_name(15,tl_name),get_trans_name(15,tl_name),self.token)      
        self.pn.add_output(get_place_name(14,tl_name),get_trans_name(15,tl_name),self.token)

        #t16
        self.pn.add_input(get_place_name(14,tl_name),get_trans_name(16,tl_name),self.token)
        self.pn.add_output(get_place_name(14,tl_name),get_trans_name(16,tl_name),self.token)

        #t19
        self.pn.add_input(get_place_name(18,tl_name),get_trans_name(19,tl_name),self.token)
        self.pn.add_output(get_place_name(18,tl_name),get_trans_name(19,tl_name),self.token)

        #t20
        self.pn.add_input(get_place_name(10,tl_name),get_trans_name(20,tl_name),self.token)
        self.pn.add_output(get_place_name(10,tl_name),get_trans_name(20,tl_name),self.token)

        #t22
        self.pn.add_input(get_place_name(5,tl_name),get_trans_name(22,tl_name),self.token)
        self.pn.add_output(get_place_name(5,tl_name),get_trans_name(22,tl_name),self.token)
        self.pn.add_input(get_place_name(8,tl_name),get_trans_name(22,tl_name),self.inhibitor_arc)

        #t23
        self.pn.add_input(get_place_name(8,tl_name),get_trans_name(23,tl_name),self.token)
        self.pn.add_output(get_place_name(8,tl_name),get_trans_name(23,tl_name),self.token)
        self.pn.add_input(get_place_name(5,tl_name),get_trans_name(23,tl_name),self.inhibitor_arc)                                      
    
        prev_tl_name = tl_name

        #self.pn.draw('/home/rbranco/pn_{}.png'.format(tl_name))
        #print('pn_{}.png'.format(tl_name))      

    #self.pn.reset()
    return self.pn

def get_place_name(i,tl_name):
  return 'p{}_{}'.format(i,tl_name)

def get_trans_name(i,tl_name):
  return 't{}_{}'.format(i,tl_name)