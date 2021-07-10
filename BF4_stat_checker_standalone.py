# Import dependencies
import time
import requests
import matplotlib.pyplot as plt
import numpy as np
from bokeh.plotting import figure
from bokeh.plotting import show
from bokeh.layouts import column

# Name of person to fetch reports for
player_name = input("Origin name of player: ")

# Number of reports to fetch
fetch_number = int(input("Number of Reports to look up: "))

# Interval for calculation of moving average
ma_interval = int(input("Interval for moving average. Recommended to be at least 10: "))

assert fetch_number >= 20, "Number of reports should be greater or equal 20 to get a good result"

# Prepare empty arrays
weapons = {}
vehicles = {}
kills = np.array([])
deaths = np.array([])
bwkills = np.array([])
bvkills = np.array([])
headshots = np.array([])
shots_fired = np.array([])
shots_hit = np.array([])
headshot_kills = np.array([])
nru_count = 0
vehicle_rounds = 0

# Counter for how many reports have been fetched already
fetched = 0


# Function that evaluates the data
def evaluate(data_dict):
    global weapons, vehicles, kills, deaths, bwkills, bvkills, headshots, nru_count, vehicle_rounds, shots_fired, shots_hit, headshot_kills

    # Iterate through all reports
    for i in data_dict["br_array"]:

        # Count if round has been played on our server
        if "NRU" in i["serverName"]:
            nru_count += 1

        # Count if kills with best vehicle > kills with best weapon
        if i["vehBestKills"] > i["bwKills"]:
            vehicle_rounds += 1

        # Fill dictionary of best vehicles
        if i["vehBest"] not in vehicles.keys():
            vehicles[i["vehBest"]] = i["vehBestKills"]
        else:
            vehicles[i["vehBest"]] += i["vehBestKills"]

        # Fill dictionary of best weapons
        if i["bestWeapon"] not in weapons.keys():
            weapons[i["bestWeapon"]] = i["bwKills"]
        else:
            weapons[i["bestWeapon"]] += i["bwKills"]

        # Fill arrays
        shots_fired = np.append(shots_fired, i["shotsFired"])
        shots_hit = np.append(shots_hit, i["shotsHit"])
        if isinstance(i["headShots"], str):
            headshot_kills = np.append(headshot_kills, int(i["headShots"].strip("c")))
        else:
            headshot_kills = np.append(headshot_kills, i["headShots"])
        bwkills = np.append(bwkills, i["bwKills"])
        bvkills = np.append(bvkills, i["vehBestKills"])
        kills = np.append(kills, i["kills"])
        deaths = np.append(deaths, i["deaths"])


# BF4 cheatreport only allows 200 reports to be fetched at a time. This loop fetches the newest 200 reports from the current time.
# It then checks the timestamp of the oldest report out of that batch and starts a new request using that timestamp as 
# "only reports older than this date". This results in the script fetching consecutive batches of 200 reports until
# the given number of reports is reached. However, because this results in the last report of one batch being the same 
# as the first report of the next batch, it has to be cut from the enxt batch to temove dupicates.        

while fetched != fetch_number:
    # Fetch the first batch
    if fetched == 0:
        if fetch_number < 200:
            r = requests.get(
                'http://bf4cheatreport.com/db_br.php?uid=' + player_name + '&cnt=' + str(fetch_number) + '&ts=' + str(
                    int(time.time())) + '&outputtype=json')
        else:
            r = requests.get('http://bf4cheatreport.com/db_br.php?uid=' + player_name + '&cnt=200' + '&ts=' + str(
                int(time.time())) + '&outputtype=json')

        # Call evaluate function to evaluate the data
        evaluate(r.json())

        # Coiunt number of reports fetched
        fetched += len(r.json()["br_array"])

        # Check if the number of reports fetched is smaller than 200. If yes, that's the maximum amount of reports available
        # and the loop stops
        print(f"Reports fetched: {fetched}")
        if len(r.json()["br_array"]) < 200:
            break

    # Fetch new batches using the timestamp of the last report from the previous batch as the timestamp as the 
    # newest report of the next batch.
    else:
        # If the remaining number of reports that have to be fetched is greater or equal to 199, then the request is
        # sent for 200 reports, which results in 199 new reports
        if fetch_number - fetched >= 199:
            r = requests.get('http://bf4cheatreport.com/db_br.php?uid=' + player_name + '&cnt=200' + '&ts=' + str(
                int(r.json()["br_array"][-1]["createdAt"])) + '&outputtype=json')
            evaluate(r.json())
            # Increase counter
            fetched += len(r.json()["br_array"]) - 1
            # Check if the number of reports fetched is smaller than 200. If yes, that's the maximum amount of reports available
            # and the loop stops
            print(f"Reports fetched: {fetched}")
            if len(r.json()["br_array"]) < 200:
                break

        # If the remaingin number of reports that have to be fetched is smaller than 199, it sends an request for the
        # the still missing number of reports instead of 200
        else:
            r = requests.get('http://bf4cheatreport.com/db_br.php?uid=' + player_name + '&cnt=' + str(
                fetch_number - fetched + 1) + '&ts=' + str(
                int(r.json()["br_array"][-1]["createdAt"])) + '&outputtype=json')
            evaluate(r.json())
            # Increase counter
            fetched += len(r.json()["br_array"]) - 1
            print(f"Reports fetched: {fetched}")
            break

