#!/usr/bin/python

import sys, getopt
import copy
import json
from cmsis_svd.parser import SVDParser
from random import *
from os.path import exists

funcs = {} 		# This is the PDG
data ={}		# This gives which data is used by which function
cfg = {} 		# This remains the CFG
compartments=[] # This gives the different compartments in the system
compartmentMap={} # This gives the function to compartment map
policy = "file" # Select policy, possible values: device, color, file, component, thread


def newCompartment():
		global compartments
		compartment = []
		compartments.append(compartment)
		return compartment

def deleteEmptyCompartment(comp):
		global compartments
		if len(comp) != 0:
			print("Wrong way of calling function")
			exit()
		compartments.remove(comp)
		

def addToCompartment(func, compartment):
		global compartmentMap
		global compartments
		if func in compartmentMap:
			oldCompartment = compartmentMap[func]
			compartmentMap[func] = compartment
			compartment.append(func)
			oldCompartment.remove(func)
			if len(oldCompartment) == 0:
				compartments.remove(oldCompartment)
		else:
			compartment.append(func)
			compartmentMap[func] = compartment

def resetPartitions():
	global compartments
	global compartmentMap
	compartments= [] # This gives the different compartments in the system
	compartmentMap= {}


def getSVDHandle(oem,model):
	return SVDParser.for_packaged_svd(oem, model).get_device().peripherals

def getDevice(addr, peripherals):
	addr = int(addr, 16)
	# Make sure this is a device, this is a possible circumvent around the enforced protections
	# a malicious program can hardcode to other compartment's memory, make sure we don't allow it
	if not (addr>= 0x40000000 and addr <=0x60000000):
		#print("Private region or protected region used:" + hex(addr))
		return None, 0, 0
	for peripheral in peripherals:
		if  peripheral._address_block is not None:
			if ((addr >= peripheral.base_address) and (addr < (peripheral.base_address + peripheral._address_block.size))):
				return peripheral, peripheral.base_address, peripheral._address_block.size
		elif peripheral.get_derived_from():
			derivedFrom = peripheral.get_derived_from()
			if derivedFrom._address_block is not None:
				if ((addr >= peripheral.base_address) and (addr < (peripheral.base_address + derivedFrom._address_block.size))):
						return peripheral, peripheral.base_address, derivedFrom._address_block.size
		elif peripheral.size is not None:
		  	if ((addr >= peripheral.base_address) and (addr < (peripheral.base_address + peripheral.size))):
				return peripheral, peripheral.base_address, peripheral.size

	print("Device not found:" + hex(addr))
	return None, 0, 0
	
def mergeComponentsExcept(tCompartments):
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	comp = newCompartment()
	objlist =[]
	for compartment in list(compartments):
		if compartment not in tCompartments:
			for obj in list(compartment):
				addToCompartment(obj, comp)

#Merge compartments, but really we move all compartments from compartment2 to compartmen1
def mergeCompartments(compartment1, compartment2):
	for fun in list(compartment2):
		addToCompartment(fun, compartment1)
	
def assignLooseFunctions(): 
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	compartment = newCompartment()	
	for func in funcs:
		if func not in compartmentMap:
			addToCompartment(func, compartment)
		for obj in funcs[func]:
			if obj not in compartmentMap:
				addToCompartment(obj, compartment)
	
def threadComp(threads):
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	#Create thread compartments if haven't done already
	for thread in threads:
		if thread not in compartmentMap:
			compartment = newCompartment()
			addToCompartment(thread, compartment)
#for obj in funcs[thread]:
#				addToCompartment(obj, compartment)

# If for a PDG edge different nodes have different colors
# make a new compartment that is the superset of all small colors
# .
def paint():
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	for func in funcs:
		colors=[]
		if func in compartmentMap:
			colors.append(compartmentMap[func])
		for obj in funcs[func]:
			if obj in compartmentMap:
				if compartmentMap[obj] not in colors:
					colors.append(compartmentMap[obj])
			else:
				#If an object in PDG has not been seen before we can safely put it in any of the color.
				if len(colors) > 0:
					compartment = colors[0]
					addToCompartment(obj, compartment)
					

		if len(colors)>1:
#		print("Different colors: ")
#print colors
		#Repaint
#print("Different Compartments before in the colored compart:")
#		print(colors)
			cPolicy = "submerge" #while painting cherry pick the minimum set of objects for consistent coloring
			if cPolicy == "cherrypick":
				compartment = []
				for color in colors:
					for obj in color:
						if "main" in obj:
							print(color)
						oldCompartment = compartmentMap[obj]
						compartmentMap[obj] = compartment
						compartment.append(obj)
						oldCompartment.remove(obj)
						if len(oldCompartment) == 0:
							compartments.remove(oldCompartment)
				compartments.append(compartment)
			elif cPolicy == "submerge":
				compartment = []
				for color in colors:
					oldCompartment = color
					for obj in color: 
						compartmentMap[obj] = compartment
						compartment.append(obj)
					compartments.remove(oldCompartment)
				compartments.append(compartment)

#Increase compartments size but not take any object from other compartments
def expandComponentsX(tCompartments):
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	for comp in tCompartments:
		print comp
		for obj in comp:
			if obj in funcs:
				for ptsTo in funcs[obj]:
					if ptsTo in compartmentMap:
						if compartmentMap[ptsTo] in tCompartments:
							continue
						else: 
							addToCompartment(ptsTo,comp)
					else:
						addToCompartment(ptsTo,comp)
			elif obj in data:
					for user in data[obj]:
						if user in compartmentMap:
							if compartmentMap[user] in tCompartments:
								continue
							else:
								addToCompartment(user,comp)
						else:
							addToCompartment(user,comp)
	

# If all the nodes in PDG that are connected are not of same color
# spread the color. That is increase the size of the compartment.
def spreadPaint():
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	compartment=[]
	for func in funcs:
		if func not in compartmentMap:
#print("There was funcs not in compartments")
			for val in funcs[func]:
				if val in compartmentMap:
					#At this point all compartments must be same in the pointed thing
					compartment=compartmentMap[val]
					break;
			addToCompartment(func, compartment)
			for val in funcs[func]:
				if val not in compartmentMap:
					compartment.append(val)
					compartmentMap[val] = compartment

def printStats():
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	global policy
	print("**********Printing stats******")
	objCount =0
	for func in funcs:
		objCount +=1
	funcount = objCount
	print("Total Functions: "+ str(objCount))
	for var in data:
		objCount +=1
	print("Total Variables: " + str(objCount - funcount))
	print("Total Objects:" +str(objCount))
	printLooseFunctions()
	printCompartments =False
	j = len(compartments)
	original_stdout = sys.stdout
	with open(policy+"_policy", 'w') as f:
			sys.stdout = f
			for compartment in compartments:
				print(compartment)
			sys.stdout = original_stdout

	with open(".policy", 'w') as f:
			sys.stdout = f
			for compartment in compartments:
				print(compartment)
			sys.stdout = original_stdout

	if printCompartments:
		for compartment in compartments:
			print(compartment)
	coloredObj =0
	for compartment in compartments:
		coloredObj += len(compartment)
	

	print("Compartments:" +str(j))
	print("Loose Functions:" + str(objCount - coloredObj))


def printLooseFunctions():
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	printLoseObjects = True
	print("Now we print Loose objects")
	if printLoseObjects:
		for func in funcs:
			if func not in compartmentMap:
				print("**********Lost Function ***********")
				print func
		for var in data:
			if var not in compartmentMap:
				print("************Lost Object ***********")
				print var
				print(data[var])
	print("End of loose objects")
ffmap = {} #Function file map
datafmap = {} #Data to file map
files = {} # Files map
fdmap = {} # Function to data map?
dfmap = {} # Device to function map?
dfmapCoarse = {} # Devices used by the firmare but mapped to a 4K boundary to function map but coursed?
import os
def compCheck():
	print("*******COMPCHECKSTART********")
	for comp in compartments:
		if "z_rb_walk" in comp:
			print comp
	print("*******COMPCHECKEND********")

def main(argv):
	cfg = ''
	dfg = ''
	global funcs
	global data
	global PDG
	global compartments
	global compartmentMap
	global policy 
	try:
		opts, args = getopt.getopt(argv,"hc:d:p:",["cfile=","dfile=","partConfig="])
	except getopt.GetoptError:
		print 'test.py -i <inputfile> -o <outputfile>'
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print 'test.py -i <inputfile> -o <outputfile>'
			sys.exit()
		elif opt in ("-c", "--cfile"):
			bc = arg
		elif opt in ("-d", "--dfile"):
			dfg = arg

	#See if partition cache available

	if (exists("./.policy")):
		print("HELLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLOOOOOOOOOOOOOOOOOOOOOOOO")
		return
	
	cfg = "./cg"
	cmd = "opt  --print-callgraph " + bc +" 2> cg"
	os.system(cmd)

	
	ffmapFile = "./ffmap"
	with open(ffmapFile) as f:
		lines = f.readlines()
		for line in lines:
			line = line.replace("\n","")
			[func, fileN] = line.split("##")
			ffmap[func] = fileN
	datafmapFile = "./dfmap"
	with open(datafmapFile) as f:
		lines = f.readlines()
		for line in lines:
			line = line.replace("\n","")
			[func, fileN] = line.split("##")
			datafmap[func] = fileN

	for func in ffmap:
		if ffmap[func] not in files:
			files[ffmap[func]] = []
		files[ffmap[func]].append(func)

	for obj_elem in datafmap:
		if datafmap[obj_elem] not in files:
			print(datafmap[obj_elem] +"is a data only file")
			files[datafmap[obj_elem]] = [] 

	fdmapFile = "./fdmap"
	with open(fdmapFile) as f:
		lines = f.readlines()
		for line in lines:
			line = line.replace("\n", "")
			[func,dev] = line.split("##")
			if func in fdmap:
				fdmap[func].append(dev)
			else:
				fdmap[func] =[dev]

#dfmap = {v: k for k, v in fdmap.items()} #Only works for 1-1
	
	for f in fdmap:
		for addr in fdmap[f]:
			if addr in dfmap:
				if f not in dfmap[addr]:
					dfmap[addr].append(f)
			else:
				dfmap[addr] = [f]
	#Test this map later

	for addr in dfmap:
		base = int(addr, 0) & 0xFFFFF000
		if base in dfmapCoarse:
			dfmapCoarse[base] = dfmapCoarse[base]  + dfmap[addr]
		else:
			dfmapCoarse[base] = dfmap[addr]


	curr = "null"
	funcs[curr] = []
	with open(cfg) as f:
		lines = f.readlines()

		for line in lines:
#print(line)
			if ("Call graph node for function:" in line):
				curr = line.split('\'')[1]
				funcs[curr] = []
			if("calls function " in line):
				if (len(line.split('\'')) == 3):
					if line.split('\'')[1] not in funcs[curr]:
						funcs[curr].append(line.split('\'')[1])

	funcs.pop("null", None)

	#At this point we have the CFG, since we use the ADT move the CFG to cfg
	cfg = funcs
#for func in funcs:
#print(func + "  calls: ") 
#print(funcs[func])
	#Let's get the DDG 
	with open(dfg) as f:
		lines = f.readlines()
		consume =1
		for line in lines:
			line = line.replace("\n","")
#print(line)
			if consume ==1:
				obj = line
				data[obj] = []
				consume =0
				continue
			if("***" in line):
				consume=1
				obj = ""
			if obj:
				if ("Used By:" in line):
					continue
				data[obj].append(line)
	
	#Let's get the DDG from our graph. 
	for d in data:
		for fun in data[d]:
			if fun not in funcs:
				funcs[fun] = []
	for func in funcs: 
		for obj in data:
			if func in data[obj]:
				funcs[func].append(obj)

	for func in ffmap:
		if func not in funcs:
			funcs[func] = []
	


	objCount =0
	for func in funcs:
		objCount +=1
	for var in data:
		objCount +=1
	print("Total Objects:" +str(objCount))

#	for obj in data:
#		print(obj) 
#		print("touches")
#		print(data[obj])
	
#	for func in funcs:
#		print(func + "  calls or touches: ")
#		print(funcs[func])

	######################
	#Find the leaves in the function and data 
	leaves = []
	for func in funcs:
		if (len(funcs[func]) ==0):
			leaves.append(func)
	for obj in data: 
		if (len(data[obj]) == 1):
			leaves.append(data[obj][0])
	i =0
	for func in funcs:
		if func not in leaves:
			i += 1
		for val in funcs[func]:
			if val not in leaves:
				i+=1

#print(func + "  calls or touches: ")
#print(funcs[func])
	print("Leaf Compartments:" +str(len(leaves)))
	print("Loose Functions:" + str(objCount - len(leaves)))

	##############################
	# Initialize compartments with dominator nodes - Leaf with dominator nodes
	for leaf in leaves:
		compartment = newCompartment()
		addToCompartment(leaf, compartment)
	
	for func in funcs:
#print(len(funcs[func]))
#		if len(funcs[func]) ==1:
#print(funcs[func][0])
#			print(funcs[func][0] in leaves)
#			print(funcs[func][0] in compartmentMap)
		if len(funcs[func]) ==1 and funcs[func][0] in leaves:
			for compartment in compartments:
				if(funcs[func] in compartment):
						compartment.append(funcs[func])
						compartmentMap[funcs[func]] = compartment
	print("After dominator merge")

	###################
	# Pair-Merge
	for func in funcs:
		iter =0
		if func not in compartmentMap:
			for val in funcs[func]:
				if val in compartmentMap:
					break;
				iter+=1
			if iter==len(funcs[func]):
				compartment = newCompartment()
				addToCompartment(func, compartment)
				for val in funcs[func]:
					addToCompartment(val, compartment)

				
	print("After Pair merge")
	FreeRTOSComp = ["Task", "Queue", "Stream", "Semaphore", "Timer", "Event", "Port"]
	ZephyrComp = ["audio_codec_", "dmic_", "i2s_", 
	"sys_notify_",
	"bt_", 
	"cipher_",
	"device_",
	"display_",
	"edac_",
	"fs_",
	"k_thread_",
	"k_work_", 
	"irq_",
	"k_poll_",
	"k_sem_",
	"k_mutex_",
	"k_condvar_",
	"k_event_",
	"k_queue_",
	"k_fifo_",
	"k_lifo_",
	"k_stack_",
	"k_msgq_",
	"k_mbox_",
	"k_pipe_",
	"k_heap_",
	"k_mem_slab_",
	"k_timer_",
	"log_",
	"k_mem_",
	"shared_multi_",
	"modbus_",
	"dns_",
	"sntp_",
	"net_trickle_",
	"net_",
	"adc_",
	"counter_",
	"clock_",
	"dac_",
	"dma_",
	"ec_",
	"dma_",
	"eeprom_",
	"entropy_",
	"flash_",
	"gna_",
	"gpio_",
	"hwinfo_",
	"i2c_",
	"ipm_",
	"kscan_",
	"led_",
	"mbox_",
	"pinmux_",
	"pwm_",
	"ps2_",
	"peci_",
	"regulator_",
	"maxim_ds3231_",
	"sensor_",
	"spi_",
	"uart_",
	"mdio_",
	"wdt_",
	"video_",
	"espi_",
	"usb_",
	"shell_",
	"nvs_",
	"stream_flash_",
	"flash_",
	"fcb_"
	]
#k_ prequel for threading

	threads = ["prvQueueReceiveTask", "prvQueueSendTask"]

	#For Zephyr
	threads = "./threads"
	with open(threads) as f:
		threads = f.readlines()
	i =0
	for thread in threads:
		threads[i] = thread.replace("\n","")
		i +=1


	if policy == "color":
		paint()
		spreadPaint()
		# In coloring we usually generate a lot of compartments which usually don't fit in memory
		# because of alignment requirements. Therefore we need to constraint the number of compartments.	
		while len(compartments) > 1:
			mergeCompartments(compartments[0], compartments[1])
	elif policy == "thread":
		threadComp(threads)
		tCompartments = []
		for thread in threads:
			tCompartments.append(compartmentMap[thread])
		expandComponentsX(tCompartments)
		assignLooseFunctions()
		mergeComponentsExcept(tCompartments)
#expandComponentsX(tCompartments)

	elif policy == "component":
		dexpert = FreeRTOSComp
		if not len(dexpert) == 0:
			cCompartments = []
			for fcomp in dexpert:
				comp =  newCompartment()
				
				for func in funcs:
					if fcomp in func:
						addToCompartment(func, comp)
				if len(comp) == 0:
					compartments.remove(comp)
				else:
					cCompartments.append(comp)
			
			expandComponentsX(cCompartments)
			assignLooseFunctions()
			mergeComponentsExcept(cCompartments)
				
		else:
			for f in files:
				comp = newCompartment()
				for func in files[f]:
					addToCompartment(func, comp)
					if func in funcs:
						for obj in funcs[func]:
							addToCompartment(obj, comp)
	elif policy == "file":
		for f in files:
			comp = newCompartment()
			for func in files[f]:
				addToCompartment(func, comp)
				if func in funcs:
					for obj in funcs[func]:
						if obj not in ffmap:
							addToCompartment(obj, comp)
						elif ffmap[obj] == ffmap[func]:
							addToCompartment(obj, comp)
			#For case where files don't have any functions
			if len(comp) == 0:
				deleteEmptyCompartment(comp)

		with open("raw_policy", 'w') as f:
			sys.stdout = f
			for f in files:
				print(f)
			sys.stdout = original_stdout

				
	
	elif policy == "device":
#		for f in files:
#			comp = newCompartment()
#			for func in files[f]:
#				addToCompartment(func, comp)
#				if func in funcs:
#					for obj in funcs[func]:
#						addToCompartment(obj, comp)
#				else:
#					print (func +"not found in anything")
		devices = []
		svdfmap = {} #Map SVD tuples to devices
		handle = getSVDHandle("STMicro", "STM32F46_79x.svd")
		resetPartitions()
		print ("Initial Compartments count: " + str(len(compartments)))
#		device policy needs a clean state
		for d in dfmap:
			print dfmap[d]
		for addr in dfmap:
			dev,base,size = getDevice(addr, handle)
			if dev is None:
				name = "unkown"
			else:
				name = dev.name
			if (name,base,size) not in devices:
				devices.append((dev,base,size))
			if (name,base,size) in svdfmap:
				for f in dfmap[addr]:
					if f not in svdfmap[(name,base,size)]:
						svdfmap[(name,base,size)].append(f)
			else:
				svdfmap[(name,base,size)] = []
				for f in dfmap[addr]:
					svdfmap[(name,base,size)].append(f)

		printDevUsage = False
		if printDevUsage:
			for dev,base,size in svdfmap:
				if dev is "unkown":
					continue
				print dev + " used by:"
				for fun in svdfmap[(dev,base,size)]:
				 	print "	" + str(fun)
		i =0
		for dev,base,size in svdfmap:
			print dev
			i = i+1

		print str(i) + " devices found"


		# For each device create a compartment
		# if a user already in a compartment merge them
		# Assign loose functions, i think we do it later anywas
		print(svdfmap)
		for dev,base,size in svdfmap:
			#print ("Compartments count: " + str(len(compartments)))
			if dev == "unkown":
				print("-_-")
				#continue
			#Give a compartment to every function that doesn't have a compartment
			comp = newCompartment() #New compartment for the device 
#print comp
			allcomps=[comp]
			for fun in svdfmap[(dev,base,size)]:
				if fun not in compartmentMap:
					addToCompartment(fun, comp)
					for obj in funcs[fun]:
						addToCompartment(obj, comp)
			if len(comp) == 0:
				#All current users are in compartments
				print (dev + "all users alreaedy in compartments")
				deleteEmptyCompartment(comp)

			#merge compartment if one device users are in different compartments
			# if len(allcomps) > 1:
				#print ("Merging compartments")
				#bigcomp = newCompartment()
#for comp in allcomps:
#					mergeCompartments(bigcomp, comp)


		print "There are "+ str(len(compartments)) + " compartments before merging"
		#If this option is enabled it will place all the objects and functions in the same driver 
		#in the same compartment before random merging

		#print(compartments)
		optionalDeviceDriverMerge = True
		if optionalDeviceDriverMerge:
			for comp in list(compartments):
				for func in list(comp):				
					#Get the file this function is in
					if func not in ffmap and func not in datafmap:
						print func + "not in funfileMap"
						continue
					if func in ffmap:
						fil =  ffmap[func]
					else:
						fil = datafmap[func]
					for drivFunc in files[fil]:
						#if drivFunc not in compartmentMap:
						addToCompartment(drivFunc, comp)



#		for dev in dfmapCoarse:
#			compartment = compartmentMap[dfmapCoarse[dev][0]]
#			for funcL in dfmapCoarse[dev]:
#				if compartment != compartmentMap[funcL]:
#					mergeCompartments(compartment, compartmentMap[funcL])

	print "There are "+ str(len(compartments)) + " compartments after merging"
	#Assign Objects in unsed compartment
	unusedComp = newCompartment()
	for func in funcs:
			if func not in compartmentMap:
				addToCompartment(func, unusedComp)
				
	for var in data:
		if var not in compartmentMap:
			addToCompartment(var, unusedComp)

#	print("***************************************")
#	print("***************************************")
#	print("*************after additions**********")
#	print("***************************************")
#	print("***************************************")
#print(unusedComp)

	for comp in list(compartments):
		if len(comp) ==0:
			deleteEmptyCompartment(comp)

	# Merge compartments that may share data 
	Merge = True
	while(Merge):
		Merge =  False 
		for var in data:
			users = []
			users = compartmentMap[func]
			compartment = None
			#Check for all users of this data
			ogFunc = None
			for func in data[var]:
			#Is this the first user compartment?
				if ogFunc is None:
					#Make this the big compartment, everything will be merged into it.
					ogFunc = func
				if compartmentMap[ogFunc] != compartmentMap[func]:
					#mergeCompartments(compartment, compartmentMap[func])
					print "For data:" + var
					print func
					print ogFunc
					mergeCompartments(compartmentMap[ogFunc], compartmentMap[func])
					Merge = True 		

	for var in data:
		users = []
		users = compartmentMap[func]
		compartment = []
		ogFunc = None
		for func in data[var]:
			if ogFunc is None:
				ogFunc = func 
			if compartmentMap[ogFunc] != compartmentMap[func]:
					print "******************************"
					print "*********BUG ON***************"
					print "******************************"
					print "For data:" + var
					print ogFunc
					print func
					#print compartment  
#				   print compartmentMap[func]
					#mergeCompartments(compartment, compartmentMap[func])
					#compartment = compartmentMap[func]



	debugDev = False
	## Ensure that each compartment has access to its compartment devices
	## We dump this file in rtmk.dev so that configdata generator can fill this up
	rtdev = open("rtmk.dev", "w")
	svdmap = {}
	handle = getSVDHandle("STMicro", "STM32F46_79x.svd")
	for fun in funcs:
		if fun in fdmap:
			for addr in fdmap[fun]:
				periph,base,size = getDevice(addr, handle);
				if fun not in svdmap:
					svdmap[fun] = [(periph,base,size)]
				elif (periph,base,size) not in svdmap[fun]:
					svdmap[fun].append((periph,base,size))				
			if debugDev:
				rtdev.write(fun +" uses: \n")
				for dev in svdmap[fun]:
					if dev is not None:
						rtdev.write("	" +str(dev.name) +"\n")

				
#	for dev in handle:
#		if  dev._address_block is not None:
#			rtdev.write(str(dev.name) + ":" + hex(dev.base_address) + "::" +str (dev._address_block.size) + "\n")


	compartmentDevMap = []
	i = 0
	for compart in compartments:
		compartmentDevMap.append({})
		for fun in funcs:
			if fun in svdmap:
				for dev in svdmap[fun]:
					if dev is not None:
						compartmentDevMap[i][dev] = 1
		i += 1

	# Write ranges
	rtdeva = open("rtmk.devautogen", "w")
	miss = False
	for compart in compartmentDevMap:
		print(compart)
		for dtuple in compart:
			dev, base, size = dtuple
			if dev is not None:
				rtdev.write(dev.name + ":" +hex(base)+ ":"+ hex(size))
			else:
				#Missing this device info
				miss = True
			rtdev.write("\n")
		for dtuple in compart: 
			minBase = 0xFFFFFFFF # Currently we only do 32bit
			maxBase = 0
			dev, base, size = dtuple
			if dev is not None:
				start = base
				end = base +size
				if start < minBase:
					minBase = start
				if end > maxBase:
					maxBase = end
		rtdeva.write(hex(minBase) + "," + hex(maxBase - minBase) +"," +hex(maxBase) + "\n")

	if miss: 
		print "Some Devices information was missing"
	printStats()
	return 
	debugPrint = False
	printThread = False


	###Print stats about the compartmentalizations if 
	if debugPrint:
		if printThread:
			for thread in threads:
				print(compartmentMap[thread])
		l=[]
		for comp in compartments:
			l += comp
		s =set(l)
		for func in funcs:
			if func in funcs[func]:
				print("Recursive call for :" +func)

		seen = []
		for obj in l:
			if obj in seen:
				print("Duplicate: ****")
				print(obj)
			else:
				seen.append(obj)

		obj=[]
		for func in funcs:
			obj.append(func)
		for d in data:
			obj.append(d)
		sobj = set(obj)
		print("Objects in compartmenst but not in the original data: ")
		print(s - sobj)
		printLooseFunctions()
		print("Total number of compartments:" +str(len(compartments)))
#	print(compartments)
#   import pdb; pdb.set_trace();
	

#print(colors)
if __name__ == "__main__":
	main(sys.argv[1:])
