import sys
import numpy as np
import time
from .TabuSearch import TSP
from .savingVRP import saving, updateCost
from .dbscan_with_pre_com import NewCluster


# calculateMaxCapRoadMatrix max tonage matrix for cluster
class NewRouting:
    def calculateMaxCapRoadMatrix(maxCapRoadMatrix, customersList):
        newMatrix = list()
        for i in customersList:
            listMaxCapRoad = list()
            for j in customersList:
                if i == j:
                    listMaxCapRoad.append(0)
                else:
                    listMaxCapRoad.append(maxCapRoadMatrix[i, j])
            newMatrix.append(listMaxCapRoad)
        return np.array(newMatrix)


    # Update the index corresponding to the original customer list
    def updateIndexCustomer(nodes, customersList):
        customersList = np.array(customersList)
        customer = customersList[nodes]
        return customer


    # costMatrix, maxCapRoadMatrix is numpy array

    # costMatrix = np.genfromtxt('E:/data_routing/data_01_19032021/cost_matrix.csv', delimiter=',')
    # maxCapRoadMatrix = np.genfromtxt('E:/data_routing/data_01_19032021/max_tonage.csv', delimiter=',')
    # demand = np.genfromtxt('E:/data_routing/data_01_19032021/demand.csv', delimiter=',')
    # vehicle = np.genfromtxt('E:/data_routing/data_01_19032021/vehicle.csv', delimiter=',')
    def main(self, costMatrix, maxCapRoadMatrix, demand, vehicle):
        # costMatrix = np.genfromtxt('E:/data_routing/data_02_17032021/matrix_cost.csv', delimiter=',')
        # maxCapRoadMatrix = np.genfromtxt('E:/data_routing/data_02_17032021/max_tonnage.csv', delimiter=',')
        # demand = np.genfromtxt('E:/data_routing/data_02_17032021/demand.csv', delimiter=',')
        # vehicle = np.genfromtxt('E:/data_routing/data_02_17032021/vehicle.csv', delimiter=',')


        startime = time.process_time()
        eps = 18000
        minSample = 3
        timeRunTabu = 10
        totalCost = 0

        # cost value to prohibit the vehicle from crossing an overloaded road
        costRoadErr = np.max(costMatrix)*len(costMatrix)

        # clustering
        cluster, noise = NewCluster.cluster(costMatrix, eps, minSample)
        lstRerult = list()
        noiseSaving = list()

        for c in cluster:
            print(c[0])
            # print(c[1])

            # max tonage matrix for each cluster
            maxCapRoadMatrixCustomers = NewRouting.calculateMaxCapRoadMatrix(maxCapRoadMatrix, c[0])

            # Saving
            # r, c, v = saving(costMatrix, demand, capacity, maxCapRoadMatrix, customersList)
            route, vehicle, vehicleFixCustomer = saving(c[1], demand[c[0]], vehicle, maxCapRoadMatrixCustomers, c[0])

            print('route: ')
            for key, value in route.items():
                value['totalD'] = demand[value['nodes']].sum()
                print(f'{" " * 8}{key}:{value}')

                # create matrix for each route
                costMatrixForRoute = updateCost(costMatrix, maxCapRoadMatrix, value['nodes'], value['Cap'], costRoadErr)

                # tabu search
                result = TSP.find_way(costMatrixForRoute, timeRunTabu)
                totalCost += result[1]

                # Update index for customers
                shortestPath = NewRouting.updateIndexCustomer(result[0], value['nodes'])

                print(f'{" " * 8}The shortest path: ', shortestPath)
                print(f'{" " * 8}Total cost: ', result[1])

                rout = {
                    'vehicle': value['Cap'],
                    'rout': shortestPath,
                    'capacity': value['totalD']
                }
                lstRerult.append(rout)

                # If the way goes wrong then print costMatrix of route
                if result[1] >= costRoadErr:
                    matrixRoadErr = costMatrixForRoute.tolist()
                    print(" " * 8, matrixRoadErr)
                print(f'{" " * 8}--------------------------')
            for key,value in vehicleFixCustomer.items():
                noiseSaving.append(key)

            print(f'\nThe remaining vehicles: {vehicle}\nThe remaining customers:{vehicleFixCustomer}')

            print("===========================")


        print("List of noise points: ", noise)
        print("Run time: ", time.process_time() - startime)
        print("Total Cost: ", totalCost)
        return lstRerult,noise,noiseSaving


