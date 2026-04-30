# EV Charging Scheduling Optimization

This repository implements and compares two methods for optimizing EV charging schedules in a large-scale EV station (e.g., 259 charging points in Germany):

- **MILP Optimization Model (Gurobi-based)**
- **Tabu Search Heuristic (Python-based)**

This work is part of the paper **“Comparative Optimization and Heuristic Approaches for Electric Vehicle Charging Schedule Management,”** published in the **SICEL 2025 conference proceedings**.

📄 **Paper:** https://doi.org/10.15446/sicel.v12.121216

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
