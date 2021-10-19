#!/usr/bin/env python
# coding: utf-8

# In[3]:


# simulation steps:
#     outer loop on hours in arrival_data - i
#     for each hour:                                                           Done   O(hours = 168*52*7 = 61K for 7 years)
#         create event by finding out ev_arrivals(arrival_data[i])             Done
#         for every event/arrival of an EV:                                                    O(events = might grow by usually < 50)
#             update ports list for exceeded durations                         Debug  O(ports = usually < 50)
#             make sure there is space using choice() and choose port too      Debug  O(1)
#             choose car if there is space                                     Done   O(1)
#             insert car in port                                               Debug  O(ports)
#             find total consumption                                           Debug
#             return (consumption, hour)                                       Done
#     add to df
# plot df with hours and week etc. perhaps export to csv or excel              To Do


# In[16]:


import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

# There are 3 ports. each port is represented by a matrix - [[status=0\1], [durations=hours], [consumption of car=kW]]
# Every hour there are arrivals. EV arrivals is the product: arrivals * adoption. if arrival is float a probabalistic choice is made
# Every EV arrival will be given a car by a choice made with a given distribution. In the future this can take extra variables such as SOC or price

# Input - all three ports. Function - choose for the current event a port by availability. Output -the port and an integer 1, 2 or 3 representing port number. if output is 0 then all ports are full
def choice(port_a, port_b, port_c):
    tot = sum(port_a[0] + port_b[0] + port_c[0])  # find total available ports
    if tot:
        port_prob = [sum(port_a[0]) / tot, sum(port_b[0]) / tot, sum(port_c[0]) / tot]
    else:
        return [], 0                           # This means that there are no more available ports!
    temp = int(np.random.choice([1, 2, 3], 1, p=port_prob))
    if temp == 1:
        return port_a, temp
    elif temp == 2:
        return port_b, temp
    elif temp == 3:
        return port_c, temp


# this function inserts a car to a chosen port with his given consumption and duration. This may change due to complexity additions
def insert(port, mode, ev_array, car_index, durat):
    if not port[0]:             # if the port does not have any slots to begin with skip
        return
    for inx in range(len(port[0])):
        if port[0][inx]:  # if available insert
            port[0][inx] = 0
            port[1][inx] = durat
            port[2][inx] = ev_array[car_index][mode-1]
            return
    return


# ports may or may not be available, but durations change after each iteration (1 hour less) but can be float too (40 minutes). this func. can update each port given durations
def update(port):
    if not port[0]:
        return
    for slt in range(len(port[0])):
        if not port[0][slt]:  # if port is being used, then it is set to be 0. we may need to extract it and update consumption
            if port[1][slt] >= 1:  # car should stay put until next round because duration is more than 1 hour
                port[1][slt] -= 1  # subtract an hour from remaining duration
            elif port[1][slt] <= 0:  # in case car needed to go out - remove protocol:
                port[0][slt] = 1  # update status to available
                port[1][slt] = 0  # update duration to be 0
                port[2][slt] = 0  # update consumption to be 0
            else:  # in case a fraction of an hour remains, choose wisely
                decision = np.random.choice([1, 0], 1, p=[port[1][slt], 1 - port[1][slt]])  # choose with probability if car will stay[1] or leave[0]
                if decision:
                    port[1][slt] -= 1  # car stays put
                else:  # remove car
                    print("remove2")
                    port[0][slt] = 1 # set to be an available port
                    port[1][slt] = 0 
                    port[2][slt] = 0 # consumption is 0
    return


# this can determine how many cars arrive at each given point to follow number of declined charging events and kW consumption
def get_arrival(arr, adp_level):
    arr_frac = arr * adp_level
    deter_arr = int(arr_frac)
    decision = np.random.choice([1, 0], 1, p=[arr_frac % 1, 1 - arr_frac % 1])
    return int(deter_arr + decision)


def choose_ev(ev_data):  # this should be done for each arrival. ev_data is type ndarray
    return int(np.random.choice(np.shape(ev_data)[0], 1, p=ev_data[:, 4]))


# In[17]:


# loading Data from file
# numpy indexes: 0-mode2 ,1-mode3 2-mode4, 3-Capacity, 4-probabilities
ev_database = pd.DataFrame.to_numpy(pd.read_excel("EVDatabase.xlsx"), dtype=float)

# hours = pd.DataFrame.to_numpy(pd.read_excel("hours.xlsx"), dtype=str)
# graph_hours = [st[0] for st in hours]

# import list of arrival data - can be done faster/with array
arr_data = pd.DataFrame.to_numpy(pd.read_excel("Arrivals.xlsx"))
arrival_data = arr_data.tolist()
arrivals = [_[0] for _ in arrival_data]


# In[18]:


# inputs - port numbers for mode 2 3 and 4
p_nums = [0, 10, 0]
duration = 2         # duration is constant
adoption = 0.02
rejected, potentials, consumption = [], [], [0 for h in range(len(arrivals))]


# In[19]:


# create compatible port lists. each list contains 3 lists: status, duration and consumption.
port1 = [[1 for _ in range(station_size[0])], [0 for _ in range(station_size[0])], [0 for _ in range(station_size[0])]]
port2 = [[1 for _ in range(station_size[1])], [0 for _ in range(station_size[1])], [0 for _ in range(station_size[1])]]
port3 = [[1 for _ in range(station_size[2])], [0 for _ in range(station_size[2])], [0 for _ in range(station_size[2])]]
if p_nums[0] == 0:
    port1 = [[], [], []]
elif p_nums[1] == 0:
    port2 = [[], [], []]
elif p_nums[2] == 0:
    port3 = [[], [], []]

    
# main simulation program
for hour, num in enumerate(arrivals):
    events = get_arrival(num, adoption)  # adoption is const but can be functionallized with another outer loop
    potentials += [events]
    update(port1) # These updates needs to remove 1 hour from duration
    update(port2) 
    update(port3)
    for i in range(events):
        chosen_port, index = choice(port1, port2, port3)  # choose a port if available and return the port itself
        if not chosen_port:
            rejected += [hour]
        else:
            insert(chosen_port, index, ev_database, choose_ev(ev_database), duration-1)  # error list index out of range
    # add total consumption at given hour index
    consumption[hour] = sum(port1[2] + port2[2] + port3[2])
    


# In[20]:


# output 
print(f"Peak consumption: {max(consumption):6.2f} kW")
print(f"Num rejected: {len(rejected)}")
print(f"Num potentials: {sum(potentials)}")
print(f"Estimated weekly loss: Add power price NIS")
print(f"Weekly total {sum(consumption):6.2f} kWh")
index = [i for i in range(168)]
plt.xlabel('Hour in week')
plt.plot(index, consumption)
plt.ylabel('kW')
plt.grid(color='g', linestyle='-', linewidth=0.1)


# In[9]:


# debugging and changes:

# 1. duration should be more than 1 value => it is set to 0 because of sequencing of updating ports. In addition it is fixed but can be changed to be imported
# 2. changes in port numbers does not change rejected/potentials. this means the program has an issue ==> Fixed
# 3. simulation is not correct because there is consumption also at no man hours!!                    ==> Fixed
# 3. if we add 1 port to mode 2 it suddenly changes too many things. this cannot be right.            ==> Fixed
# 4. can SOC be taken into account ?                  
# 5. can prices be taken into account ?                                      ==> Yes will be implemented in simulation 1.1          
# 6. Add station utillization percentage                                     ==> Possible, perhaps at peaks?      


# In[ ]:




