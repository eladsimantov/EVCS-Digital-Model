#!/usr/bin/env python
# coding: utf-8

# In[46]:


# This EVCS simulation script has the following assumptions:
    # Arrivals - # of new cars arriving at each hour is known and given as input
    # EV fleet and distributions aer known and given as input
    # EV adoption rate is constant per year and given as input
    # Durations - The time each arrival at every hour stays in the CS is known and given as input
    # Arriving EVs will always choose to charge if there are available ports
    # SOC is not in simulation
    # If a PHEV arrives at a FC station it is rejected.
    # Prices per hour are taken from the hourly model.
    # charging tarif is 5 NIS to begin charging

# The input process for a Shopping Center is as follows:
    # get total weekly traffic e.g. N = 50000
    # multiply by normalized arrival profile for SC
    # get weekly durations
    # repeat 52 times to get annual arrivals and durations (8736 hours)

# The simulation process is as follows
    # for every hour get EV arrivals using adoption rate
        # update ports and remove 1 hour from car durations
        # for every arrival choose an EV from fleet with dist. function
            # Add EV to port if available else add to rejections and calc alternative cost
        # calc port utilization per hour in iteration
        # calc consumption of each port per hour in iteration


# In[47]:


import numpy as np
import pandas as pd


# to determine how many cars arrive at each given point we need to follow the number of declined charging events and kW consumption
def get_arrival(arr, adp_level):
    arr_frac = arr * adp_level
    deter_arr = int(arr_frac)
    decision = np.random.choice([1, 0], 1, p=[arr_frac % 1, 1 - arr_frac % 1])
    return int(deter_arr + decision)


# Every EV arrival will be given a car by a choice made with a given distribution. In the future this can take extra variables such as SOC or price
def choose_ev(ev_data):  # this should be done for each arrival. ev_data is type ndarray
    return int(np.random.choice(np.shape(ev_data)[0], 1, p=ev_data[:, 4]))


# Input - consumption of three ports (ndarrays) and ev, Function - choose for the EV a port by availability and compatibility. Output - availability (0/1) and port index (123)
def choose_port(m2, m3, m4, ev, ev_data):
    a, b, c = len(m2[m2==0]), len(m3[m3==0]), len(m4[m4==0])          # calculate number of available slots in each port
    if ev_data[ev,2]:            # if the ev has FC capabilities then choice may change ()
        total = a + b + c                        # find total available ports
        if total:                                # in this case there must be an available slot
            port_prob = [a/total, b/total, c/total]
            port_index = int(np.random.choice([1, 2, 3], 1, p = port_prob))
            slot = np.argmax(locals()[f'm{port_index+1}'] == 0)
            return port_index, slot
        else:
            return 0, 0
    else:                        # in case the ev is a phev that can't use FCs
        total = a + b        
        if total:
            port_prob = [a/total, b/total]
            port_index = int(np.random.choice([1, 2], 1, p = port_prob))
            slot = np.argmax(locals()[f'm{port_index+1}'] == 0)
            return port_index, slot
        else:
            return 0, 0

        
def update_ports(d1,d2,d3,c1,c2,c3):
    # if duration will be in fractions of hour we can genarate randoms or choose with prob 
#     d1[d1<1] = np.random.randint(2)
#     d2[d2<1] = np.random.randint(2)
#     d3[d3<1] = np.random.randint(2)
    
    d1[d1>1] -= 1    # durations with more than 1h should simply decrese 1h 
    d2[d2>1] -= 1
    d3[d3>1] -= 1
    
    c1[d1<=1] = 0    # consumptions update to 0 in slots that duration is 1 which means that hour is finished
    c2[d2<=1] = 0
    c3[d3<=1] = 0
    return

# --------------------------------------------------------------------------------------------------------------


# In[48]:


# numpy indexes: 0-mode2 ,1-mode3 2-mode4, 3-Capacity, 4-probabilities
ev_database = pd.DataFrame.to_numpy(pd.read_excel("EVDatabase.xlsx"), dtype=float)

# load prices list
annual_prices_list = pd.read_excel("Prices.xlsx")["TariffNIS"].tolist()
prices = annual_prices_list[0:8736]   

# load input data - plugin price, adoption and number of ports
inputs = pd.read_excel('Input variables.xlsx')
mode2, mode3, mode4 = int(inputs['Value'][2]), int(inputs['Value'][3]), int(inputs['Value'][4])
annual_adoption = inputs['Value'][1] 
start_charging_tariff = inputs['Value'][0]      # To beging charging EV owner will pay 5 NIS as a fee => added to alternative cost for CS
weekly_traffic = int(inputs['Value'][5])

# import list of new arrivals at given hour in week
arrivals = (pd.read_excel("Weekly input template.xlsx")["Tot arrivals"]*weekly_traffic).tolist()*52

# import list of durations at given hour in week
duration = pd.read_excel("Weekly input template.xlsx")["Total Durations"].tolist()*52 

# create zeros lists - alternative cost (loss), 
empty = [0 for _ in range(len(arrivals))]
port1_utilization, port2_utilization, port3_utilization = empty[:], empty[:], empty[:]
alt_cost, rejections, potentials, loads, load1, load2, load3 = 0, empty[:], empty[:], empty[:], empty[:], empty[:], empty[:]


# In[ ]:


# create station size by different modes - nparray with 2 rows. row 1 = consumption, row 2 = durations.
# To know if a port has an available slot, condition is: consumption != 0

# Create variables for simulation
durat_1, consum_1 = np.zeros(mode2), np.zeros(mode2)
durat_2, consum_2 = np.zeros(mode3), np.zeros(mode3)
durat_3, consum_3 = np.zeros(mode4), np.zeros(mode4)


# In[49]:


# EV events are discrete in Active simulation
for h, val in enumerate(arrivals):
    arr_evs = get_arrival(val, annual_adoption)
    potentials += [arr_evs]                          # count number of potentials
    update_ports(durat_1, durat_2, durat_3, consum_1, consum_2, consum_3)           # update ports by removing 1 hour from durations or removing cars
    for j in range(arr_evs):                         # loop over number of arriving EVs
        car_choice = choose_ev(ev_database)              # choose an EV - given index
        avail_port, slot = choose_port(consum_1, consum_2, consum_3, car_choice, ev_database)     # choose a port (PHEVs can't choose port 3)       
        if not avail_port:              # there may be space in a FC port but chosen car is a PHEV and therefore it is a rejection.
            rejections[h] += 1                           # num of rejections will be sum of list, and port utilization is merely the fraction between port size and rejections
            alt_cost += start_charging_tariff + sum(prices[h:h+duration[h]])            # calc alternative cost of rejection of EV.
        else:
            d = duration[h]
            if d==0:
                continue            
            globals()[f"durat_{avail_port}"][slot] = d            # add to durations in given slot location
            ev_load = ev_database[car_choice][avail_port-1]
            globals()[f"consum_{avail_port}"][slot] = ev_load               # add to consumptions in given slot location
    port1_utilization[h] = 100*np.count_nonzero(consum_1)/(len(consum_1) or 1)
    port2_utilization[h] = 100*np.count_nonzero(consum_2)/(len(consum_2) or 1)
    port3_utilization[h] = 100*np.count_nonzero(consum_3)/(len(consum_3) or 1)
    load1[h] = np.sum(consum_1)
    load2[h] = np.sum(consum_2)
    load3[h] = np.sum(consum_3)
    loads[h] = np.sum(consum_1) + np.sum(consum_2) + np.sum(consum_3)       # insert total load at given hour after dealing with events


# In[50]:


# Choose start and end
s_start, s_end = '2/1/2020', '1/30/2021'
# Generate hourly simulation model as pandas dataframe called 'tf'
timeindex = pd.date_range(start=s_start, end=s_end, freq='1h', name='Date/Hour')
df_out = pd.DataFrame(timeindex)
df_out["Mode 2 load"] = pd.DataFrame(load1)
df_out["Mode 3 load"] = pd.DataFrame(load2)
df_out["Mode 4 load"] = pd.DataFrame(load3)
df_out["Mode 2 utilization"] = pd.DataFrame(port1_utilization)
df_out["Mode 3 utilization"] = pd.DataFrame(port2_utilization)
df_out["Mode 4 utilization"] = pd.DataFrame(port3_utilization)
df_out["Rejected vehicles"] = pd.DataFrame(rejections)

df_out.to_csv("simulation output.csv")


# In[ ]:




