# Native-python libs:
import os
import pylab
import math
import win32com.client

# Third-party libraries:
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# My libraries:
from dss import aux_lib as aux                      


# Basic setup:
plt.rcParams.update({'font.size': 14, 'figure.figsize': (10,8)})


class DSS(object):
    # Class DSS definitions:
    # This class initializes the DSS objetc and gets some of the circuit basic
    # information. It gives the support for other classes to inherit from it 
    # and perform more complex tasks.

    def __init__(self, dssFileName, std_unit = 'km', Dssview_disable = False):
        #This subroutine initializes the DSS object

        #Getting the DSPA current working directory:
        self.DSS_cwd =  os.getcwd()
        self.DSS_LVRT_filename = self.DSS_cwd + '\__LVRTcurves__\LVRT_Curve.dss'
        self.pv_irradtempeff_file = self.DSS_cwd + '\__timeconditions\irrad_standard_dss.dss'
        #File name and file path related variables:
        self.filename = dssFileName
        self.filepath = os.path.dirname(dssFileName)
        self.short_filename = self.filename[len(self.filepath)+1:-4]        
        #Closing the DSSView if required:
        if Dssview_disable == True:
            os.system("TASKKILL /F /IM DSSView.exe")
            
        #Create a new instance of the DSS
        self.dssObj = win32com.client.Dispatch("OpenDSSEngine.DSS")           
        #Assign a variable to some important interfaces for easier access:
        self.dssText = self.dssObj.Text
        self.dssCircuit = self.dssObj.ActiveCircuit
        self.dssCktElement = self.dssCircuit.ActiveCktElement
        self.dssSolution = self.dssCircuit.Solution
        self.dssCtrlQueue = self.dssCircuit.CtrlQueue
        self.dssBus = self.dssCircuit.ActiveBus
        self.dssMonitors = self.dssCircuit.Monitors
        self.dssMeters = self.dssCircuit.Meters
        #PD-elements interfaces:
        self.dssPDElement = self.dssCircuit.PDElements
        self.dssLines = self.dssCircuit.Lines
        self.dssTransformers = self.dssCircuit.Transformers
        #PC-elements interfaces:
        self.dssLoads = self.dssCircuit.Loads
        self.dssPVSystem = self.dssCircuit.PVSystems
        self.dssGenerators = self.dssCircuit.Generators
        #Control & protection elements interfaces:
        self.dssFuses = self.dssCircuit.Fuses
        self.dssReclosers = self.dssCircuit.Reclosers
        self.dssRelays = self.dssCircuit.Relays
        self.dssSwtControls = self.dssCircuit.SwtControls
        self.dssRegControls = self.dssCircuit.RegControls 
          
        #The std_unit specified will be used as standard unit length in case
        #the line unit length wasn't defined.
        self.std_unit_len = std_unit
        #"Infinite" resistance value:
        self.Rinf = 1000000000

        #Innitializing the system:
        self.init_system()
        #Re-setting the current working directory:
        os.chdir(self.DSS_cwd)
        print("\nDSS started successfully!")


    def dss_version(self):
        # This subroutine prints the OpenDSS program version.
        
        print(self.dssObj.Version)
        

    def init_system(self):
            #This subroutine initializes the circuit and gets all the relevant 
            #information about the system.
            
            #Always a good idea to clear the DSS when loading a new circuit:
            self.dssObj.ClearAll()
            #Load the given circuit file into OpendSS and compile it:
            self.dssText.Command = "Compile " + self.filename
            #Getting the voltage-base default values:
            self.dssText.Command = "get Voltagebases"
            self.kvbases = aux.get_numvalues(self.dssText.Result)
            #Pre-solving the circuit in Snapshot mode for initialization:
            self.dssText.Command = "MakeBusList"
            self.dssText.Command = "calcv"
            self.dssText.Command = "Set mode=Snapshot"
            self.dssText.Command = "set controlmode=Time"
            self.dssSolution.Solve()

            #IMPORTANT CIRCUIT Information:
            #The names of all circuit elements, such as buses, nodes and lines
            #will be given in lower case.
            #Name of all circuit elements (Enabled and Disabled):
            self.allElements = list()
            for elmnt in self.dssCircuit.AllElementNames:
                self.allElements.append(elmnt.lower())
            self.n_Elements = len(self.allElements)
            #Name of all buses and number of buses in the system:
            #These are all the active buses in the system
            #An active bus has at least one active element connected to it.
            self.allBuses = list()
            for bus in self.dssCircuit.AllBusNames:
                self.allBuses.append(bus.lower())
            self.n_Buses = len(self.allBuses)
            #Name of all nodes and number of nodes in the system:
            #These nodes are referred to the active buses only.
            self.allNodes = list()
            for node in self.dssCircuit.AllNodeNames:
                self.allNodes.append(node.lower())
            self.n_Nodes = len(self.allNodes)
            #Lines and switches names:
            #All the switches are expected to be modeled as line-switches.
            #The Line elements (current-carrying lines or "real lines") will be 
            #separated from the switches. The swithces don't count for the  
            #circuit length, and are expected to be defined as very short lines 
            #(Recommended 1 meter long). 
            #The short-circuits won't be applied in them, just in ordinary lines.
            self.allLines = dict()
            self.allSwitches = list()
            self.disabled_lines = dict()
            self.feeder_length = 0
            self.n_Lines = 0
            #Getting the lines information:
            self.get_linesinfo()

            #Systematic elements info:
            #Dictionary with all PD-Elements bus connections info:
            self.PD_elements = dict()
            self.n_PDs = 0
            #Dictionary with all PC-Elements bus connections info:
            self.PC_elements = dict()
            self.n_PCs = 0
            #Dictionary with all Protection Elements info:
            self.Protect_elements = dict()
            #Dictionary with all DG anti-islanding protection elements info:
            self.DG_Protect = dict()
            #Dictionary with all other Elements info:
            self.Other_elements = dict()
            #Substation bus information:
            self.subs = tuple()            
            #Getting the elements info:
            self.get_elementsinfo()
            #Buses connections dictionary:
            self.Bus_connect = dict()
            #Getting all the buses connections info:
            #self.Bus_connect must contain all the buses connections (enabled and disabled).
            self.get_busconnect()
            
            #Getting the voltage base values for each bus and classifying the 
            #lines as low, medium or high-voltage lines:
            #Voltage base kv values for each bus:
            self.bus_kvbases = dict() 
            #HV, MV and LV lines:
            self.HV_buses = list()
            self.MV_buses = list()
            self.LV_buses = list()
            #Transformers voltages dictionary:
            self.allTransfs = dict()
            self.allTransfskva = dict()
            #HV, MV and LV lines:
            self.HV_lines = dict()
            self.MV_lines = dict()
            self.LV_lines = dict()
            #Circuit length per voltage level:
            self.length_HV = 0
            self.length_MV = 0
            self.length_LV = 0
            #Number of lines in each voltage lines:
            self.n_HVLines = 0
            self.n_MVLines = 0
            self.n_LVLines = 0
            #Getting the voltage base values:
            self.get_kvbases()

            #Calculating the distance from each bus to the substation bus:
            self.bus_dist2subs = dict()
            self.calc_bus_dist2subs()
            #Buses interrupted by each protection device action.
            self.Protect_interrupt = dict()
            self.get_busesinterrupted()
            #Getting the buses that are part of each secondary network:
            self.allTransfs_sec_buses = dict()
            self.get_Transfs_sec_nets()
            
            #Circuit general information:
            self.psystem = dict()
            #Getting system info:
            self.get_systinfo()
            #Dictionary with all Distributed generators info:
            self.allDGs = dict()
            self.n_DGs = 0
            #Distributed generation power in the system:
            self.DG_power = [0,0]     #[kva,kw]
            #Getting DGs info:
            self.get_dginfo()

#            #Protection curves info:
#            self.TCC_curves = dict()
#            #building the TCC curves:
#            self.config_TCCcurves()
#            #Protection curves models:        
#            self.TCC_models = dict()
#            self.buid_TCCmodels()
#            #DG-Protection curves info:
#            self.LVRT_curves = dict()
#            #building the LVRT curves:
#            self.config_LVRTcurves()
#            #DG-Protection curves models:        
#            self.LVRT_models = dict()
#            self.buid_LVRTmodels()
#            
#            #CIRCUIT GRAPHS PLOT:
#            #Bus coordinates dictionary:
#            self.Buscoords = dict()
#            self.Buscoords_defined = 0            
#            #Getting the Buscoords values:
#            self.get_buscoords()        
#            #Building all the graphs:
#            self.build_graphs()


###############################################################################
#Basic info subroutines:
###############################################################################
            
    def get_linesinfo(self):
        #This subroutine gets some information related to the line objects.
        #It separates the ordinary current-carrying lines from the lines that 
        #are defined as switches.
        #It also gets the length and unit length of all lines.

        switches = list()
        real_Lines = list()
        #Identifying the switches and real lines:
        for line in self.dssLines.AllNames:
            line = line.lower()
            self.dssText.Command = '? Line.'+line+'.switch'
            if self.dssText.Result == 'True':
                switches.append(line)
            else:
                real_Lines.append(line)
        self.allSwitches = switches
        self.n_Lines = len(real_Lines)
        for line in real_Lines:
            self.dssText.Command = '? Line.'+line+'.length'
            line_length = self.dssText.Result
            self.dssText.Command = '? Line.'+line+'.units'
            line_unit = self.dssText.Result
            self.allLines[line] = [0,'km',float(line_length),line_unit.lower()]
        #calculating the total circuit length:
        self.calc_circlength()


    def calc_circlength(self):
        # This subroutine converts all the line length units to km and calculates
        # the total circuit length
        
        #Total feeder length:
        feeder_length = 0.0
        Unit_alarm = False
        #Converting all the lengths to km
        for line_key in self.allLines.keys():
            line = self.allLines[line_key]
            line_length = line[2]
            if line[3] =='none':
                temp_unit = self.std_unit_len
                if Unit_alarm == False:
                    Unit_alarm = True
                    print('\nLine '+line_key+' unit length was not informed.\n'+self.std_unit_len+' will be considered in this case.')
            else:
                temp_unit = line[3]
            #re-calculating the distance values for all tha allowed units:
            if temp_unit == 'mi':
                conv_to_km = 1.6093
            elif temp_unit == 'kft':
                conv_to_km = 0.3048
            elif temp_unit == 'km':
                conv_to_km = 1
            elif temp_unit == 'm':
                conv_to_km = 1/1000
            elif temp_unit == 'ft':
                conv_to_km = (0.3048)/1000
            elif temp_unit == 'in':
                conv_to_km = (0.0254)/1000
            elif temp_unit == 'cm':
                conv_to_km = 1/100000
            else:
                #In case the unit informed for a line segment is not allowed, this
                #line won't be considered in the length calculation and the user will
                #receive a message.
                conv_to_km = 0.0
                print('\nLine '+line_key+' has a non-allowed length unit: '+temp_unit)
                print('It will not  be considered in the circuit length calculation.')
            #calculating the line length:
            line_length = conv_to_km*line_length
            feeder_length += line_length
            #updating the line unit
            self.allLines[line_key][0] = line_length
        self.feeder_length = feeder_length
        

    def get_elementsinfo(self):
        #This subroutine gets the PD, PC, protection elements and substation
        #info, such as buses/terminals connections and nodes available.
        #Other elements are stored at the Other_elements dictionary.
        
        pd_elements = ['line','capacitor','reactor'] #2-terminal pds
        pc_elements = ['generator','load','pvsystem','storage','indmach012']
        for element in self.allElements:
            [element_type,element_name] = element.split(".")
            #print(element_type,element_name)
            Element_class = 0       #PD=1, PC=2, Dist-Protect=3, Substation=4, DG-Protect = 5, Other=0
            buses_12N = list()          #buses_12N may have the nodes information
            buses_orig_dest = list()    #buses_orig_dest just has the buses names            
            #Getting the buses info of each element:
            #PDElements:
            if element_type in pd_elements:
                Element_class = 1
                self.dssText.Command = "? "+element+".bus1"
                bus_1 = self.dssText.Result
                self.dssText.Command = "? "+element+".bus2"
                bus_2 = self.dssText.Result
                #This may happen for capacitors or reactors when bus2 is not defined:
                if bus_2 == '\x00\x00':
                    buses_12N = [bus_1,'none']
                else:
                    buses_12N = [bus_1,bus_2]
            #Transformers (GICTransformers are not being considered):
            elif element_type == 'transformer':
                #print('\n',element_type,element_name)
                Element_class = 1
                self.dssText.Command = "? "+element+".buses"
                buses = self.dssText.Result
                buses = buses.replace("[","").replace(" ]","").replace(",","")
                buses_12N = buses.split(" ")
            #PCElements:
            elif element_type in pc_elements:
                Element_class = 2
                self.dssText.Command = "? "+element+".bus1"
                buses_12N = [self.dssText.Result]
                #print(element_type,element_name,buses_12N)
            #Protection Elements:
            elif element_type == 'fuse':
                Element_class = 3
                self.dssText.Command = "? "+element+".MonitoredObj"
                monitobj = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".SwitchedObj"
                switchobj = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".FuseCurve"
                fuse_curve = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".RatedCurrent"
                rated_current = float(self.dssText.Result)
                self.dssText.Command = "? "+element+".Delay"
                delay = float(self.dssText.Result)
                curves_info = [('fusecurve',fuse_curve,delay,rated_current,1)]
                #Reclosing intervals [ms]:
                recintervals =  0
            elif element_type == 'recloser':
                Element_class = 3
                self.dssText.Command = "? "+element+".MonitoredObj"
                monitobj = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".SwitchedObj"
                switchobj = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".Delay"
                delay = float(self.dssText.Result)
                curves_info = list()
                #Fast curve:
                self.dssText.Command = "? "+element+".PhaseFast"
                PhaseFast = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".PhaseTrip"
                PhaseTrip = float(self.dssText.Result)   
                self.dssText.Command = "? "+element+".TDPhFast"
                TDPhFast = float(self.dssText.Result)  
                curves_info.append(('phasefast',PhaseFast,delay,PhaseTrip,TDPhFast))
                #Delayed curve:
                self.dssText.Command = "? "+element+".PhaseDelayed"
                PhaseDelayed = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".TDPhDelayed"
                TDPhDelayed = float(self.dssText.Result)               
                curves_info.append(('phasedelayed',PhaseDelayed,delay,PhaseTrip,TDPhDelayed))
                #Reclosing intervals [ms]:
                self.dssText.Command = "? "+element+".RecloseIntervals"
                recintervals = aux.get_numvalues(self.dssText.Result)
            elif element_type == 'relay':
                self.dssText.Command = "? "+element+".type"
                if self.dssText.Result.lower() == 'current':
                    Element_class = 3
                    self.dssText.Command = "? "+element+".MonitoredObj"
                    monitobj = self.dssText.Result.lower()
                    self.dssText.Command = "? "+element+".SwitchedObj"
                    switchobj = self.dssText.Result.lower()
                    self.dssText.Command = "? "+element+".Delay"
                    delay = float(self.dssText.Result)
                    curves_info = list()
                    #Phase curve:
                    self.dssText.Command = "? "+element+".Phasecurve"
                    Phasecurve = self.dssText.Result.lower()
                    self.dssText.Command = "? "+element+".PhaseTrip"
                    PhaseTrip = float(self.dssText.Result)   
                    self.dssText.Command = "? "+element+".TDPhase"
                    TDPhase = float(self.dssText.Result)
                    if Phasecurve != '\x00\x00':
                        curves_info.append(('phasecurve',Phasecurve,delay,PhaseTrip,TDPhase))
                    #Reclosing intervals [ms]:
                    self.dssText.Command = "? "+element+".RecloseIntervals"
                    recintervals = aux.get_numvalues(self.dssText.Result)
                elif self.dssText.Result.lower() == 'voltage':
                    Element_class = 5
                    self.dssText.Command = "? "+element+".MonitoredObj"
                    monitobj = self.dssText.Result.lower()
                    self.dssText.Command = "? "+element+".SwitchedObj"
                    switchobj = self.dssText.Result.lower()
                    self.dssText.Command = "? "+element+".Delay"
                    delay = float(self.dssText.Result)
                    curves_info = list()
                    #Phase curve:
                    self.dssText.Command = "? "+element+".undervoltcurve"
                    undervoltcurve = self.dssText.Result.lower()
                    self.dssText.Command = "? "+element+".overvoltcurve"
                    overvoltcurve = self.dssText.Result .lower()  
                    self.dssText.Command = "? "+element+".kvbase"
                    kvbase = float(self.dssText.Result)
                    #print(undervoltcurve,overvoltcurve,delay,kvbase)
                    curves_info.append((undervoltcurve,overvoltcurve,delay,kvbase))
            #Substation:
            elif element_type == 'vsource':
                Element_class = 4
                self.dssText.Command = "? "+element+".bus1"
                bus_1 = self.dssText.Result.lower()
                self.dssText.Command = "? "+element+".bus2"
                bus_2 = self.dssText.Result.lower()
                buses_12N = [bus_1,bus_2]
                
            #Adjusting the buses names:
            if buses_12N != list():
                #All buses names in lower case:
                for i in range(len(buses_12N)):
                    buses_12N[i] = buses_12N[i].lower()
                #Getting the terminals info:
                for bus in buses_12N:
                    buses_orig_dest.append(bus.split(".")[0])
            #Storing the data in each dictionary:
            if Element_class == 1:
                self.PD_elements[element] = (element_type,buses_12N,buses_orig_dest,element_name)
            elif Element_class == 2:
                self.PC_elements[element] = (element_type,buses_12N,buses_orig_dest,element_name)
            elif Element_class == 3:
                #In case the switchobj was not specified, it will be considered
                #the same as the monitobj:
                if switchobj not in self.allElements:
                    switchobj = monitobj
                self.Protect_elements[element] = (element_type,monitobj,switchobj,curves_info,recintervals,element_name)
            elif Element_class == 4:
                self.subs = (element_type,buses_12N,buses_orig_dest,element_name)
            elif Element_class == 5:
                #In case the switchobj was not specified, it will be considered
                #the same as the monitobj:
                if switchobj not in self.allElements:
                    switchobj = monitobj
                self.DG_Protect[element] = (element_type,monitobj,switchobj,curves_info,element_name)
            else:
                self.Other_elements[element] = (element_type,element_name)
        self.n_PDs = len(self.PD_elements)
        self.n_PCs = len(self.PC_elements)


    def get_busconnect(self):
        #This subroutine builds the Bus_connect dictionary, using the data from
        #the previously buit PD_elements and PC_elements dictionary.

        #Innitializing the dictionary:
        for bus in self.allBuses:
            self.Bus_connect[bus] = [list(),list()]
        #Adding the source element bus connection info:
        source_bus = self.subs[2]
        self.Bus_connect[source_bus[0]][0].append(self.subs[0]+'.'+self.subs[-1])

        #Finding the pre and pos PD elements from each bus:
        for pd_element in self.PD_elements.keys():
            PD_buses = self.PD_elements[pd_element][2]
            if PD_buses[0]!=PD_buses[1]:
                for i,pd_bus in enumerate(PD_buses):
                    if pd_bus != 'none':
                        if i == 0:
                            if pd_bus in self.Bus_connect:
                                self.Bus_connect[pd_bus][1].append(pd_element)
                            else:
                                self.Bus_connect[pd_bus] = [list(),[pd_element]]
                        else:
                            if pd_bus in self.Bus_connect:
                                self.Bus_connect[pd_bus][0].append(pd_element)
                            else:
                                self.Bus_connect[pd_bus] = [[pd_element],list()]
        #Adding the PC elements buses info:
        for pc_element in self.PC_elements.keys():
            [PC_bus] = self.PC_elements[pc_element][2]
            self.Bus_connect[PC_bus][1].append(pc_element)
            
    
    def calc_bus_dist2subs(self):
        #This subroutine calculates the distance of each bus to the substation.
        
        #Adding the source_bus with 0 as a reference:
        source_bus = self.subs[2][0]
        self.bus_dist2subs[source_bus] = 0        
        #Adding the next buses in the sequence:
        self.calc_bus_dist2subs_sequence(source_bus)


    def calc_bus_dist2subs_sequence(self,bus):
        #This subroutine calculates the distance of each bus to the substation.
        
        #Getting the PDs in the sequence:
        next_PDs_fw = list()
        for elmnt in self.Bus_connect[bus][1]:
            if elmnt in self.PD_elements:
                next_PDs_fw.append(elmnt)
        next_PDs_bk = list()
        for elmnt in self.Bus_connect[bus][0]:
            if elmnt in self.PD_elements:
                next_PDs_bk.append(elmnt)
        #Checking all the PDs forward:        
        for new_pd in next_PDs_fw:
            #Checking all the buses in the sequence of the PD element selected:
            for new_bus in self.PD_elements[new_pd][2][1:]:
                #Checking if the new_bus is different of the bus given at 
                #the subroutine call. 
                if new_bus != bus and new_bus != 'none':
                    #Checking if the PD element is a line. In this case the length 
                    #of the line will be taken into account, if not, the length 
                    #of the other elements, such as transformers, capacitors and 
                    #swithces won't be counted.
                    if new_pd.split('.')[0] == 'line' and new_pd.split('.')[1] in self.allLines and new_bus not in self.bus_dist2subs:
                        self.bus_dist2subs[new_bus] = self.bus_dist2subs[bus] + self.allLines[new_pd.split('.')[1]][0]
                        #print(new_bus,'=',self.bus_dist2subs[bus],'+',self.allLines[new_pd.split('.')[1]][0],'=',self.bus_dist2subs[new_bus],'km')
                        self.calc_bus_dist2subs_sequence(new_bus)
                    elif new_bus not in self.bus_dist2subs:
                        self.bus_dist2subs[new_bus] = self.bus_dist2subs[bus] + 1/1000
                        #print(new_bus,self.bus_dist2subs[new_bus])
                        self.calc_bus_dist2subs_sequence(new_bus)
        #Checking all the PDs backward:        
        for new_pd in next_PDs_bk:
            #Checking all the buses in the sequence of the PD element selected:
            for new_bus in self.PD_elements[new_pd][2][0:1]:
                #Checking if the new_bus is different of the bus given at 
                #the subroutine call. 
                if new_bus != bus and new_bus != 'none':
                    #Checking if the PD element is a line. In this case the length 
                    #of the line will be taken into account, if not, the length 
                    #of the other elements, such as transformers, capacitors and 
                    #swithces won't be counted.
                    if new_pd.split('.')[0] == 'line' and new_pd.split('.')[1] in self.allLines and new_bus not in self.bus_dist2subs:
                        self.bus_dist2subs[new_bus] = self.bus_dist2subs[bus] + self.allLines[new_pd.split('.')[1]][0]
                        #print(new_bus,'=',self.bus_dist2subs[bus],'+',self.allLines[new_pd.split('.')[1]][0],'=',self.bus_dist2subs[new_bus],'km')
                        self.calc_bus_dist2subs_sequence(new_bus)
                    elif new_bus not in self.bus_dist2subs:
                        self.bus_dist2subs[new_bus] = self.bus_dist2subs[bus] + 1/1000
                        #print(new_bus,self.bus_dist2subs[new_bus])
                        self.calc_bus_dist2subs_sequence(new_bus)


    def get_busesinterrupted(self):
        #This subroutine finds the buses affected by the openning action of each 
        #protection device.
        
        for prot_device in self.Protect_elements:
            affected_buses_list = list()
            switchobj = self.Protect_elements[prot_device][2]
            affected_buses_list = self.get_interruption_path(switchobj,self.PD_elements[switchobj][2][1:],affected_buses_list)
            self.Protect_interrupt[prot_device] = affected_buses_list
            #print('Buses',len(affected_buses_list))
            

    def get_interruption_path(self,prev_PD,bus_affected,affected_buses_list):
        #Given a starting bus, this subroutine finds all the buses located downstream
        #that bus in a radial system. These buses will be affected by an 
        #interruption due to the openning of a switch locate just upstream the 
        #starting bus given.

        new_buses = list()
        for bus in bus_affected:
            if bus not in affected_buses_list and bus!='none':
                affected_buses_list.append(bus)
                new_buses.append(bus)
        #Checking the circuit sequence:
        for bus in new_buses:
            #print(bus,self.Bus_connect[bus])
            back_PDs = self.Bus_connect[bus][0]
            next_PDs = self.Bus_connect[bus][1]
            for PD in next_PDs:
                if PD in self.PD_elements and PD != prev_PD:
                    affected_buses_list = self.get_interruption_path(PD,self.PD_elements[PD][2][1:],affected_buses_list)
            for PD in back_PDs:
                if PD in self.PD_elements and PD != prev_PD:
                    affected_buses_list = self.get_interruption_path(PD,self.PD_elements[PD][2][:1],affected_buses_list)
        return affected_buses_list


    def get_Transfs_sec_nets(self):
        #This subroutine gets all the buses at each secondary network from each
        #transformer. Part 1.
        
        for transf in self.allTransfs:         
            #List of available buses:
            secnet_buses = list()
            bus_list = self.PD_elements[transf][2][1:]
            for bus in bus_list:
                secnet_buses = self.get_buses_in_sec_net(bus,secnet_buses)
            self.allTransfs_sec_buses[transf] = secnet_buses
#        for transf in self.allTransfs_sec_buses:  
#            print(transf,self.allTransfs_sec_buses[transf])
        
        
    def get_buses_in_sec_net(self,new_bus,secnet_buses):
        #This subroutine gets all the buses at each secondary network from each
        #transformer. Part 2.
        
        #Adding the new bus:
        if new_bus not in secnet_buses:
            secnet_buses.append(new_bus)
        #Checking the new pds for more buses:
        pds_fw = self.Bus_connect[new_bus][1]
        for elmtn in pds_fw:
            if elmtn in self.PD_elements and self.PD_elements[elmtn][0]!='transformer' and self.PD_elements[elmtn][2][0]!=self.PD_elements[elmtn][2][1] and self.PD_elements[elmtn][2][1] not in secnet_buses:
                 secnet_buses = self.get_buses_in_sec_net(self.PD_elements[elmtn][2][1],secnet_buses)
        pds_bk = self.Bus_connect[new_bus][0]
        for elmtn in pds_bk:
            if elmtn in self.PD_elements and self.PD_elements[elmtn][0]=='line' and self.PD_elements[elmtn][2][0] not in secnet_buses:
                 secnet_buses = self.get_buses_in_sec_net(self.PD_elements[elmtn][2][0],secnet_buses)
        return secnet_buses
    

    def get_kvbases(self):
        #This subroutine creates the self.allTransfs dictionary with voltage 
        #information for all transformers and the self.allTransfskva dictionary
        #with the kva value of each transformer. 
        #Then, it gets the voltage base values for all buses starting from the 
        #substation and then, from each transformer until finding all buses kvBases
        #that are connected to the circuit.

        #Getting the voltage kV and powerkVA values of each transformer:
        for PD in self.PD_elements:
            if self.PD_elements[PD][0] == 'transformer':
                self.dssText.Command = '? '+PD+'.kVs'
                self.allTransfs[PD] = aux.get_numvalues(self.dssText.Result)
                self.dssText.Command = "? "+PD+".kvas"
                self.allTransfskva[PD] = max(aux.get_numvalues(self.dssText.Result))
#        print(self.allTransfs)

        #kV-base voltage values dictionary:
        base_buses = dict()
        #Getting the base voltage value for each bus starting from the the source:
        source_name = self.subs[0]+'.'+self.subs[-1]
        self.dssText.Command = '? '+source_name+'.basekv'
        vsource_basekv = float(self.dssText.Result)
        source_bus = self.subs[2][0]
        self.dssCircuit.SetActiveBus(source_bus)
        sourcebus_kVBase = round(self.dssBus.kVBase,4)
        KV_value = round(self.dssBus.VMagAngle[0]/1000,4)
        #Checking the bus kv Values:
        if abs(sourcebus_kVBase-KV_value)<0.1*sourcebus_kVBase:
            bus_kvbase = sourcebus_kVBase
        elif abs(vsource_basekv-KV_value)<abs(sourcebus_kVBase-KV_value) and abs(vsource_basekv-KV_value)<0.1*vsource_basekv:
            bus_kvbase = vsource_basekv
        elif min(abs(KV_value-np.array(self.kvbases)))<0.1*KV_value:
            bus_kvbase = 0
            for value in self.kvbases:
                if abs(value-KV_value)<0.1*value and abs(value-KV_value)<abs(KV_value-bus_kvbase):
                    bus_kvbase = value
        else:
            avg_KV_value = 0
            num_nodes_abc = 0
            j=0
            for node in self.dssBus.Nodes:
                if node in[1,2,3]:
                    avg_KV_value+=self.dssBus.VMagAngle[2*j]
                    num_nodes_abc+=1
                j+=1
            bus_kvbase = round(avg_KV_value/(num_nodes_abc*1000),3)
        #Adding the kV base to all buses at the main trunk:
        if source_bus not in base_buses:
            base_buses = self.find_circ_kvpath(source_bus,bus_kvbase,base_buses)

        #Adding the new buses kvBase values starting from the transformers in 
        #both directions to reach the buses with no kvBase values found yet:
        for transformer in self.allTransfs:
            transf_buses = self.PD_elements[transformer][2]
            for i,bus in enumerate(transf_buses):
                if bus not in base_buses:
                    transf_basekv = self.allTransfs[transformer][i]
                    self.dssCircuit.SetActiveBus(bus)
                    transfbus_kVBase = round(self.dssBus.kVBase,4)
                    KV_value = round(self.dssBus.VMagAngle[0]/1000,4)
                    #Checking the bus kv Values:
                    if abs(transfbus_kVBase-KV_value)<0.2*transfbus_kVBase or KV_value==0.0:
                        bus_kvbase = transfbus_kVBase
                    elif abs(transf_basekv-KV_value)<abs(transfbus_kVBase-KV_value) and abs(transf_basekv-KV_value)<0.1*transf_basekv:
                        bus_kvbase = transf_basekv
                    elif min(abs(KV_value-np.array(self.kvbases)))<0.1*KV_value:
                        bus_kvbase = 0
                        for value in self.kvbases:
                            if abs(value-KV_value)<0.1*value and abs(value-KV_value)<abs(KV_value-bus_kvbase):
                                bus_kvbase = value
                    else:
                        avg_KV_value = 0
                        num_nodes_abc = 0
                        j=0
                        for node in self.dssBus.Nodes:
                            if node in[1,2,3]:
                                avg_KV_value+=self.dssBus.VMagAngle[2*j]
                                num_nodes_abc+=1
                            j+=1
                        bus_kvbase = round(avg_KV_value/(num_nodes_abc*1000),3)
                    base_buses = self.find_circ_kvpath(bus,bus_kvbase,base_buses)

        #Buses and lines will be classyfied as low voltage (LV), medium voltage (MV) 
        #or high voltage (HV) according to the following criteria:
        # < 1 kv                --> LV
        # >= 1 kv e < 72.5kv    --> MV
        # >= 72.5 kv            --> HV
        #Classifying the buses:
        for bus in base_buses:
            if base_buses[bus]<1.0:
                self.LV_buses.append(bus)
            elif base_buses[bus]>=1.0 and base_buses[bus]<72.5:
                self.MV_buses.append(bus)
            else:
                self.HV_buses.append(bus)
        self.bus_kvbases = base_buses
        #Classifying the lines:
        for line_key in self.allLines.keys():
            orig_bus_line = self.PD_elements['line.'+line_key][2][0]
            dest_bus_line = self.PD_elements['line.'+line_key][2][1]
            #Checking both line buses:
            if orig_bus_line in base_buses:
                if base_buses[orig_bus_line]<1.0:                
                    self.LV_lines[line_key] = self.allLines[line_key]
                    self.length_LV += self.allLines[line_key][0]
                elif base_buses[orig_bus_line]>=1.0 and base_buses[orig_bus_line]<72.5:
                    self.MV_lines[line_key] = self.allLines[line_key]
                    self.length_MV += self.allLines[line_key][0]
                else:
                    self.HV_lines[line_key] = self.allLines[line_key]
                    self.length_HV += self.allLines[line_key][0]
            elif dest_bus_line in base_buses:
                if base_buses[dest_bus_line]<1.0:                
                    self.LV_lines[line_key] = self.allLines[line_key]
                    self.length_LV += self.allLines[line_key][0]
                elif base_buses[dest_bus_line]>=1.0 and base_buses[dest_bus_line]<72.5:
                    self.MV_lines[line_key] = self.allLines[line_key]
                    self.length_MV += self.allLines[line_key][0]
                else:
                    self.HV_lines[line_key] = self.allLines[line_key]
                    self.length_HV += self.allLines[line_key][0]
            #In this case, none of the line buses has a kv base value defined.
            #It means the line might not be connected to the rest of the circuit.
            else:
                self.disabled_lines[line_key] = self.allLines[line_key]
        #Counting the number of lines from each type:
        self.n_HVLines = len(self.HV_lines)
        self.n_MVLines = len(self.MV_lines)
        self.n_LVLines = len(self.LV_lines)


    def find_circ_kvpath(self,start_bus,kv_value,base_buses):
        #This subroutine should receive a start_bus, a voltage base value and
        #the base_buses dict. It will find the sequence of the circuit in both 
        #directions and assign a voltage base value to each bus until the circuit 
        #reaches a new transformer, another already indentified bus or the last
        #bus in the sequence.

        base_buses[start_bus] = kv_value
        #Checking the bus connections:
        next_PDs_back = self.Bus_connect[start_bus][0]
        next_PDs_forw = self.Bus_connect[start_bus][1]
        #print('PDs back:',next_PDs_back)
        #print('PDs forward:',next_PDs_forw)
        #----------------------------------------------------------------------
#        Checking the other buses starting from the start_bus:
#        (bus_back)       (start_bus)          (bus_forw)
#            |-----PDs_back-----|-----PDs_forw-----|
        #----------------------------------------------------------------------
        #Going forward:
        for PD in next_PDs_forw:
            if PD in self.PD_elements and self.PD_elements[PD][0]!='transformer' and (self.PD_elements[PD][2][1] not in base_buses) and (self.PD_elements[PD][2][1] != 'none'):
                base_buses = self.find_circ_kvpath(self.PD_elements[PD][2][1],kv_value,base_buses)
        #Going backward:
        for PD in next_PDs_back:
            if PD in self.PD_elements and self.PD_elements[PD][0]!='transformer' and (self.PD_elements[PD][2][0] not in base_buses) and (self.PD_elements[PD][2][1] != 'none'):
                base_buses = self.find_circ_kvpath(self.PD_elements[PD][2][0],kv_value,base_buses)
        return base_buses


    def get_systinfo(self):
        #This subroutine gets some important informations related to the 
        #electric system, like frequency, 1ph and 3pg short-circuit relation,etc.
        
        #Getting the system frequency of operation and calculating its cycle:
        self.dssText.Command = "? "+self.subs[0]+"."+self.subs[-1]+".basefreq"
        self.freq = float(self.dssText.Result)
        self.cycle = 1/self.freq  #[s]
        #Circuit name:
        self.psystem['Name'] = self.dssCircuit.Name
        #System base kv and pu info:
        self.dssText.Command = "? "+self.subs[0]+"."+self.subs[-1]+".basekv"
        self.psystem['basekv'] = float(self.dssText.Result)
        self.dssText.Command = "? "+self.subs[0]+"."+self.subs[-1]+".pu"
        self.psystem['pu'] = float(self.dssText.Result)
        #Getting the system MVA 1ph and 3ph short-circuit values:
        self.dssText.Command = "? "+self.subs[0]+"."+self.subs[-1]+".MVAsc1"
        self.psystem['MVAsc1'] = float(self.dssText.Result)
        self.dssText.Command = "? "+self.subs[0]+"."+self.subs[-1]+".MVAsc3"
        self.psystem['MVAsc3'] = float(self.dssText.Result)
        #System baseMVA
        self.dssText.Command = "? "+self.subs[0]+"."+self.subs[-1]+".baseMVA"
        self.psystem['baseMVA'] = float(self.dssText.Result)


    def get_dginfo(self):
        #This subroutine gets some important informations related to the 
        #distributed generators.
        dgs = ['generator','pvsystem']

        for pc_elmnt in self.PC_elements:
            if self.PC_elements[pc_elmnt][0] in dgs:
                self.dssText.Command = "? "+pc_elmnt+".kv"
                kv = float(self.dssText.Result)
                self.dssText.Command = "? "+pc_elmnt+".kva"
                kva = float(self.dssText.Result)
                self.dssText.Command = "? "+pc_elmnt+".pf"
                pf = float(self.dssText.Result)
                kw = pf*kva
                self.allDGs[pc_elmnt] = (self.PC_elements[pc_elmnt][0],kv,kva,kw,pf,self.PC_elements[pc_elmnt][-1])
                #Adding the DG power rated values:
                self.DG_power[0] += kva
                self.DG_power[1] += kw
        #Counting the DGs:
        self.n_DGs = len(self.allDGs)


###############################################################################
#Protection-related subroutines:
###############################################################################
        
    def config_TCCcurves(self):
        #This subroutine configures the TCC curves of all protection elements.
        #The curves will be read from a "TCC_Curve.dss" file in the same folder
        #of the circuit working directory and adpated according to each protection
        #element settings.
        
        if os.path.exists(self.filepath+'\TCC_Curve.dss'):
            TCC_info = self.load_TCCfile()
            #Adapting the curves from the file to the protection elements settings:
            TCC_info_adjust = dict()
            for elmnt in self.Protect_elements:
                for curve in self.Protect_elements[elmnt][3]:
                    T_delay = curve[2]
                    I_mult = curve[3]
                    T_mult = curve[4]
                    TCC_info_adjust[elmnt+' '+curve[0].lower()] = (I_mult*np.array(TCC_info[curve[1]][1] ),T_delay+T_mult*np.array(TCC_info[curve[1]][2]))
    
#            #Plotting the Time-current curves:
#            plt.figure('Time-current curves - Protection elements')    
#            plt.clf()
#            min_x = 0
#            max_x = 0
#            min_y = 0
#            max_y = 0 
#            for curve in TCC_info_adjust:               
#                plt.plot(TCC_info_adjust[curve][0], TCC_info_adjust[curve][1], label = curve.replace(" ","\n"), linewidth = 2.0)
#                #Calculating x limits:
#                if min(TCC_info_adjust[curve][0])<min_x:
#                    min_x = min(TCC_info_adjust[curve][0])
#                if max(TCC_info_adjust[curve][0])>max_x:
#                    max_x = max(TCC_info_adjust[curve][0])
#                #Calculating y limits:
#                if min(TCC_info_adjust[curve][1])<min_y:
#                    min_y = min(TCC_info_adjust[curve][1])
#                if max(TCC_info_adjust[curve][1])>max_y:
#                    max_y = max(TCC_info_adjust[curve][1])
#            plt.yscale('log')
#            plt.xscale('log')
#            plt.title('Time-current curves \nCircuit: '+self.psystem['Name'])
#            plt.xlabel('Current (A)')
#            plt.ylabel('Time (s)')
#            plt.xlim([0,max_x])
#            plt.ylim([0,max_y])
#            plt.grid(True)
#            #plt.legend(loc='center left', bbox_to_anchor=(1, 0.5));
#            plt.legend(loc='best');
#            plt.show() 
    
            self.TCC_curves = TCC_info_adjust
        else: 
            print('\nFile',self.filepath+'\TCC_Curve.dss not found!')


    def load_TCCfile(self,file_path=None):
        #This subroutine reads the TCC curves in the TCCCurve.dss file and returns
        #the TCC_info list
        
        #TCC curves info list:
        TCC_info = dict()
        #Openning the file:
        if file_path == None:
            inFile = open(self.filepath+'\TCC_Curve.dss')
        else:
            inFile = open(file_path)
        #Each line is a string with the whole content of each line in the file
        for line in inFile:
            #Reading each line:
            fields = line.split(' ')
            #fields is a list of blocks of characters.
            #Each block is determined by a blank space in the line.
            if fields[0].lower() == 'new':
                #Getting the TCC curve name:
                #fields[1] contains TCC_curbe.TCC_name
                TCC_name = fields[1].replace('"','').split('.')[-1].lower()
                #Getting the number of points in each TCC curve:
                #fields[2] = 'npts=number'
                npts = int(fields[2].split('=')[-1])
                fields3 = [x for x in fields[3:] if x != '']
                array_len = int(len(fields3)/2)
                #Getting the C_array and T_array in string forms:
                #The C and T vectors must come in this order.
                C_array_str = fields3[0:array_len]
                T_array_str = fields3[array_len:]                
                C_array = list()
                T_array = list()
                #Transforming the C_array_str in a list with numbers
                for val in C_array_str:
                   the_number = aux.get_numval(val)
                   if the_number!= None:
                       C_array.append(float(the_number))                       
                #Transforming the T_array_str in a list with numbers
                for val in T_array_str:
                   the_number = aux.get_numval(val)
                   if the_number!= None:
                       T_array.append(float(the_number))                            
                TCC_info[TCC_name] = (npts,C_array,T_array)            
        return TCC_info


    def buid_TCCmodels(self):
        #This subroutine builds the TCC curves models of all protection elements.
        #These models will be used posteriorly to determine the time of the protection 
        #actuation.
        
        for curve in self.TCC_curves:
            (c_intervals,t_intervals) = aux.split_intervals_norepeat(self.TCC_curves[curve][0],self.TCC_curves[curve][1])
            n_parts = len(c_intervals)
            all_curvmodels = list()
            for i in range(n_parts):
                #print(c_intervals[i],t_intervals[i])
                model = np.polyfit(c_intervals[i], t_intervals[i],1)
                #estYVals = pylab.polyval(model, c_intervals[i])
                #R2_new = aux.r_squared(t_intervals[i], estYVals)
                all_curvmodels.append(model)
                #print(model)
            
#            print(curve,len(self.TCC_curves[curve][0]),n_parts)
            
#            plt.close('TCC Polyfit test ' + curve)
#            plt.figure('TCC Polyfit test ' + curve)    
#            plt.clf()
#            plt.plot(self.TCC_curves[curve][0],self.TCC_curves[curve][1],'ko',label = 'Orig. values', linewidth = 1.0)
#            for i in range(n_parts):
#                plt.plot(c_intervals[i],pylab.polyval(all_curvmodels[i], c_intervals[i]),label = 'interval:'+str(i+1), linewidth = 2.0)
#            plt.title('Time-current plot - ' + curve)
#            plt.xlabel('Current [A]')
#            plt.ylabel('Time [s]')
#            plt.yscale('log')
#            plt.xscale('log')
#            plt.grid(True)
#            if len(all_curvmodels)<10:
#                plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.19),fancybox=True, shadow=False, ncol=3)
#            plt.show()
                
            self.TCC_models[curve] = (c_intervals[:len(all_curvmodels)],t_intervals[:len(all_curvmodels)],all_curvmodels)
    

    def config_LVRTcurves(self):
        #This subroutine configures the LVRT curves that will be used as reference
        #for the DG anti-islanding protection elements. The curves will be read
        #from a "LVRT_Curve.dss" file in the folder "__LVRTcurves__" which is 
        #in the same folder of the DSPA working directory.
        
        LVRT_info = self.load_TCCfile(self.DSS_LVRT_filename)

#        #Plotting the Time-voltage curves:
#        plt.figure('Voltage-current curves - Protection elements')    
#        plt.clf()
#        min_x = 0
#        max_x = 0
#        min_y = 0
#        max_y = 0 
#        for curve in LVRT_info:               
#            plt.plot(LVRT_info[curve][1], LVRT_info[curve][2], label = curve.replace(" ","\n"), linewidth = 2.0)
#            #Calculating x limits:
#            if min(LVRT_info[curve][1])<min_x:
#                min_x = min(LVRT_info[curve][1])
#            if max(LVRT_info[curve][1])>max_x:
#                max_x = max(LVRT_info[curve][1])
#            #Calculating y limits:
#            if min(LVRT_info[curve][2])<min_y:
#                min_y = min(LVRT_info[curve][2])
#            if max(LVRT_info[curve][2])>max_y:
#                max_y = max(LVRT_info[curve][2])
#        plt.title('Time-voltage curves')
#        plt.xlabel('Voltage (pu)')
#        plt.ylabel('Time (s)')
#        max_y = math.ceil(max_y*10)/10
#        if max_x < 1:
#            max_x = 1
#        plt.xlim([0,max_x])
#        plt.ylim([-0.01,max_y])
#        plt.grid(True)
##        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
#        plt.legend(loc='upper left');
#        plt.show() 

        self.LVRT_curves = LVRT_info
        

    def buid_LVRTmodels(self):
        #This subroutine builds the LVRT-models of all LVRT curves.
        #These models will be used posteriorly to determine the time of the  
        #protection actuation.        

        for curve in self.LVRT_curves:
            v_intervals = aux.split_intervals(self.LVRT_curves[curve][1])
            t_intervals = aux.split_intervals(self.LVRT_curves[curve][2])
            n_parts = len(v_intervals)
            all_curvmodels = list()
            for i in range(n_parts):
                model = np.polyfit(v_intervals[i], t_intervals[i],1)
                #estYVals = pylab.polyval(model, c_intervals[i])
                #R2_new = aux.r_squared(t_intervals[i], estYVals)
                all_curvmodels.append(model)
            
#            plt.close('LVRT Polyfit test ' + curve)  
#            plt.figure('LVRT Polyfit test ' + curve)    
#            plt.clf()
#            plt.plot(self.LVRT_curves[curve][1],self.LVRT_curves[curve][2],'ko',label = 'Orig. values', linewidth = 1.0)
#            for i in range(n_parts):
#                plt.plot(v_intervals[i],pylab.polyval(all_curvmodels[i], v_intervals[i]),label = 'interval:'+str(i+1), linewidth = 2.0)
#            plt.title('Time-voltage plot - ' + curve)
#            plt.xlabel('Voltage [pu]')
#            plt.ylabel('Time [s]')
#            plt.grid(True)
#            plt.xlim([0,1])
#            #plt.legend(loc='upper right')
#            #plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.19),fancybox=True, shadow=False, ncol=3)
#            plt.show()
                
            self.LVRT_models[curve] = (v_intervals,t_intervals,all_curvmodels)

    
    def get_protactiontime(self,prot_device,curve_name,Icc):
        #This subroutine calculates the actuation time of a given curve of a given
        #protection device. 
        
        #Current intervals:
        c_intervals = self.TCC_models[prot_device+' '+curve_name][0]       
        action_time = 0
        model_number = 0
        #In case the current is too small:
        if Icc<c_intervals[0][0]:
            action_time = math.inf #('infinite')
        #In case the current is too large:
        elif Icc>c_intervals[-1][1]:
            Icc = c_intervals[-1][1]
            model_number = len(c_intervals)-1
        #General case:
        else:
            i=0
            for interval in c_intervals:
                if Icc>=interval[0] and Icc<=interval[1]:
                    model_number = i
                    break
                i+=1
        #Calculating the protection device action time:
        if action_time == 0:
            action_time = 1000*pylab.polyval(self.TCC_models[prot_device+' '+curve_name][2][model_number], Icc)
        return action_time


    def get_DGprotactiontime(self,vmag_pu):
        #This subroutine calculates the actuation time of a DG protection device 
        #which follows both curves and with a voltage given by vmag_pu.
        
        disc_time = dict()
        for curve in self.LVRT_models:
            action_time = 0
            model_number = 0
            #Voltage intervals:
            v_intervals = self.LVRT_models[curve][0]
#            print(curve,v_intervals)
            #In case the voltage is not low enough:
            if vmag_pu>v_intervals[-1][-1]:
                action_time = math.inf #('infinite')
            #General case:
            else:
                i=0
                for interval in v_intervals:
                    if vmag_pu>=interval[0] and vmag_pu<=interval[1]:
                        model_number = i
                        break
                    i+=1
                #Calculating the protection device action time:
                action_time = 1000*pylab.polyval(self.LVRT_models[curve][2][model_number], vmag_pu)
            disc_time[curve] = action_time
        return disc_time            


###############################################################################
#Circuit Graphics methods:
###############################################################################

    def get_buscoords(self):
        #This subroutine builds and plots the circuit graph according to the
        #connections given:
        BusCoords = dict()
        count_defined = 0
        coords_estimated = 0
        coords_not_estimated = 0
        for bus in self.Bus_connect.keys():
            self.dssCircuit.SetActiveBus(bus);
#            print(bus,self.dssBus.x,self.dssBus.y)
            if self.dssBus.Coorddefined:
                BusCoords[bus] = (self.dssBus.x,self.dssBus.y)
                count_defined+=1
            else:
#                print('\nCoordinates not identified!')
#                print('Bus:',bus,self.dssBus.x,self.dssBus.y)
#                print(self.Bus_connect[bus])
                #Identigying the PDs connected to the bus:
                pd1 = None
                pd2 = None
                if self.Bus_connect[bus][0] != list():
                    for pd in self.Bus_connect[bus][0]:
                        if pd in self.PD_elements:
                            pd1 = pd
                            break
                if self.Bus_connect[bus][1] != list():
                    for pd in self.Bus_connect[bus][1]:
                        if pd in self.PD_elements:
                            pd2 = pd
                            break
#                print('Pds:',pd1,pd2)
                #Identifying the extremity buses of each pd connected to that bus:
                pd1_b1 = 'none'
                pd2_b2 = 'none'
                if pd1 != None and self.PD_elements[pd1][2][0] != 'none':
                    pd1_b1 = self.PD_elements[pd1][2][0]
                if pd2 != None and self.PD_elements[pd2][2][1] != 'none':
                    pd2_b2 = self.PD_elements[pd2][2][1]
#                print('PD buses:',pd1_b1,pd2_b2)
                pd1_coords = (0,0)
                pd2_coords = (0,0)
                #If there is a pd1_b1:
                if pd1_b1 != 'none':
                    self.dssCircuit.SetActiveBus(pd1_b1)
                if pd1_b1 != 'none' and self.dssBus.Coorddefined:
                    if pd1_b1 in BusCoords:
                        pd1_coords = BusCoords[pd1_b1]
#                        print('pegou referencia 1 - ja tava')
                    else:
                        pd1_coords = (self.dssBus.x,self.dssBus.y)
#                        print('pegou referencia 1 - ainda nao tava')
                    self.dssCircuit.SetActiveBus(pd2_b2)
                    if pd2_b2 in BusCoords:
                        pd2_coords = BusCoords[pd2_b2]
#                            print('pegou referencia 2 - ja tava')
                    elif self.dssBus.Coorddefined:
                        pd2_coords = (self.dssBus.x,self.dssBus.y)
#                            print('pegou referencia 2 - ainda nao tava')
                    else:
                        #If there is no pd2_coords defined:
                        pd2_coords = pd1_coords
#                        print('Não há buscoords para pd2_b2!\nB2 Baseado em B1.')
                    BusCoords[bus] = ((pd1_coords[0]+pd2_coords[0])/2 ,(pd1_coords[1]+pd2_coords[1])/2)
                    coords_estimated += 1
#                    print('Pds 1 & 2 coords:',pd1_coords,pd2_coords)
#                    print('Estimated coordinates:',BusCoords[bus])
                #If there is no pd1_b1 defined:
                elif pd2_b2 != 'none':
                    pd2_coords = tuple()
                    self.dssCircuit.SetActiveBus(pd2_b2)
                    if pd2_b2 in BusCoords:
                        pd2_coords = BusCoords[pd2_b2]
                    elif pd2_b2 in self.Bus_connect and self.dssBus.Coorddefined:
                        pd2_coords = (self.dssBus.x,self.dssBus.y)
                    if pd2_coords != tuple():
                        BusCoords[bus] = pd2_coords
                        coords_estimated += 1
#                        print('Pds 1 & 2 coords:',pd1_coords,pd2_coords)
#                        print('Estimated coordinates:',BusCoords[bus])
                    else:
                        coords_not_estimated += 1
#                        print('Pds 1 & 2 coords:',pd1_coords,pd2_coords)
#                        print('Coordinates not estimated!')
                else:
                    coords_not_estimated += 1
#                    print('Pds 1 & 2 coords:',pd1_coords,pd2_coords)
#                    print('Coordinates not estimated!')
        self.Buscoords = BusCoords
        self.Buscoords_defined = count_defined
#        print('\nBuses in the system:',len(self.Bus_connect.keys()),' - Coordinates defined:',count_defined)
#        print('Coordinates estimated:',coords_estimated)
#        print('Coordinates not estimated:',coords_not_estimated)
#        print('Buses in the graph:',len(BusCoords),'\n')

 
    def plot_circuit(self):
        #This subroutine plots the circuit according to the Buscoords given:

        if self.Buscoords_defined > 0:
            if self.n_Buses<100:
                self.dssText.Command = "Set MarkTransformers=yes"
                self.dssText.Command = "plot circuit Power dots=y labels=y subs=y"
            elif self.n_Buses<500:
                self.dssText.Command = "Set MarkTransformers=yes"
                self.dssText.Command = "plot circuit Power dots=y labels=n subs=y"
            else:
                self.dssText.Command = "plot circuit Power dots=n labels=n subs=y"


    def build_graphs(self):
        #This subroutine builds and plots the complete circuit graph
        #All the buses whose coordinates are in self.Buscoords will be considered as graph nodes.
        #All PD elements whose buses are different (and whose buses  coordinates
        #are also in self.Buscoords) will be considered as edges of the graph.

        #Circuit graphs:
        self.circ_graph = nx.Graph()
        self.circ_graph_edge_labels = dict()
        #Circuit elements graphs:
        self.G_loads = nx.Graph()
        self.G_switches = nx.Graph()
        self.G_loads_coords = dict()
        self.G_switches_coords = dict()  
        self.Prot_circ_graph = nx.Graph()
        self.Prot_circ_graph_coords = dict()
        self.Prot_circ_graph_edge_labels = dict()
        self.Transf_graph = nx.Graph()
        self.G_subs = nx.Graph()
        self.Transf_graph_coords = dict()
        self.G_subs_coords = dict()
        #Loads size graphs:
        self.G_loadSize = dict()
        self.small_loads = nx.Graph()   #<=100kva
        self.medium_loads = nx.Graph()  #>100kva and <1000kva
        self.big_loads = nx.Graph()     #>1000kva
        
        #Adding the buses coordinates found to each graph:
        if len(self.Buscoords)>0:
            #self.circ_graph is the complete circuit graph:
            #Adding all buses as nodes:
            self.circ_graph.add_nodes_from(list(self.Buscoords.keys()))
            all_edges_in_graph = list()          
            #Adding the PD elements as edges:
            for pd in self.PD_elements:
                bus1 = self.PD_elements[pd][2][0]
                bus2 = self.PD_elements[pd][2][1:]
                for bus in bus2:
                    #Adding the elements to G:
                    if bus1 != bus and bus1 != 'none' and bus != 'none' and bus1 in self.Buscoords and bus in self.Buscoords and (bus1,bus) not in all_edges_in_graph:
                        self.circ_graph.add_edge(bus1,bus)
                        if pd[0:4]=='line':
                            if pd.split('.')[1] in self.allLines:
                                self.circ_graph_edge_labels[(bus1,bus)] = str(round(self.allLines[pd.split('.')[1]][0],2))
                            elif pd.split('.')[1] in self.allSwitches:
                                self.circ_graph_edge_labels[(bus1,bus)] = str('sw')
                            else:
                                self.circ_graph_edge_labels[(bus1,bus)] = str('Object unknown')
                        else:
                            self.circ_graph_edge_labels[(bus1,bus)] = pd.split('.')[1]
                        all_edges_in_graph.append((bus1,bus))
                    elif bus1 != bus and bus1 != 'none' and bus != 'none' and bus1 in self.Buscoords and bus in self.Buscoords and (bus1,bus) in all_edges_in_graph:
                        if pd[0:4]=='line':
                            if pd.split('.')[1] in self.allLines:
                                self.circ_graph_edge_labels[(bus1,bus)] =  self.circ_graph_edge_labels[(bus1,bus)]+'\n'+ str(round(self.allLines[pd.split('.')[1]][0],2))
                            elif pd.split('.')[1] in self.allSwitches:
                                self.circ_graph_edge_labels[(bus1,bus)] =  self.circ_graph_edge_labels[(bus1,bus)]+'\n'+ str('sw')
                            else:
                                self.circ_graph_edge_labels[(bus1,bus)] =  self.circ_graph_edge_labels[(bus1,bus)]+'\n'+ str('Object unknown')
                        else:
                            self.circ_graph_edge_labels[(bus1,bus)] = self.circ_graph_edge_labels[(bus1,bus)]+'\n'+ pd.split('.')[1]
            
            #Voltage Graphs:
            G_LV = nx.Graph()
            G_MV = nx.Graph()
            G_HV = nx.Graph()
            Transf_graph = nx.Graph()
            G_subs = nx.Graph()
            #VGraphs coords:
            G_LV_bus_coords = dict()
            G_MV_bus_coords = dict()
            G_HV_bus_coords = dict()
            Transf_graph_coords = dict()
            G_subs_coords = dict()
            #Adding all the buses to its respective voltage category:
            for key in self.Buscoords.keys():
                if self.bus_kvbases[key]<1.0:
                    G_LV.add_node(key)
                    G_LV_bus_coords[key] = self.Buscoords[key]
                elif self.bus_kvbases[key]>=1.0 and self.bus_kvbases[key]<72.5:
                    G_MV.add_node(key)
                    G_MV_bus_coords[key] = self.Buscoords[key]
                else:
                    G_HV.add_node(key)
                    G_HV_bus_coords[key] = self.Buscoords[key]   
            #Adding all PD elements as edges to its respective graphs:
            for pd in self.PD_elements:
                #Getting the buses names:
                bus1 = self.PD_elements[pd][2][0]
                bus2 = self.PD_elements[pd][2][1:]
                if self.PD_elements[pd][0] != 'transformer':
                    for bus in bus2:
                        if bus1 != bus and bus1 != 'none' and bus != 'none':
                            if bus1 in G_LV_bus_coords and bus in G_LV_bus_coords:
                                G_LV.add_edge(bus1,bus)
                            elif bus1 in G_MV_bus_coords and bus in G_MV_bus_coords:
                                G_MV.add_edge(bus1,bus)
                            elif bus1 in G_HV_bus_coords and bus in G_HV_bus_coords:
                                G_HV.add_edge(bus1,bus)
                elif self.PD_elements[pd][0] == 'transformer':
                    Transf_graph.add_node(bus1)
                    Transf_graph_coords[bus1] = self.Buscoords[bus1]
#                    for bus in bus2:
#                        if bus1 != bus and bus1 != 'none' and bus != 'none' and bus1 in self.Buscoords and bus in self.Buscoords:
#                            Transf_graph.add_edge(bus1,bus)
#                            Transf_graph_coords[bus1] = self.Buscoords[bus1]
#                            Transf_graph_coords[bus] = self.Buscoords[bus]
            #Creating the substation graph:
            if self.subs[2][0] in self.Buscoords:
                G_subs.add_node(self.subs[2][0])
                G_subs_coords[self.subs[2][0]] = self.Buscoords[self.subs[2][0]]
            #Updating the graphs info:
            #Voltage Graphs:
            self.G_LV = G_LV
            self.G_MV = G_MV
            self.G_HV = G_HV
            self.Transf_graph = Transf_graph
            self.G_subs = G_subs
            #VGraphs coords:
            self.G_LV_bus_coords = G_LV_bus_coords
            self.G_MV_bus_coords = G_MV_bus_coords
            self.G_HV_bus_coords = G_HV_bus_coords
            self.Transf_graph_coords = Transf_graph_coords
            self.G_subs_coords = G_subs_coords
            
            #Protection Graph:
            Prot_circ_graph = nx.Graph()
            Prot_circ_graph_coords = dict()
            Prot_circ_graph_edge_labels = dict()
            for prot_dev in self.Protect_elements:
                switch_obj = self.Protect_elements[prot_dev][2]
                buses = self.PD_elements[switch_obj][2]                
                #Adding the buses as nodes and the coordinates:
                for bus in buses:
                    if bus in self.Buscoords:
                        Prot_circ_graph.add_node(bus)
                        Prot_circ_graph_coords[bus] = self.Buscoords[bus]
                #Adding the protection device as an edge:
                if buses[0] in self.Buscoords and buses[1] in self.Buscoords:
                    Prot_circ_graph.add_edge(buses[0],buses[1])
                    Prot_circ_graph_edge_labels[(buses[0],buses[1])] = prot_dev.split('.')[0]+'\n'+prot_dev.split('.')[1]            
            #Updating the protection graphs info:
            self.Prot_circ_graph = Prot_circ_graph
            self.Prot_circ_graph_coords = Prot_circ_graph_coords
            self.Prot_circ_graph_edge_labels = Prot_circ_graph_edge_labels
            
            #Loads Graph:
            for pc in self.PC_elements:
                if self.PC_elements[pc][0]=='load':
                    bus = self.PC_elements[pc][2][0]
                    if bus in self.Buscoords:
                        self.G_loads.add_node(bus)    
                        self.G_loads_coords[bus] = self.Buscoords[bus]
            #Loads-by-size Graph:
            for pc in self.PC_elements:
                if self.PC_elements[pc][0]=='load':
                    bus = self.PC_elements[pc][2][0]
                    if bus in self.Buscoords:
                        self.dssText.Command = '? '+pc+'.kva'
                        load_size = float(self.dssText.Result)
                        self.G_loadSize[pc] = load_size
                        if load_size < 100:
                            self.small_loads.add_node(bus)
                        elif load_size < 1000:
                            self.medium_loads.add_node(bus)
                        else:
                            self.big_loads.add_node(bus)
            #Switches Graph:
            for sw in self.allSwitches:
                bus = self.PD_elements['line.'+sw][2][1]
                if self.PD_elements['line.'+sw][2][1] in self.Buscoords:
                    bus = self.PD_elements['line.'+sw][2][1]
                    self.G_switches.add_node(bus)    
                    self.G_switches_coords[bus] = self.Buscoords[bus]
                elif self.PD_elements['line.'+sw][2][0] in self.Buscoords:
                    bus = self.PD_elements['line.'+sw][2][0]
                    self.G_switches.add_node(bus)    
                    self.G_switches_coords[bus] = self.Buscoords[bus]

            #Building the protection devices graphs:
            self.cb = nx.Graph()
            self.cb_graph_coords = dict()
            self.recloser = nx.Graph()
            self.recloser_graph_coords = dict()
            self.relay = nx.Graph()
            self.relay_graph_coords = dict()
            self.fuse = nx.Graph()
            self.fuse_graph_coords = dict()
            for prot_dev in self.Protect_elements:
                switch_obj = self.Protect_elements[prot_dev][2]
                sw_bus = self.PD_elements[switch_obj][2][1]
                if prot_dev.split('.')[0]=='recloser':
                    if self.PD_elements[switch_obj][2][0]==self.subs[2][0]:
                        self.cb.add_node(sw_bus)
                        self.cb_graph_coords[sw_bus] = self.Buscoords[sw_bus]    
                    else: 
                        self.recloser.add_node(sw_bus)
                        self.recloser_graph_coords[sw_bus] = self.Buscoords[sw_bus]    
                elif prot_dev.split('.')[0]=='relay':
                    self.relay.add_node(sw_bus)
                    self.relay_graph_coords[sw_bus] = self.Buscoords[sw_bus]                   
                elif prot_dev.split('.')[0]=='fuse':
                    self.fuse.add_node(sw_bus)
                    self.fuse_graph_coords[sw_bus] = self.Buscoords[sw_bus] 
                

    def plot_graphs(self):
        #This subroutine builds and plots the complete circuit graph
        #All the buses whose coordinates are in self.Buscoords will be considered as graph nodes.
        #All PD elements whose buses are different (and whose buses  coordinates
        #are also in self.Buscoords) will be considered as edges of the graph.

        #Exit in case no Buscoords found:
        if len(self.Buscoords)==0:
            return

        #Plotting the circ graph:
        plt.close('Circuit graph')
        plt.figure('Circuit graph')
        plt.clf();
        if self.circ_graph != nx.Graph():
            #Plotting the graph:
            if self.circ_graph.number_of_nodes() < 50:
                nx.draw(self.circ_graph, pos=self.Buscoords, with_labels=True, node_color="lightblue",edge_color="gray",node_size=250);
                nx.draw_networkx_edge_labels(self.circ_graph, pos=self.Buscoords, edge_labels=self.circ_graph_edge_labels, label_pos=0.5, font_size=8, font_color='k', rotate=True);
            elif self.circ_graph.number_of_nodes() < 250:
                nx.draw(self.circ_graph, pos=self.Buscoords, with_labels=True, node_color="lightblue",edge_color="gray",node_size=50,font_size=8);
            elif self.circ_graph.number_of_nodes() < 1000:
                nx.draw(self.circ_graph, pos=self.Buscoords, node_size=10);
            else:
                nx.draw(self.circ_graph, pos=self.Buscoords, node_size=1);
        #If no coordinates were found, the graph will be plotted using the
        #default springlayout.
        else:
            #Adding all buses as nodes:
            G = nx.Graph()
            G.add_nodes_from(list(self.Bus_connect.keys()))
            all_edges_in_graph = list()
            #Adding all PD elements as edges:
            for pd in self.PD_elements:
                bus1 = self.PD_elements[pd][2][0]
                bus2 = self.PD_elements[pd][2][1:]
                for bus in bus2:
                    if bus1 != bus and bus1 != 'none' and bus != 'none' and ((bus1,bus) not in all_edges_in_graph):
                        G.add_edge(bus1,bus)
                        all_edges_in_graph.append((bus1,bus))
            #Drawing the graph:
            if G.number_of_nodes() < 50:
                nx.draw(G, with_labels=True, node_color="lightblue",edge_color="gray",node_size=250);
            elif G.number_of_nodes() < 500:
                nx.draw(G, with_labels=True, node_color="lightblue",edge_color="gray",node_size=50,font_size=8);
            else:
                nx.draw(G,node_size=1);
        #Adding the title and saving the figure:
        plt.title(self.short_filename+' circuit plot')
        plt.savefig(self.filepath+"\_"+self.short_filename+"_graph.pdf")
        plt.show()
        

    def plot_voltgraphs(self):
        #This subroutine builds and plots the voltage circuit graphs.

        #Exit in case no Buscoords found:
        if len(self.Buscoords)==0:
            return
        
        #Closing all the graphs:
        plt.close('Voltage graph')
        plt.close('HV&MV + Transformers graph')
        plt.close('HV and MV graph')
        plt.close('LV graph')
        #Setting the size of the nodes and edges width according to the number of buses:
        (node_size,width,with_labels,font_size) = self.config_graph_settings()
        #Plotting all the graphs superimposed:
        #All voltages graph:
        plt.figure('Voltage graph')
        plt.clf();
        nx.draw(self.G_HV, pos=self.G_HV_bus_coords, with_labels=with_labels, font_color="gray", font_size = font_size, node_color="green", edge_color="lighgreen", width=width*2, node_size=node_size*4, label='HV');
        nx.draw(self.G_MV, pos=self.G_MV_bus_coords, with_labels=with_labels, font_color="gray", font_size = font_size, node_color="blue", edge_color="lightblue", width=width*2, node_size=node_size*2, label='MV');
        nx.draw(self.G_LV, pos=self.G_LV_bus_coords, with_labels=with_labels, font_color="gray", font_size = font_size, node_color="black", edge_color="gray", width=width, node_size=node_size, label='LV');
        nx.draw(self.Transf_graph, pos=self.Transf_graph_coords,node_color="red", edge_color="red", width=width/2, node_size=node_size/4, label='Transformer');
        plt.title('Buses voltage distribution\n'+'HV: '+str(self.G_HV.number_of_nodes())+'MV: '+str(self.G_MV.number_of_nodes())+', LV: '+str(self.G_LV.number_of_nodes()))
        plt.legend()
        plt.savefig(self.filepath+"\_"+self.short_filename+"_Voltage_graph.pdf")
        plt.show()
        #High & Medium-voltage + transformers graph:
        plt.figure('HV&MV + Transformers graph')
        plt.clf();                
        nx.draw(self.G_HV, pos=self.G_HV_bus_coords, with_labels=with_labels, font_size = font_size, node_color="green", edge_color="lighgreen", width=width*2, node_size=node_size*4, label='HV');
        nx.draw(self.G_MV, pos=self.G_MV_bus_coords, with_labels=with_labels, font_size = font_size, node_color="blue", edge_color="lightblue", width=width*2, node_size=node_size*2, label='MV');
        nx.draw(self.Transf_graph, pos=self.Transf_graph_coords, with_labels=with_labels, font_size = font_size, node_color="red", edge_color="maroon", width=width/2, node_size=node_size/4, label='Transformer');
        plt.title('MV buses and Transformers distribution:\n'+str(self.G_MV.number_of_nodes())+' MV buses, '+str(int(self.Transf_graph.number_of_nodes()/2))+' transformers')
        plt.legend()
        plt.savefig(self.filepath+"\_"+self.short_filename+"_HV&MV&Transformers_graph.pdf")
        plt.show()
        #Closing one of the plots depending on the number of buses:
        if self.n_Buses>200 and self.G_MV.number_of_nodes()>100 and self.G_LV.number_of_nodes()>100:
            plt.close('Voltage graph')
        else:
            plt.close('HV&MV + Transformers graph')
        #Just High and Medium-voltage buses and lines:
        if self.G_MV.number_of_nodes() > 10 and self.n_Buses>100:
            plt.figure('HV and MV graph');
            plt.clf();
            nx.draw(self.G_HV, pos=self.G_HV_bus_coords, with_labels=with_labels, node_color="green", edge_color="lighgreen", width=width*2, node_size=node_size*4, label='HV');
            nx.draw(self.G_MV, pos=self.G_MV_bus_coords, with_labels=with_labels, node_color="blue", edge_color="lightblue", width=width, node_size=node_size, label='MV');
            plt.title('MV buses distribution: '+str(self.G_MV.number_of_nodes())+' buses')
            plt.legend()
            plt.savefig(self.filepath+"\_"+self.short_filename+"_HV_MV_graph.pdf")
            plt.show()
            plt.close('HV and MV graph')
        #Just low-voltage buses and lines:
        if self.G_LV.number_of_nodes() > 10 and self.n_Buses>100:
            plt.figure('LV graph');
            plt.clf();
            nx.draw(self.G_LV, pos=self.G_LV_bus_coords, with_labels=with_labels, node_color="red", edge_color="maroon", width=width, node_size=node_size, label='LV');
            plt.title('LV buses distribution: '+str(self.G_LV.number_of_nodes())+' buses')
            plt.legend()
            plt.savefig(self.filepath+"\_"+self.short_filename+"_LV_graph.pdf")
            plt.show()
            plt.close('LV graph')
    
    
    def config_graph_settings(self):            
        #This subroutine configures the main graph settings such as node_size,
        #linewidth, labels and font size depending on the number circuit size.
        
        if self.n_Buses<50:
            node_size = 20
            width = 3
            with_labels = True
            font_size = 10
        elif self.n_Buses<100:
            node_size = 8
            width = 2
            with_labels = True
            font_size = 8
        elif self.n_Buses<250:
            node_size = 7
            width = 2
            with_labels = False
            font_size = 7
        else:
            node_size = 5
            width = 1
            with_labels = False
            font_size = 6
        return(node_size,width,with_labels,font_size)
        
        
    def plot_protectgraph(self):
        #This subroutine builds and plots the circuit protection graph.

        #Exit in case no Buscoords found:
        if len(self.Buscoords)==0 or len(self.Prot_circ_graph)==0 :
            return
        
        #Closing all the graphs:
        plt.close('Protection graph')
        #Setting the size of the nodes and edges width according to the number of buses:
        (node_size,width,with_labels,font_size) = self.config_graph_settings()
        #Plotting all the graphs superimposed:
        #All voltages graph:
        plt.figure('Protection graph')
        plt.clf();
        nx.draw(self.G_subs, pos=self.G_subs_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="cyan", edge_color="cyan", width=width*2, node_size=node_size*6, label='Substation')
        nx.draw(self.G_HV, pos=self.G_HV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="purple", edge_color="purple", width=width*2, node_size=node_size*4, label='HV')
        nx.draw(self.G_MV, pos=self.G_MV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="gray", edge_color="gray", width=width, node_size=node_size*2, label='MV')
        nx.draw(self.Transf_graph, pos=self.Transf_graph_coords,node_color="red", edge_color="red", width=width/2, node_size=node_size/4, label='Transformer');
        nx.draw(self.Prot_circ_graph, pos=self.Prot_circ_graph_coords, with_labels=False, font_color="black", font_size = font_size, node_color="blue", edge_color="blue", width=width*2, node_size=node_size*4, label='Protection')
        nx.draw_networkx_edge_labels(self.Prot_circ_graph, pos=self.Prot_circ_graph_coords, edge_labels=self.Prot_circ_graph_edge_labels, label_pos=0.5, font_size = font_size, font_color='k', rotate=True)
        plt.title('Buses voltage distribution\n'+'HV: '+str(self.G_HV.number_of_nodes())+'MV: '+str(self.G_MV.number_of_nodes())+', LV: '+str(self.G_LV.number_of_nodes()))
        plt.legend()
        plt.savefig(self.filepath+"\_"+self.short_filename+"_Voltage_graph.pdf")
        plt.show()                        


    def plot_circuit_representation(self):
        #This subroutine builds and plots the circuit protection graph.

        #Exit in case no Buscoords found:
        if len(self.Buscoords)==0:
            return

        #Setting the size of the nodes and edges width according to the number of buses:
        (node_size,width,with_labels,font_size) = self.config_graph_settings()                                
        #Plotting all the graphs superimposed:
        #All voltages graph:
        plt.rcParams.update({'font.size': 16, 'figure.figsize': (9,6)})
        plt.close('cap_04_Circuit_representation')
        plt.figure('cap_04_Circuit_representation')
        nx.draw(self.G_HV, pos=self.G_HV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="gray", edge_color="gray", width=width, node_size=1/100000)
        nx.draw(self.G_MV, pos=self.G_MV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="gray", edge_color="gray", width=width, node_size=1/100000)
#        nx.draw(self.G_LV, pos=self.G_LV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="gray", edge_color="gray", width=width, node_size=1/100000)
        nx.draw(self.G_subs, pos=self.G_subs_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="purple", node_shape="s", width=width*2, node_size=node_size*15, label='Subestação')
        nx.draw(self.cb, pos=self.cb_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="cyan", width=width*2, node_size=node_size*10, node_shape='x', label='Disjuntor')
        nx.draw(self.recloser, pos=self.recloser_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="orangered", width=width*2, node_size=node_size*30, node_shape='*', label='Religador', zorder=5)
        nx.draw(self.fuse, pos=self.fuse_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="darkorange", width=width*2, node_size=node_size*10, node_shape='v', label='Fusível')
        nx.draw(self.relay, pos=self.relay_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="purple", width=width*2, node_size=node_size*10, node_shape='d', label='Relé')
        nx.draw(self.Transf_graph, pos=self.Transf_graph_coords,node_color="blue", edge_color="blue", width=width*2, node_shape="o", node_size=node_size*5, label='Transformador')
        
        plt.title('Circuit Representation')
        plt.legend(loc='lower right')
#        plt.savefig(self.filepath+"\_"+self.short_filename+"_Circuit_representation.pdf")
        plt.show()
 

    def plot_circuit_representation_lv(self):
        #This subroutine builds and plots the circuit protection graph.

        #Exit in case no Buscoords found:
        if len(self.Buscoords)==0:
            return

        #Setting the size of the nodes and edges width according to the number of buses:
        (node_size,width,with_labels,font_size) = self.config_graph_settings()     
        #Getting the min and max load values:
        min_nodemult = math.inf
        max_nodemult = -math.inf    
        all_Loads = list()
        for load in self.G_loadSize:
            nodemult = self.G_loadSize[load]
            min_nodemult = min([min_nodemult,nodemult])
            max_nodemult = max([max_nodemult,nodemult])
            all_Loads.append(nodemult)                           
        
        #Plotting all the graphs superimposed:
        #All voltages graph:
        plt.close('Circuit representation - LV')
        plt.figure('Circuit representation - LV')
        plt.clf()
        nx.draw(self.G_HV, pos=self.G_HV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="gray", edge_color="gray", width=width*2, node_size=1/100000)
        nx.draw(self.G_MV, pos=self.G_MV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="gray", edge_color="gray", width=width*2, node_size=1/100000)
        nx.draw(self.G_LV, pos=self.G_LV_bus_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="red", edge_color="red", width=width, node_size=1/100000)
        nx.draw(self.G_subs, pos=self.G_subs_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="red", node_shape="s", width=width*2, node_size=node_size*20, label='Subestação')
        #Plotting the loads with different sizes and colors by category:        
        nx.draw(self.small_loads, pos=self.Buscoords,node_color="black", node_shape="s", node_size=node_size*2, label='Carga: 0 - 100kva')
        nx.draw(self.medium_loads, pos=self.Buscoords,node_color="purple", node_shape="s", node_size=node_size*5, label='Carga: 100kva - 1M')
        nx.draw(self.big_loads, pos=self.Buscoords,node_color="cyan", node_shape="s", node_size=node_size*10, label='Carga: > 1M')
        #Plotting all the switches, protection elements and transformers:  
        nx.draw(self.G_switches, pos=self.G_switches_coords,node_color="orange", edge_color="orange", node_shape="x", node_size=node_size*2,label='Switch')
        nx.draw(self.cb, pos=self.cb_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="black", width=width*2, node_size=node_size*5, node_shape='x', label='Disjuntor')
        nx.draw(self.recloser, pos=self.recloser_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="orange", width=width*2, node_size=node_size*8, node_shape='*', label='Religador')
        nx.draw(self.fuse, pos=self.fuse_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="green", width=width*2, node_size=node_size*5, node_shape='o', label='Fusível')
        nx.draw(self.relay, pos=self.relay_graph_coords, with_labels=with_labels, font_color="black", font_size = font_size, node_color="purple", width=width*2, node_size=node_size*5, node_shape='d', label='Relé')
        nx.draw(self.Transf_graph, pos=self.Transf_graph_coords,node_color="blue", edge_color="blue", width=width*2, node_shape="o", node_size=node_size*2, label='Tranformador')
        plt.title('Circuit Representation')
        plt.legend(loc='best')
        plt.savefig(self.filepath+"\_"+self.short_filename+"_Circuit_representation.pdf")
        plt.show()
        

    def locatebus_ingraph(self,buses_to_locate=list()):
        #This subroutine builds and plots the complete circuit graph and locates
        #a specific bus given in buses_to_locate
        #All the buses whose coordinates are in self.Buscoords will be considered as graph nodes.
        #All PD elements whose buses are different (and whose buses  coordinates
        #are also in self.Buscoords) will be considered as edges of the graph.

        #Exit in case no Buscoords found:
        if len(self.Buscoords)==0:
            print('Buscoords found: 0')
            return
        
        #If no buses to locate are specified, no graph is plotted.
        if buses_to_locate!=list():
            #If there are coordinates found and the circuit graph was built:
            if len(self.Buscoords)>0 and self.circ_graph.number_of_nodes()>0:     
                #Creating the graph with the buses located:
                G_buses = nx.Graph()
                G_buses_coords = dict()
                #Adding the buses to locate in the G_buses graph:
                buses_to_locate_copy = buses_to_locate[:]
                for bus in buses_to_locate:
                    if bus in self.Buscoords.keys():
                        G_buses.add_node(bus)
                        G_buses_coords[bus] = self.Buscoords[bus]
                        buses_to_locate_copy.remove(bus) 
                if G_buses.number_of_nodes() > 0:
                    if len(G_buses) > len(self.MV_buses):
                        b_to_loc_label = False
                    else:
                        b_to_loc_label = True
                    plt.close('Buses located')
                    plt.figure('Buses located')
                    plt.clf();
                    #Plotting the graph:
                    if self.circ_graph.number_of_nodes() < 50:
                        nx.draw(self.circ_graph, pos=self.Buscoords, with_labels=True, node_color="lightblue",edge_color="gray",node_size=250,font_size=10)
                        nx.draw_networkx_edge_labels(self.circ_graph, pos=self.Buscoords, edge_labels=self.circ_graph_edge_labels, label_pos=0.5, font_size=8, font_color='k', rotate=True)
                        nx.draw(G_buses, pos=self.Buscoords, with_labels=b_to_loc_label, node_color="red",node_size=250,font_size=10)
                    elif self.circ_graph.number_of_nodes() < 250:
                        nx.draw(self.circ_graph, pos=self.Buscoords, with_labels=True, node_color="lightblue",edge_color="gray",node_size=50,font_size=8)
                        nx.draw(G_buses, pos=self.Buscoords, with_labels=b_to_loc_label, node_color="red",node_size=50,font_size=8)
                    elif self.circ_graph.number_of_nodes() < 1000:
                        nx.draw(self.circ_graph, pos=self.Buscoords, with_labels=False, node_color="blue",edge_color="gray", node_size=10)
                        nx.draw(G_buses, pos=self.Buscoords, with_labels=b_to_loc_label, node_color="red",node_size=15,font_size=7)
                    else:
                        nx.draw(self.circ_graph, pos=self.Buscoords, with_labels=False, node_color="blue",edge_color="gray", node_size=1)
                        nx.draw(G_buses, pos=self.Buscoords, with_labels=b_to_loc_label, node_color="red",node_size=5,font_size=6)
                    #In case not all the buses were located:
                    if len(buses_to_locate_copy)>0:
                        print('\nThese buses were not located in the graph:')
                        for bus in buses_to_locate_copy:
                            print(bus)
                    else:
                        print('\nAll buses were located!') 
                else:
                    print('\nNone of the buses were located!')
            else:
                print('\nThere are no Bus coords specified for this graph!')
        else: 
            print('\nNo buses to locate were specified!')


###############################################################################
#Voltage and currrent profile methods:
###############################################################################  

    def plot_vprofile(self,mode=1,the_title=''):
        # This subroutine plots a graph of the circuit voltage profile in
        # all nodes in each bus at the current condition.
        # If mode==1 the image created will be saved as a file
        # If mode!=1 the image will be plotted in the console and not saved.
        
        #Closing all figures:
        if mode==0:
            plt.close('all')
        #Getting all the voltage values:
        [VA_,VB_,VC_] = self.get_allvbus()      
        #max. voltage:
        zmax = max([max(VA_),max(VB_),max(VC_)])
        #Creating the X-axis ticks:
        X_axis_ticks = ['' for x in range(self.n_Buses)]
        for i,bus in enumerate(self.allBuses):
            self.dssCircuit.SetActiveBus(bus)
            X_axis_ticks[i] = bus + "\n("+str(len(self.dssBus.Nodes))+")"
        #Calculating how many figures will be plotted in order to plot a max
        #amount of 10 buses per plot and trying to plot the same number of buses
        #voltages in all figures.
        if self.n_Buses<= 10:
            nplots = 1
            n_figs_by_plot = self.n_Buses
        else: 
            nplots = int(self.n_Buses/10) + 1
            n_figs_by_plot = int(self.n_Buses/nplots) + 1
        #Initializing the markers:
        init_marker = 0
        end_marker = n_figs_by_plot-1
        if end_marker > self.n_Buses-1:
            end_marker = self.n_Buses-1
        for i in range(nplots):
            #N is the number of buses in each plot:
            N = end_marker - init_marker + 1
            #print(N)
            #Plotting the bars:
            ind = np.arange(N)  # the x locations for the groups
            width = 0.2      # the width of the bars
            fig, ax = plt.subplots()
            rects1 = ax.bar(ind +(1/2)*width, VA_[init_marker:end_marker+1], width, color='r')
            rects2 = ax.bar(ind +(3/2)*width, VB_[init_marker:end_marker+1], width, color='b')
            rects3 = ax.bar(ind +(5/2)*width, VC_[init_marker:end_marker+1], width, color='g')
            ax.set_ylabel('Voltage [pu]')
            ax.set_xlabel('Buses (n° of phases)')
            if the_title == '':
                ax.set_title('Voltage profile - 0'+str(i+1))
            else:
                ax.set_title(the_title)
            ax.set_yticks(np.arange(0,1.5,0.1))
            ax.set_xticks(ind + 1.5*width)
            ax.set_xticklabels(X_axis_ticks[init_marker:end_marker+1],rotation=-90,ha='center')
            #ax.legend((rects1[0], rects2[0],rects3[0]), ('VA', 'VB','VC'),loc='upper center', bbox_to_anchor=(0.5, -0.19),fancybox=True, shadow=True, ncol=3)
            ax.legend((rects1[0], rects2[0],rects3[0]), ('VA', 'VB','VC'),loc='center left', bbox_to_anchor=(1, 0.5));
            #Plotting the limits reference lines:
            plt.plot([-0.5,N], [0.90, 0.90], "k")
            plt.plot([-0.5,N], [1.10, 1.10], "k")
            #Limits of the plot:
            plt.ylim([0,max(zmax,1.11)])
            plt.xlim([-0.5,N])
            plt.grid(True)
            if mode==1:
                path_pref_condition = self.filepath + '\__' + 'vprofile_'+ self.short_filename
                #Creating the pre_fault_condition folder in case it does not exist
                if not os.path.exists(path_pref_condition):
                    os.makedirs(path_pref_condition)
                img_name = path_pref_condition+'\_'+self.short_filename+'_vprofile_00'+str(i+1)+'.png'
                plt.savefig(img_name,bbox_inches='tight')
                plt.close()
            else:
                plt.show()
            #Updating the markers:
            init_marker+=n_figs_by_plot
            end_marker+=n_figs_by_plot
            if end_marker > self.n_Buses-1:
                end_marker = self.n_Buses-1
        if mode==1:
            print('\nVoltage profile image saved.')


    def plot_avg_voltbydist(self):
        # This subroutine plots a graph of the circuit voltage profile in all
        # buses at the current condition by the distance from the substation.
        
        # Getting all the voltage values:
        [VA,VB,VC] = self.get_allvbus()
        # max. voltage:
        Vmax = max([max(VA),max(VB),max(VC)])
        dist_max = max(self.bus_dist2subs.values())
        Avg_voltvals = list()
        bus_dist = list()
        for i in range(self.n_Buses):
            the_bus = self.allBuses[i]
            n_values = 0
            if VA[i] != 0:
                n_values+=1
            if VB[i] != 0:
                n_values+=1
            if VC[i] != 0:
                n_values+=1
            if n_values > 0:
                mean = (VA[i]+VB[i]+VC[i])/n_values
                Avg_voltvals.append(mean)
                bus_dist.append(self.bus_dist2subs[the_bus])
        #Plotting the graph:
        plt.close('Voltage by distance')    
        plt.figure('Voltage by distance')    
        plt.clf()
#        plt.plot([-0.5,1.1*math.ceil(max(bus_dist))], [0.90, 0.90], "k")
#        plt.plot([-0.5,1.1*math.ceil(max(bus_dist))], [1.10, 1.10], "k")
#        plt.plot(bus_dist,Avg_voltvals,'bo')
        plt.scatter(bus_dist,Avg_voltvals,color='b',facecolor='None',marker='o',s=10)  
        plt.title('Buses voltage by distance from substation')
        plt.xlabel('Distance (km)')
        plt.ylabel('Voltage (pu)')
        if max(bus_dist)>1:
            plt.xlim([-0.001,math.ceil(dist_max)*1.05])
        else:
            print(max(bus_dist),math.ceil(max(bus_dist)*10)/10)
            plt.xlim([-0.001,math.ceil(max(bus_dist)*10)/10])
#        if Vmax < 1.15:
#            plt.ylim([0.85,1.15])
#        else:
#            plt.ylim([0.85,Vmax])
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        
        
    def plot_voltbydist_byphase(self,title=''):
        # This subroutine plots a graph of the circuit voltage profile in all
        # buses at the current condition by the distance from the substation.
        
        if title == '':
            title = 'Voltage by distance by phase'
        else: 
            title = 'Voltage by distance by phase - ' + title
        #Getting all the voltage values:
        [VA,VB,VC] = self.get_allvbus()
        #max. voltage:
        Vmax = max([max(VA),max(VB),max(VC)])
        dist_max = max(self.bus_dist2subs.values())
        VA_ = list()
        VB_ = list()
        VC_ = list()
        bus_dist_A = list()
        bus_dist_B = list()
        bus_dist_C = list()
        for i in range(self.n_Buses):
            the_bus = self.allBuses[i]
            if VA[i] != 0:
                bus_dist_A.append(self.bus_dist2subs[the_bus])
                VA_.append(VA[i])
            if VB[i] != 0:
                bus_dist_B.append(self.bus_dist2subs[the_bus])
                VB_.append(VB[i])
            if VC[i] != 0:
                bus_dist_C.append(self.bus_dist2subs[the_bus])
                VC_.append(VC[i])
                
        #Plotting the graph:
        plt.close(title)    
        plt.figure(title)    
        plt.clf() 
#        plt.plot([-0.5,1.1*math.ceil(dist_max)], [0.90, 0.90], "k")
#        plt.plot([-0.5,1.1*math.ceil(dist_max)], [1.10, 1.10], "k")
        plt.scatter(bus_dist_A,VA_,color='b',marker='o',facecolor='None',s=10,label='VA')  
        plt.scatter(bus_dist_B,VB_,color='r',marker='s',facecolor='None',s=10,label='VB')  
        plt.scatter(bus_dist_C,VC_,color='g',marker='D',facecolor='None',s=10,label='VC') 
        plt.title('Buses voltage by distance from substation')
        plt.xlabel('Distance (km)')
        plt.ylabel('Voltage (pu)')
        if dist_max>1:
            plt.xlim([-0.001,math.ceil(dist_max)*1.05])
        else:
            print(dist_max,math.ceil(dist_max*10)/10)
            plt.xlim([-0.001,math.ceil(dist_max*10)/10])
#        if Vmax < 1.15:
#            plt.ylim([0.85,1.15])
#        else:
#            plt.ylim([0.85,Vmax])
        plt.legend(loc='lower right')
        plt.grid(True)
        plt.tight_layout()
        plt.show()
            

    def get_allvbus(self):
        #This subroutine gets the voltages in all nodes of the circuit:
        #In case one phase is not defined for a specific bus, the voltage returned
        #for that phase will be zero.

        #Creating the lists that will contain all voltage values by phase:
        VA_ = [0 for x in range(self.n_Buses)]
        VB_ = [0 for x in range(self.n_Buses)]
        VC_ = [0 for x in range(self.n_Buses)]
        #Getting the voltage value by node in each bus:
        for i in range(self.n_Buses):
            #Setting the active bus:
            active_bus = self.allBuses[i]
            self.dssCircuit.SetActiveBus(active_bus)
            for j in range(len(self.dssBus.Nodes)):
                active_node = self.dssBus.Nodes[j]
                #VA_:
                if active_node==1:
                    VA_[i] = round(self.dssBus.VMagAngle[2*j]/(self.bus_kvbases[active_bus]*1000),6)
                #VB_:
                elif active_node==2:
                    VB_[i] = round(self.dssBus.VMagAngle[2*j]/(self.bus_kvbases[active_bus]*1000),6)
                #VC_:  
                elif active_node==3:
                    VC_[i] = round(self.dssBus.VMagAngle[2*j]/(self.bus_kvbases[active_bus]*1000),6)
        return [VA_,VB_,VC_]


    def get_minvbus(self,buses_selected=list()):
        # This subroutine gets the minimum voltage in each bus and returns them as a dict.

        #If no list of buses were given, all buses will be considered
        if buses_selected==list():
            buses_selected=self.allBuses
            
        #Creating the dictionay that will contain the  min voltage values in each bus:
        VABC_min = dict()
        #self.dssText.Command = "show voltages ln nodes"
        #Getting the voltage values by node in each bus:
        for bus in buses_selected:
            #Setting the active bus:
            self.dssCircuit.SetActiveBus(bus)
            VABC = list()
            for j in range(len(self.dssBus.Nodes)):
                active_node = self.dssBus.Nodes[j]
                if active_node in [1,2,3] and math.isnan(self.dssBus.VMagAngle[2*j]) == False and self.dssBus.VMagAngle[2*j] > 0:
                    VABC.append(self.dssBus.VMagAngle[2*j])
            if len(VABC)>0:
                VABC_min[bus] = round(min(VABC)/(self.bus_kvbases[bus]*1000),9)
            else: 
                #If something is very weird, say that the bus has 1 pu, this way
                #it won't cause any harm. Also pray for it not to happen.
                VABC_min[bus] = 1 
                print('\nWarning: Bus with len(VABC_min)==0!')
                print(bus,self.dssBus.VMagAngle)
        return VABC_min
 
    
    def get_vbus(self,the_bus):
        #This subroutine gets the voltages in all nodes for a specific bus.

        #Creating the list that will contain all voltage values by phase:
        V_bus = dict()
        for ph in ['A','B','C']:
            V_bus['V'+ph] = 0
        #Getting the voltage value by node in each bus:
        for bus in self.allBuses:
            if bus == the_bus:
                #Setting the active bus:
                self.dssCircuit.SetActiveBus(bus)
                for j in range(len(self.dssBus.Nodes)):
                    active_node = self.dssBus.Nodes[j]
                    #VA_:
                    if active_node==1:
                        V_bus['VA'] = round(self.dssBus.VMagAngle[2*j]/(self.bus_kvbases[bus]*1000),6)
                    #VB_:
                    elif active_node==2:
                        V_bus['VB'] = round(self.dssBus.VMagAngle[2*j]/(self.bus_kvbases[bus]*1000),6)
                    #VC_:  
                    elif active_node==3:
                        V_bus['VC'] = round(self.dssBus.VMagAngle[2*j]/(self.bus_kvbases[bus]*1000),6)
        return V_bus
    

    def get_currents(self,ckt_element):
        #This subroutine gets the current values in all phases of the circuit 
        #element first terminal.

        #Setting the active ckt element:
        self.dssCircuit.SetActiveElement(ckt_element)        
        currents = list()
        for i in range(int(len(self.dssCktElement.CurrentsMagAng)/2)):
            if i%2==0:
                currents.append(self.dssCktElement.CurrentsMagAng[i])
        return currents


    def get_ICCcurrent(self,ckt_element):
        #This subroutine gets the current ICC value in the given circuit element.
        #The ICC current given will be the one with the greatest value in all
        #phases and in both terminals.
        
        #Setting the active ckt element:
        self.dssCircuit.SetActiveElement(ckt_element)        
        currents = list()
        for i in range(len(self.dssCktElement.CurrentsMagAng)):
            if i%2==0:
                currents.append(self.dssCktElement.CurrentsMagAng[i])
        return max(currents)


#_______________________________________________________________________________

