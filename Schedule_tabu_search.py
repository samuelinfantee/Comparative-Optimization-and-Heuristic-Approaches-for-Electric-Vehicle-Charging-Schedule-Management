import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
import random
from copy import deepcopy

# -------------------------
# PARAMETERS
# -------------------------
start_time = time.time()
charging_rates = [19, 15, 12]
num_chargers = 259
MDL = [103]*24
ToU_rate = 0.227
fixed_price = 0.5
arrival_fee = 0.99
MDL_penalty_rate = 0.5
T = 24
max_iter = 50
tabu_tenure = 20

# -------------------------
# LOAD DATA
# -------------------------
excel_path = r"C:\Users\samue\Desktop\AA_LOS ANDES\Semestre 7\Proyecto\Instancias 24h.xlsx"
df = pd.read_excel(excel_path, sheet_name="79")
EV_data = list(zip(df.iloc[:, 0], df.iloc[:, 4], df.iloc[:, 2]))
EV_data = sorted(EV_data, key=lambda x: x[0])

# -------------------------
# FIFO INITIALIZATION
# -------------------------
def build_fifo_plan():
    hourly_consumption = [0]*T
    hourly_chargers = [0]*T
    plan = {i: [] for i in range(len(EV_data))}
    for i, (arrival, departure, demand) in enumerate(EV_data):
        best_rate = min(charging_rates, key=lambda r: demand % r)
        energy_needed = demand
        for t in range(arrival, departure):
            if energy_needed < best_rate:
                break
            if hourly_chargers[t] < num_chargers:
                plan[i].append((t, best_rate))
                hourly_consumption[t] += best_rate
                hourly_chargers[t] += 1
                energy_needed -= best_rate
    return plan

# -------------------------
# OBJECTIVE FUNCTION
# -------------------------
def evaluate(plan):
    total_income = 0
    total_penalty = 0
    electricity_cost = 0
    energy_used_per_hour = [0]*T
    completion_sum = 0

    for i, sessions in plan.items():
        arrival, departure, demand = EV_data[i]
        charged = sum(s[1] for s in sessions)
        completion_sum += (charged / demand * 100) if demand > 0 else 0
        total_income += charged * fixed_price + arrival_fee
        electricity_cost += charged * ToU_rate
        for s in sessions:
            energy_used_per_hour[s[0]] += s[1]

    for t in range(T):
        if energy_used_per_hour[t] > MDL[t]:
            total_penalty += (energy_used_per_hour[t] - MDL[t]) * MDL_penalty_rate * ToU_rate

    obj = total_income - electricity_cost - total_penalty
    avg_completion = completion_sum / len(EV_data)
    return obj, total_income, electricity_cost, total_penalty, avg_completion

# -------------------------
# HELPER FOR HOURLY STATE
# -------------------------
def get_hourly_state(plan):
    hourly_chargers = [0]*T
    hourly_consumption = [0]*T
    for sessions in plan.values():
        for t, rate in sessions:
            hourly_chargers[t] += 1
            hourly_consumption[t] += rate
    return hourly_chargers, hourly_consumption

# -------------------------
# NEIGHBOR GENERATION
# -------------------------
def generate_neighbors(plan, hourly_chargers, hourly_consumption):
    neighbors = []
    for _ in range(10):
        new_plan = deepcopy(plan)
        ev = random.choice(list(plan.keys()))
        if not new_plan[ev]:
            continue
        idx = random.randint(0, len(new_plan[ev]) - 1)
        old_t, rate = new_plan[ev][idx]
        arrival, departure, demand = EV_data[ev]
        for dt in [-2, -1, 1, 2]: 
            new_t = old_t + dt
            if arrival <= new_t < departure and hourly_chargers[new_t] < num_chargers and hourly_consumption[new_t] + rate <= MDL[new_t]:
                new_plan[ev][idx] = (new_t, rate)
                neighbors.append(((ev, old_t, new_t), new_plan))
                break
    return neighbors

# -------------------------
# TABU SEARCH LOOP
# -------------------------
current_plan = build_fifo_plan()
best_plan = deepcopy(current_plan)
best_obj, *_ = evaluate(best_plan)
print("Initial objective (FIFO):", best_obj)

tabu_list = []
iter_count = 0
obj_values = [best_obj]  # store objective values per iteration

