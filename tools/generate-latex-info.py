import optparse
import json
import sys
import numpy
import os
from distutils.util import strtobool
import pandas
import scipy.stats as stats
import math
import collections

from classes.base_latex_processor import BaseLatexProcessor
from classes.improvement_latex_processor import ImprovementLatexProcessor
from classes.timeloss_no_preemption_latex_processor import TimelossNoPreemptionLatexProcessor
from classes.timeloss_over_ttt_no_preemption_latex_processor import TimelossOverTTTNoPreemptionLatexProcessor
from classes.bar_latex_processor import BarLatexProcessor
from classes.boxplot_latex_processor import BoxplotLatexProcessor
from classes.errorbar_latex_processor import ErrorBarLatexProcessor

def get_options():
  opt_parser = optparse.OptionParser()
  opt_parser.add_option("--jsonfile", dest="jsonfile", 
                        help="JSON File", metavar="FILE")
  opt_parser.add_option("--prefix", dest="prefix", 
                        help="Prefix to generate filex", metavar="FILE")
  opt_parser.add_option("--datafolder", dest="datafolder", 
                        help="Prefix to generate filex", metavar="FILE")
  opt_parser.add_option("--excludeoutliers", type="string", dest="excludeoutliers",
                        default="False", help="Indicates if outliers will be excluded")
  opt_parser.add_option("--location", type="string", dest="location",
                        help="Indicates location (SP or NY) so far")
  opt_parser.add_option("--ev", type="string", dest="ev",
                        help="Indicates EV")

  (options, args) = opt_parser.parse_args()
  return options

# this is the main entry point of this script
if __name__ == "__main__":

  options = get_options()

  if not options.jsonfile:
    sys.exit("Error: You must specify the JSON file using the '--jsonfile' option")

  if not options.prefix:
    sys.exit("Error: You must specify the prefix using the '--prefix' option")  

  if not options.datafolder:
    sys.exit("Error: You must specify the data folder using the '--datafolder' option")

  if not options.location:
    sys.exit("Error: You must specify the location using the '--location' option")
    
  if not options.ev:
    sys.exit("Error: You must specify the EV using the '--ev' option")          

  try:
    excludeoutliers = strtobool(options.excludeoutliers)
  except:
    sys.exit("Error: --sync option invalid. It should be true or false")   

  if not os.path.exists(options.datafolder):
    os.makedirs(options.datafolder, exist_ok=True)

  folder_with_prefix = options.datafolder + '/' + options.prefix

  if not os.path.exists(folder_with_prefix):
    os.makedirs(folder_with_prefix, exist_ok=True)

  folder_with_location = folder_with_prefix + '/' + options.location

  if not os.path.exists(folder_with_location):
    os.makedirs(folder_with_location, exist_ok=True)  

  folder_with_ev = folder_with_location + '/' + options.ev

  if not os.path.exists(folder_with_ev):
    os.makedirs(folder_with_ev, exist_ok=True)  

  print(options)

  file_tmp = open(options.jsonfile,'r')
  results = json.loads(file_tmp.read())
  file_tmp.close()

  algs = collections.OrderedDict()

  algs = {}
  if options.location in results:
    for i in results[options.location]:
      for alg in results[options.location][i]:
        if alg != 'no-preemption':
          if alg not in algs:
            algs[alg] = []  
          for args in results[options.location][i][alg]:
            if options.ev in results[options.location][i][alg][args]:
              algs[alg].append(args)

  metrics = ['timeloss-ev']
            #,'timeloss-other-affected']
            
  if options.location in results:
    processor = TimelossNoPreemptionLatexProcessor(options.location,'timeloss-over-ttt','no-preemption',[''],results, folder_with_ev, excludeoutliers, 
                                                  options.ev, options.prefix, 'Timeloss (s)')

    processor.print_summary()

    processor = BarLatexProcessor(options.location,'timeloss-ev',algs,'',results, folder_with_ev, excludeoutliers, 
                                                  options.ev, options.prefix, 'Improvement = (1 - (Timeloss After / Timeloss Before) x 100) (%)')

    processor.set_aditional_data(algs = algs)  

    processor.print_summary()    
