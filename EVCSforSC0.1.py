#!/usr/bin/env python
# coding: utf-8

# In[47]:


# This version takes into account 1W Prices, different durations per hour, and port utilization per hour.
# ports are np.arrays to optimize the insert and update functions.
# The assumption is that durations are integers (1-3) in this case


# In[48]:


import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from InputModule import getinput as getin
from InputModule import getinput


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


# In[49]:


# create station size by different modes - nparray with 2 rows. row 1 = consumption, row 2 = durations.
# To know if a port has an available slot, condition is: consumption != 0
mode2, mode3, mode4 = int(input("Number of mode 2 charging ports")), int(input("Number of mode 3 charging ports")), int(input("Number of FC ports"))
durat_1, consum_1 = np.zeros(mode2), np.zeros(mode2)
durat_2, consum_2 = np.zeros(mode3), np.zeros(mode3)
durat_3, consum_3 = np.zeros(mode4), np.zeros(mode4)
annual_adoption = float(input("Annual adoption rate i.e. 0.05")) 
start_charging_tariff = 5      # To beging charging EV owner will pay 5 NIS as a fee => added to alternative cost for CS


# In[50]:


# load Data from xlsx files:
# numpy indexes: 0-mode2 ,1-mode3 2-mode4, 3-Capacity, 4-probabilities
ev_database = pd.DataFrame.to_numpy(pd.read_excel("EVDatabase.xlsx"), dtype=float)

# load weekly hours list
hours = pd.DataFrame.to_numpy(pd.read_excel("hours.xlsx"), dtype=str)
graph_hours = [st[0] for st in hours]

# load prices list
annual_prices_list = pd.read_excel("Prices.xlsx")["TariffNIS"].tolist()
prices = annual_prices_list[0:168]    # Week 1 prices are being used for this simulation.

# import list of new arrivals at given hour in week
arrivals = pd.read_excel("Arrivals.xlsx")["Tot arrivals"].tolist()

# import list of durations at given hour in week
duration = pd.read_excel("Durations.xlsx")["Total Durations"].tolist()       # When duration is a dataset as arrivals
# duration = [2 for _ in range(len(arrivals))]         # When duration is an Avg constant value

# create zeros lists - alternative cost (loss), 
empty = [0 for _ in range(len(arrivals))]
port1_utilization, port2_utilization, port3_utilization = empty[:], empty[:], empty[:]
alt_cost, rejections, potentials, loads, load1, load2, load3 = 0, empty[:], empty[:], empty[:], empty[:], empty[:], empty[:]


# In[51]:


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


# In[53]:


# output 
print(f"Peak consumption: {max(loads):6.2f} kW")
print(f"Total rejected: {sum(rejections)}")
print(f"Total potentials: {sum(potentials)}")
print(f"Estimated weekly revenue loss: {alt_cost:6.2f} NIS")
print(f"Weekly total {sum(loads):6.2f} kWh")
index = [i for i in range(168)]
fig = plt.figure()
fig.suptitle('Combined Weekly Load from all modes')
plt.xlabel('Hour in week')
plt.plot(index, loads)
plt.ylabel('kW')
plt.grid(color='g', linestyle='-', linewidth=0.1)
fig.set_figwidth(17)
fig.set_figheight(6)


# In[54]:


x = index
fig, axs = plt.subplots(3, sharex=True, sharey=True)
fig.suptitle('Port Utilization % for three ports per hour')
axs[0].plot(x, port1_utilization, '-')
axs[1].plot(x, port2_utilization, '-')
axs[2].plot(x, port3_utilization, '-')
fig.set_figwidth(17)
fig.set_figheight(6)
axs[0].title.set_text('Mode 2 charging port utilization')
axs[1].title.set_text('Mode 3 charging port utilization')
axs[2].title.set_text('Mode 4 charging port utilization')


# In[55]:


# Basic stacked area chart.
fig = plt.figure()

plt.stackplot(index,load1, load2, load3, labels=['Mode 2','Mode 3','Mode 4'])
plt.legend(loc='upper left')
fig.set_figwidth(17)
fig.set_figheight(6)


# In[ ]:




