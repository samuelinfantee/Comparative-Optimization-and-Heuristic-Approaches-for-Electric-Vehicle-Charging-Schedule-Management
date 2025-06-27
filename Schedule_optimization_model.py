from gurobipy import Model, GRB, quicksum
import math
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time

start_time = time.time()

# Datos de entrada basados en el artículo
num_chargers = 259  # Número de cargadores
charging_rates = [12,15,19]  # Tasas de carga en kW
# Leer el archivo de Excel
archivo_excel = r"C:\Users\samue\Desktop\AA_LOS ANDES\Semestre 7\Proyecto\Instancias 24h.xlsx"

df = pd.read_excel(archivo_excel, "79")
df

# Organizar los datos en la forma solicitada
# Asumiendo que los datos están en las primeras tres columnas
EV_data = list(zip(df.iloc[:, 0], df.iloc[:, 4], df.iloc[:, 2]))


#EV_data = [(10,13,41),(11,14,53),(11,15,43),(12,15,37),(12,15,31),(12,15,45),(12,16,59),(12,14,26),(13,14,23),(13,16,29),(13,17,37),(14,18,59),(14,17,38),(14,17,25),(15,19,55),(15,19,24),(16,20,61),(16,20,26),(16,20,52),(17,21,49),(17,21,40),(17,20,22),(17,19,32),(18,21,61),(18,21,39),(18,22,60),(18,22,68),(18,22,25)]  # Datos de los EVs: (llegada, salida, demanda de energía en kWh)
ToU_rates = 0.227  # Tarifas ToU: [Off-peak, Mid-peak, On-peak]
fixed_price = 0.5  # Precio fijo cobrado a los usuarios
MDL_penalty_rate = 0.5  # Tasa de penalización por exceder el MDL
T = 24  # Horas laborales al día
Arrive_price = 0.99

MDL = [103]*24
inicio = 0
fin = 23

#hacer grafico cargadores vs tiempo
#sustentar el cambio para tasa de carga
#replantear objetivos especificos y general

#ESTACION DE ALEMANIA
#COSTE POR LLEGAR VEHICULO = 0.99 EUROS
#COSTE POR KW = 0.5 EUROS
#PRECIO MEDIA KW ALEMANIA = 0.4125 EUROS

# Inicializar el modelo
model = Model("EV_Charging_Scheduler")

# Variables de decisión: k_{i, j, r} para cada EV, cada hora y cada tasa de carga
k = model.addVars(((i, j, r) for i in range(len(EV_data)) for j in range(inicio, fin) for r in charging_rates), vtype=GRB.BINARY, name="k")

# Variables para la penalización en cada hora
penalties = model.addVars(range(inicio, fin), vtype=GRB.CONTINUOUS, name="penalty")

# Variables de decisión para la asignación de EV a cargador
y = model.addVars(((i, r) for i in range(len(EV_data)) for r in charging_rates), vtype=GRB.BINARY, name="y")


# Función objetivo: Maximizar la ganancia total ajustada según la fórmula, incluyendo la penalización
model.setObjective(len(EV_data)*Arrive_price + quicksum(k[i, j, r] * r * (fixed_price - ToU_rates) 
                            for i in range(len(EV_data)) for j in range(inicio, fin) for r in charging_rates) - quicksum(penalties[j] for j in range(inicio, fin)), GRB.MAXIMIZE)

# Restricciones

# Asegurar que cada EV sea cargado al menos un 50% y menos de su demanda.
for i, (arrival, departure, demand) in enumerate(EV_data):
    model.addConstr(quicksum(k[i, j, r] * r for j in range(arrival, departure) for r in charging_rates) >= demand * 0.5)
    model.addConstr(quicksum(k[i, j, r] * r for j in range(arrival, departure) for r in charging_rates) <= demand)


# Si el tiempo j está fuera del intervalo de llegada y salida, forzar k a ser 0
for i, (arrival, departure, _) in enumerate(EV_data):
    for j in range(inicio, fin):
        for r in charging_rates:
            if j < arrival or j >= departure:
                model.addConstr(k[i, j, r] == 0)

# Respetar el MDL en cada hora y calcular la penalización si se excede
for j in range(inicio, fin):
    power_consumed = quicksum(k[i, j, r] * r for i in range(len(EV_data)) for r in charging_rates)
    model.addConstr(penalties[j] >= (power_consumed - MDL[j - inicio]) * MDL_penalty_rate * ToU_rates)


# Cada EV asignado a no más de un cargador
for i in range(len(EV_data)):
    model.addConstr(quicksum(y[i, r] for r in charging_rates) <= 1)


# Vincular asignación de EV a cargador con asignación de tiempo y tasa
for i in range(len(EV_data)):
    for j in range(inicio, fin):
        for r in charging_rates:
            model.addConstr(k[i, j, r] <= y[i, r])


# Respetar el límite de n cargadores simultáneamente
for j in range(inicio, fin):
    model.addConstr(quicksum(k[i, j, r] for i in range(len(EV_data)) for r in charging_rates) <= num_chargers)

# Resolver el problema
model.optimize()

# Imprimir la solución

if model.status == GRB.OPTIMAL:
    for i in range(len(EV_data)):
        for j in range(inicio, fin):
            for r in charging_rates:
                if k[i, j, r].X == 1:
                    print(f"El EV {i+1} debe cargarse en la hora {j} con una tasa de {r} kW")

    # Imprimir la penalización total
    total_penalty = sum(penalties[j].X for j in range(inicio, fin))
    print(f"Penalización total: {total_penalty}")

    # Cálculo de consumo de energía y disponibilidad
    power_consumed_resolved = [0] * T
    power_available_resolved = list(MDL)

    for j in range(inicio, fin):
        power_consumed_resolved[j-inicio] = sum(k[i, j, r].X * r for i in range(len(EV_data)) for r in charging_rates)
        power_available_resolved[j-inicio] = MDL[j-inicio] - power_consumed_resolved[j-inicio]
        #print(f"En {j} se consumió: {power_consumed_resolved[j-inicio]} kW")
        #print(f"En {j} estaba disponible: {power_available_resolved[j-inicio]} kW")
else:
    print("No se encontró una solución óptima.")


# Tabla IV

funcion_obj = 0
ganancias = 0
if model.status == GRB.OPTIMAL:
    TOU_EV = [0]*len(EV_data)
    print("\nTABLE IV.  ELECTRICITY BILL AND PROFIT CALCULATION ")
    print("EV\tCharged\t\tPaid Electricity\tProfit")

    for i in range(len(EV_data)):
        charged = 0
        paid_electricity = 0
        penalty_total = 0
        
        for j in range(inicio, fin):
            #tou_index = math.floor((j - inicio) / 4)
            tou_rate = ToU_rates
            energy_used = sum(k[i, j, r].X * r if k[i, j, r].X > 0 else 0 for r in charging_rates)
            charged += energy_used * fixed_price
            paid_electricity += energy_used * tou_rate
            
            
            for r in charging_rates:
                if k[i, j, r].X == 1:
                    TOU_EV[i] = tou_rate

        profit = charged - paid_electricity
        ganancias += profit + Arrive_price
        
        print(f"{i+1}\t${charged:.2f}\t\t${paid_electricity:.2f}\t\t\t\t${profit:.2f}")
else:
    print("No se encontró una solución óptima.")

# TABLA 3 ATHULYA ---------------------------------------------

Suma_completitud = 0

if model.status == GRB.OPTIMAL:
    print("\nTABLE  III.  POWER UTILIZATION CHART")
    print("EV\tStart time\tPower used\tCharge rate\tCompletion Degree\tCharge Period")

    for i in range(len(EV_data)):
        inicio_carga = []
        total_energy_used = 0
        charging_periods = 0
        used_rates = []

        # Calcular la energía total usada, la tasa de carga y contar los periodos de carga
        for j in range(EV_data[i][0], EV_data[i][1]):
            for r in charging_rates:
                if k[i, j, r].X == 1:
                    inicio_carga.append(j)
                    total_energy_used += r
                    if r not in used_rates:
                        used_rates.append(r)
                    charging_periods += 1

        # Calcular el grado de completitud
        completion_degree = (total_energy_used / EV_data[i][2]) * 100 if total_energy_used else 0
        Suma_completitud += completion_degree


        # Preparar texto de tasas de carga usadas
        rate_text = ", ".join([f"{rate} kW" for rate in used_rates])

        print(f"{i+1}\t{inicio_carga[0]}\t\t\t{total_energy_used} kWh\t\t{rate_text}\t\t{completion_degree:.2f}%\t\t\t\t{charging_periods}")
else:
    print("No se encontró una solución óptima.")
    

#TABLE V. PENALTIES PER HOUR ----------------------------

if model.status == GRB.Status.OPTIMAL:
    print("\nTABLE V. PENALTIES PER HOUR")
    print("Start time\tPower used\t\tMDL\t\tPenalty")
    
    for j in range(inicio, fin):
        energy_used = sum(k[i, j, r].X * r if k[i, j, r].X else 0 for r in charging_rates for i in range(len(EV_data)))
        MDL_HORA = MDL[j-10]
        exceso = energy_used - MDL_HORA
        pen = penalties[j].X
        
        if exceso > 0:
            penalidad = MDL_penalty_rate * ToU_rates * exceso
        else:
            penalidad = 0
        
        print(f"{j}\t\t\t{energy_used} kWh\t\t{MDL_HORA}\t\t{penalidad:.2f}")