while iter_count < max_iter:
    hourly_chargers, hourly_consumption = get_hourly_state(current_plan)
    neighbors = generate_neighbors(current_plan, hourly_chargers, hourly_consumption)
    best_neighbor = None
    best_neighbor_obj = -float('inf')

    for move, neighbor in neighbors:
        valid = True
        for i, sessions in neighbor.items():
            if sum(s[1] for s in sessions) > EV_data[i][2]:
                valid = False
                break
        if not valid or move in tabu_list:
            continue

        obj, *_ = evaluate(neighbor)
        if obj > best_neighbor_obj:
            best_neighbor = (move, neighbor)
            best_neighbor_obj = obj

    if best_neighbor:
        move, current_plan = best_neighbor
        tabu_list.append(move)
        if len(tabu_list) > tabu_tenure:
            tabu_list.pop(0)
        if best_neighbor_obj > best_obj:
            best_plan = deepcopy(current_plan)
            best_obj = best_neighbor_obj

    obj_values.append(best_obj)
    print(f"Iteration {iter_count + 1}: Best Objective Value: {best_obj}")
    iter_count += 1

# -------------------------
# FINAL OUTPUT
# -------------------------
obj, total_income, electricity_cost, total_penalty, avg_completion = evaluate(best_plan)
print("\nFINAL RESULTS - TABU SEARCH")
print(f"Total Income (incl. arrival fees): €{round(total_income, 2)}")
print(f"Total Electricity Cost: €{round(electricity_cost, 2)}")
print(f"Total Penalty: €{round(total_penalty, 2)}")
print(f"Objective Function (Tabu-Swap): €{round(obj, 2)}")
print(f"Average Completion Degree: {round(avg_completion, 2)}%")
print(f"Execution Time: {round(time.time() - start_time, 2)} seconds")

# -------------------------
# PLOT OBJECTIVE FUNCTION EVOLUTION
# -------------------------
plt.plot(range(len(obj_values)), obj_values, marker='o', linestyle='-', color='b')
plt.title('Objective Function Value Over Iterations')
plt.xlabel('Iteration')
plt.ylabel('Objective Function Value')
plt.grid(True)
plt.tight_layout()
plt.show()


# -------------------------
# PLOT: CHARGERS UTILIZED PER HOUR
# -------------------------

# Compute chargers used per hour in best_plan
chargers_in_use_per_hour = [0] * T
for sessions in best_plan.values():
    for t, _ in sessions:
        chargers_in_use_per_hour[t] += 1

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(range(T), chargers_in_use_per_hour, color='blue')

ax.set_xlabel('Time (Hour)')
ax.set_ylabel('Chargers in Use')
ax.set_title('Hourly Utilization of Chargers – Tabu Search Heuristic')
ax.set_xticks(range(T))
ax.set_ylim(0, 30)  # Set upper limit slightly above total charger count

plt.tight_layout()
plt.show()

# -------------------------
# PLOT: Available Energy vs. Consumed Energy
# -------------------------

# Calculate energy used per hour
energy_used_per_hour = [0] * T
for sessions in best_plan.values():
    for t, rate in sessions:
        energy_used_per_hour[t] += rate

# Define the MDL constant line
mdl_limit = MDL[0]  # assuming it's constant (103 kW)

# Plot
fig, ax = plt.subplots(figsize=(10, 6))

# Bar plot for energy used
ax.bar(range(T), energy_used_per_hour, color='green', label='Consumed Energy (kW)')

# Dashed red line for MDL
ax.axhline(y=mdl_limit, color='red', linestyle='--', label='Maximum Demand Limit (103 kW)')

# Labels and formatting
ax.set_xlabel('Time (Hour)')
ax.set_ylabel('Energy (kW)')
ax.set_title('Energy Consumption Compared to MDL – Tabu Search Heuristic')
ax.set_xticks(range(T))
ax.legend()

plt.tight_layout()
plt.show()

# -------------------------
# PLOT: Distribution of Charging Rates
# -------------------------

# Charging rates to analyze
charging_rates = [12, 15, 19]

# Initialize counters for each rate
rate_counts = {r: 0 for r in charging_rates}

# Count how many EVs used each rate
for sessions in best_plan.values():
    used_rates = set(rate for _, rate in sessions)
    for r in used_rates:
        if r in rate_counts:
            rate_counts[r] += 1  # count once per EV per rate

# Sort rates for consistent axis
sorted_rates = sorted(charging_rates)
counts = [rate_counts[r] for r in sorted_rates]

# Plotting
fig, ax = plt.subplots(figsize=(8, 6))

ax.bar(sorted_rates, counts, color='blue')

# Axis labels and formatting
ax.set_xticks(sorted_rates)
ax.set_xticklabels([f'{r} kW' for r in sorted_rates])
ax.set_xlabel('Charging Rate (kW)')
ax.set_ylabel('Number of Vehicles')
ax.set_title('Distribution of Assigned Charging Rates – Tabu Search Heuristic')

plt.tight_layout()
plt.show()
