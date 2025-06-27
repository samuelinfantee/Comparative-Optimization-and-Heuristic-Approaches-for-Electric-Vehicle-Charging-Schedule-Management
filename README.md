# EV Charging Scheduling Optimization

This repository implements and compares two methods for optimizing EV charging schedules in a large-scale EV station (e.g., 259 charging points in Germany):

- **MILP Optimization Model (Gurobi-based)**
- **Tabu Search Heuristic (Python-based)**

These methods are part of a research study that evaluates the economic and operational performance of EV scheduling algorithms while considering arrival times, energy demands, limited chargers, ToU pricing, and Maximum Demand Limits (MDL).

---

## Models

### MILP Optimization (`Schedule_optimization_model.py`)
- Built using Gurobi and Python
- Assigns EVs to charging slots, rates, and hours
- Maximizes operator profit while minimizing energy penalties
- Ensures minimum charge completion and charger constraints

### Tabu Search Heuristic (`Schedule_tabu_search.py`)
- FIFO-based initialization
- Swap-based local search
- Avoids recently visited solutions using a tabu list
- Tracks best solution based on profit and completion