# GRAFICOS-------------------

#GRAFICO CARGADORES VS TIEMPO ------------------------------------

# Número de cargadores y horas
num_chargers = 259  # Número de cargadores
T = 24  # Horas laborales al día
inicio = 0
fin = 23

# Crear una matriz para registrar el uso de los cargadores en cada hora
charger_usage = np.zeros((num_chargers, T))

# Llenar la matriz de uso con los valores del modelo optimizado
for i in range(len(EV_data)):  # Para cada EV
    for j in range(inicio, fin):  # Para cada hora
        for r in charging_rates:  # Para cada tasa de carga
            if k[i, j, r].X == 1:  # Si el EV se está cargando en esa hora con esa tasa
                charger_usage[i % num_chargers, j] = 1  # Registrar el uso del cargador

# Crear gráfico de barras de número de cargadores en uso por hora
chargers_in_use_per_hour = np.sum(charger_usage, axis=0)  # Suma por columna (hora)

fig, ax = plt.subplots(figsize=(10, 6))

# Gráfico de barras
ax.bar(range(T), chargers_in_use_per_hour, color='blue')

# Etiquetas y formato
ax.set_xlabel('Time (Hour)')
ax.set_ylabel('Chargers in Use')
ax.set_title('Hourly Utilization of Chargers – MILP Optimization Model')
ax.set_xticks(range(T))
ax.set_ylim(0, 30) 

plt.tight_layout()
plt.show()



#-----------------------------------------------------------
# Calcular el total de energía usada en cada hora basándote en los resultados del modelo optimizado
energy_used_per_hour = np.zeros(T)

# Llenar el array de energía usada por hora con los valores del modelo optimizado
for j in range(inicio, fin):  # Para cada hora
    total_energy = 0
    for i in range(len(EV_data)):  # Para cada EV
        for r in charging_rates:  # Para cada tasa de carga
            if k[i, j, r].X == 1:  # Si el EV está siendo cargado en esa hora
                total_energy += r  # Sumar la tasa de carga
    energy_used_per_hour[j] = total_energy

# Crear el gráfico de barras para el uso de energía por hora
fig, ax = plt.subplots(figsize=(10, 6))

# Dibujar las barras del total de energía usada por hora
ax.bar(range(T), energy_used_per_hour, color='g', label='Consumed Energy (kW)')

# Dibujar la línea punteada a 103 kW como límite de demanda máxima
ax.axhline(y=103, color='r', linestyle='--', label='Maximum Demand Limit (103 kW)')

# Etiquetas y configuraciones
ax.set_xlabel('Time (Hour)')
ax.set_ylabel('Energy (kW)')
ax.set_title('Energy Consumption Compared to MDL – MILP Optimization Model')
ax.set_xticks(range(T))
ax.legend()

# Mostrar el gráfico
plt.tight_layout()
plt.show()
# -------------------------
# PLOT: Distribution of Charging Rates – MILP Optimization Model
# -------------------------

# Define the 3 available charging rates
charging_rates = [12, 15, 19]

# Initialize counters for each rate
cars_per_rate = {rate: 0 for rate in charging_rates}

# Count each EV only once, based on which rate it was assigned
for i in range(len(EV_data)):
    used_rates = set()
    for j in range(inicio, fin):
        for r in charging_rates:
            if k[i, j, r].X == 1:
                used_rates.add(r)
    for r in used_rates:
        cars_per_rate[r] += 1
        break  # count only once per EV

# Prepare data in sorted order
sorted_rates = sorted(charging_rates)
counts = [cars_per_rate[r] for r in sorted_rates]

# Create the plot
fig, ax = plt.subplots(figsize=(8, 6))
ax.bar(sorted_rates, counts, color='b')

# Format axes
ax.set_xticks(sorted_rates)
ax.set_xticklabels([f'{r} kW' for r in sorted_rates])
ax.set_xlabel('Charging Rate (kW)')
ax.set_ylabel('Number of Vehicles')
ax.set_title('Distribution of Assigned Charging Rates – MILP Optimization Model')

plt.tight_layout()
plt.show()



# Verificar si se encontró una solución óptima
if model.status == GRB.OPTIMAL:
    # Imprimir el valor óptimo del objetivo
    print(f'\nValor óptimo: {model.objVal}')
else:
    print('No se encontró una solución óptima.')
    

print("\n Función objetivo calculada manual:")
funcion_obj = ganancias - total_penalty
print(funcion_obj)
print("Ganancias:")
print(ganancias)
print("Penalidad total:")
print(total_penalty)
print("Grado de completitud promedio: ")
print( round(Suma_completitud/len(EV_data),4), "%" )

end_time = time.time()
execution_time = end_time - start_time
print(f"El tiempo de corrida es: {execution_time} segundos")