if fetched != fetch_number:
    print(
        f"Unable to fetch more than {fetched} reports. That is most likely the total amount of available reports for this player")
else:
    print(f"successfully fetched {fetched}/{fetch_number} reports")

# Reverses the order of data in the array so oldest number is first, oldest number is last
bwkills = np.flip(bwkills)
bvkills = np.flip(bvkills)
kills = np.flip(kills)
deaths = np.flip(deaths)
shots_fired = np.flip(shots_fired)
shots_hit = np.flip(shots_hit)
headshot_kills = np.flip(headshot_kills)

assert fetch_number > ma_interval, "Number of Reports must be greater than MA interval"
assert ma_interval > 0, "MA interval must be greater than zero"

# Create empty arrays for new data to be stores
kd_ma = np.array([])
kd = np.array([])
vw_ratio_ma = np.array([])
vw_ratio = np.array([])
accuracy_ma = np.array([])
accuracy = np.array([])
hsk_rate_ma = np.array([])
hsk_rate = np.array([])

# Iterate through the data
for i, j in enumerate(kills):

    # If number of deaths would be equal to 0, treat it as being 1 for the calculation
    # of the KD to prevent division by zero error. This might happen in the first 1 - 3 reports
    if np.sum(deaths[:i + 1]) == 0:
        kd = np.append(kd, np.sum(kills[:i + 1]))
    # After that, calculate KD as usual
    else:
        kd = np.append(kd, np.sum(kills[:i + 1]) / np.sum(deaths[:i + 1]))

    # If number of weapon kills would be equal to 0, treat it as being 1 for the calculation
    # of the KD to prevent division by zero error. This might happen in the first 1 - 3 reports
    if np.sum(bwkills[:i + 1]) == 0:
        vw_ratio = np.append(vw_ratio, np.sum(bvkills[:i + 1]))
    else:
        vw_ratio = np.append(vw_ratio, np.sum(bvkills[:i + 1]) / np.sum(bwkills[:i + 1]))

    # If number of shots fired is equal to 0, accuracy is treated as being equal to 0
    if np.sum(shots_fired[:i + 1]) == 0:
        accuracy = np.append(accuracy, 0)
    else:
        accuracy = np.append(accuracy, np.sum(shots_hit[:i + 1]) / np.sum(shots_fired[:i + 1]))

    # If number of kills is equal to 0, hsk ratio is treated as being equal to 0
    if np.sum(kills[:i + 1]) == 0:
        hsk_rate = np.append(hsk_rate, 0)
    else:
        hsk_rate = np.append(hsk_rate, np.sum(headshot_kills[:i + 1]) / np.sum(kills[:i + 1]))

    # As long as the number of reports while iterating is smaller than the defined interval for the moving average,
    # calculate the moving average KD with from the available number of reports
    if i < ma_interval:

        # Calculate MA of vehicles to weapons ratio
        if np.sum(bwkills[:i + 1]) == 0:
            vw_ratio_ma = np.append(vw_ratio_ma, np.sum(bvkills[:i + 1]))
        else:
            vw_ratio_ma = np.append(vw_ratio_ma, np.sum(bvkills[:i + 1]) / np.sum(bwkills[:i + 1]))

        # Calculate MA of KD
        if np.sum(deaths[:i + 1]) == 0:
            kd_ma = np.append(kd_ma, np.sum(kills[:i + 1]))
        else:
            kd_ma = np.append(kd_ma, np.sum(kills[:i + 1]) / np.sum(deaths[:i + 1]))

        # Calculate MA of accuracy
        if np.sum(shots_fired[:i + 1]) == 0:
            accuracy_ma = np.append(accuracy_ma, 0)
        else:
            accuracy_ma = np.append(accuracy_ma, np.sum(shots_hit[:i + 1]) / np.sum(shots_fired[:i + 1]))

        # Calculate MA of headshot kill rate
        if np.sum(kills[:i + 1]) == 0:
            hsk_rate_ma = np.append(hsk_rate_ma, 0)
        else:
            hsk_rate_ma = np.append(hsk_rate_ma, np.sum(headshot_kills[:i + 1]) / np.sum(kills[:i + 1]))

    # After that, calculate the moving average KD for every report from the last 50 reports
    else:
        vw_ratio_ma = np.append(vw_ratio_ma,
                                np.sum(bvkills[i - ma_interval:i + 1]) / np.sum(bwkills[i - ma_interval:i + 1]))
        kd_ma = np.append(kd_ma, np.sum(kills[i - ma_interval:i + 1]) / np.sum(deaths[i - ma_interval:i + 1]))
        accuracy_ma = np.append(accuracy_ma,
                                np.sum(shots_hit[i - ma_interval:i + 1]) / np.sum(shots_fired[i - ma_interval:i + 1]))
        hsk_rate_ma = np.append(hsk_rate_ma,
                                np.sum(headshot_kills[i - ma_interval:i + 1]) / np.sum(kills[i - ma_interval:i + 1]))

plt_group = []

# Create Moving average KD plot
makd_plt = figure(plot_width=1000, plot_height=375,
                  title=f"Moving average KD of last {ma_interval} rounds over time, "
                        f"current: {kd_ma[-1]:.2f}, all-time high: {np.max(kd_ma):.2f}",
                  x_axis_label="Rounds", y_axis_label="Moving average KD")
makd_plt.line(np.arange(0, kills.size, 1), kd_ma)
plt_group.append(makd_plt)

# Create KD plot
kd_plt = figure(plot_width=1000, plot_height=375,
                title=f"KD over time,\n current: {kd[-1]:.2f}, all-time high: {np.max(kd):.2f}",
                x_axis_label="Rounds", y_axis_label="KD")
kd_plt.line(np.arange(0, kills.size, 1), kd)
plt_group.append(kd_plt)

# Create Moving average vehicle/weapon plot
vhclma_plt = figure(plot_width=1000, plot_height=375,
                    title=f"Moving average ratio of best vehicle kills to best weapon kills over the last "
                          f"{ma_interval} rounds, current: {vw_ratio_ma[-1]:.2f}, all-time high: "
                          f"{np.max(vw_ratio_ma):.2f}",
                    x_axis_label="Rounds", y_axis_label="Moving average ratio vehicle kills to weapon kills")
vhclma_plt.line(np.arange(0, kills.size, 1), vw_ratio_ma)
plt_group.append(vhclma_plt)

# Create average vehicle/weapon plot
vhcl_plt = figure(plot_width=1000, plot_height=375,
                  title=f"Ratio of best vehicle kills to best weapon kills over time, current: {vw_ratio[-1]:.2f}, "
                        f"all-time high: {np.max(vw_ratio):.2f}",
                  x_axis_label="Rounds", y_axis_label="Ratio vehicle kills to weapon kills")
vhcl_plt.line(np.arange(0, kills.size, 1), vw_ratio)
plt_group.append(vhcl_plt)

# Create Moving average accuracy plot
accma_plt = figure(plot_width=1000, plot_height=375,
                   title=f"Moving average accuracy over the last {ma_interval} rounds,\n current: {accuracy_ma[-1]:.2f}"
                         f", all-time high: {np.max(accuracy_ma):.2f}",
                   x_axis_label="Rounds", y_axis_label="Moving average accuracy")
accma_plt.line(np.arange(0, kills.size, 1), accuracy_ma)
plt_group.append(accma_plt)

# Create accuracy plot
acc_plt = figure(plot_width=1000, plot_height=375,
                 title=f"Accuracy over time, current: {accuracy[-1]:.2f}, all-time high: {np.max(accuracy):.2f}",
                 x_axis_label="Rounds", y_axis_label="Accuracy")
acc_plt.line(np.arange(0, kills.size, 1), accuracy)
plt_group.append(acc_plt)

# Create Moving average HSK rate plot
hsk_ma_plt = figure(plot_width=1000, plot_height=375,
                    title=f"Moving average hsk rate over the last {ma_interval} rounds, current: {hsk_rate_ma[-1]:.2f}"
                          f", all-time high: {np.max(hsk_rate_ma):.2f}",
                    x_axis_label="Rounds", y_axis_label="Moving average hsk rate")
hsk_ma_plt.line(np.arange(0, kills.size, 1), hsk_rate_ma)
plt_group.append(hsk_ma_plt)

# Create HSK rate plot
hsk_plt = figure(plot_width=1000, plot_height=375,
                    title=f"Hsk rate over time, current: {hsk_rate[-1]:.2f}, all-time high: {np.max(hsk_rate):.2f}",
                    x_axis_label="Rounds", y_axis_label="Hsk rate")
hsk_plt.line(np.arange(0, kills.size, 1), hsk_rate)
plt_group.append(hsk_plt)

show(column(*plt_group))

print(f"Player name: {player_name}")
print(f"Favorite weapon: {max(weapons, key=weapons.get)}, {weapons[max(weapons, key=weapons.get)]} kills")
print(f"Favorite vehicle: {max(vehicles, key=vehicles.get)}, {vehicles[max(vehicles, key=vehicles.get)]} kills")
print(f"# of reports analyzed: {fetched}")
print(f"# of rounds with best vehicle kills > best weapon kills: {vehicle_rounds}")
print(f"# of rounds played on NRU server: {nru_count}")

input(f"\nPress any key to exit")
