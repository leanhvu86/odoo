import sys
import numpy as np
import time
from .TabuSearch import TSP
from .savingVRP import saving, updateCost
from .dbscan_with_pre_com import Cluster
from sklearn.neighbors import NearestNeighbors
from matplotlib import pyplot as plt


class Routing():
    # calculateMaxCapRoadMatrix max tonage matrix for cluster
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
    # def printResult(distance_matrix):
    #     print('-------------------------------------------------')
    #     #distance_matrix = np.array(costMatrix)
    #     for i in range(len(distance_matrix)):
    #         for j in range(len(distance_matrix[i])):
    #             print(distance_matrix[i][j], end=' ')
    #         print()

    #define eps
    # def findEps(minSample, costMatrix):
    #     distance_matrix = np.array(costMatrix)
    #     lstValue = list()
    #     for i in range(len(distance_matrix)):
    #         for j in range(len(distance_matrix[i])):
    #             distance_matrix[i].sort()
    #
    #     for i in range(len(distance_matrix)):
    #         if len(distance_matrix[i]) <= int(minSample + 1):
    #             lstValue.append(distance_matrix[i][j])
    #         else:
    #             for k in range(minSample + 1):
    #                 if k == 0:
    #                     pass
    #                 else:
    #                     lstValue.append(distance_matrix[i][k])
    #     lstValue = lstValue.sort(lstValue, axis=0)
    #     plt.plot(lstValue)
    #     plt.show()

    def findEps(minSample, matrixData):
        dataset = np.array(matrixData)
        neighbors = NearestNeighbors(n_neighbors=minSample)
        neighbors_fit = neighbors.fit(dataset)
        distances, indices = neighbors_fit.kneighbors(dataset)
        distances = np.sort(distances, axis=0)
        distances = distances[:, 1]
        plt.plot(distances)
        plt.show()

    # costMatrix, maxCapRoadMatrix is numpy array

    # costMatrix = np.genfromtxt('E:/data_routing/data_01_19032021/cost_matrix.csv', delimiter=',')
    # maxCapRoadMatrix = np.genfromtxt('E:/data_routing/data_01_19032021/max_tonage.csv', delimiter=',')
    # demand = np.genfromtxt('E:/data_routing/data_01_19032021/demand.csv', delimiter=',')
    # vehicle = np.genfromtxt('E:/data_routing/data_01_19032021/vehicle.csv', delimiter=',')
    def main(self, costMatrix, maxCapRoadMatrix,demand, vehicle  ):
        # costMatrix = np.genfromtxt('E:/data_routing/data_02_17032021/matrix_cost.csv', delimiter=',')
        # maxCapRoadMatrix = np.genfromtxt('E:/data_routing/data_02_17032021/max_tonnage.csv', delimiter=',')
        # demand = np.genfromtxt('E:/data_routing/data_02_17032021/demand.csv', delimiter=',')
        # vehicle = np.genfromtxt('E:/data_routing/data_02_17032021/vehicle.csv', delimiter=',')
        print(costMatrix)


        startime = time.process_time()
        eps = 15000
        minSample = 2
        unitTime = 10
        totalCost = 0
        Routing.findEps(3,costMatrix)


        # cost value to prohibit the vehicle from crossing an overloaded road
        costRoadErr = np.max(costMatrix)*len(costMatrix)

        # clustering
        cluster, noise = Cluster.cluster(costMatrix, eps, minSample)
        lstRerult = list()
        noiseSaving = list()
        for c in cluster:

            print(c[0])
            # print(c[1])

            # max tonage matrix for each cluster
            maxCapRoadMatrixCustomers = Routing.calculateMaxCapRoadMatrix(maxCapRoadMatrix, c[0])

            # Saving
            # r, c, v = saving(costMatrix, demand, capacity, maxCapRoadMatrix, customersList)
            route, vehicle, vehicleFixCustomer = saving(c[1], demand[c[0]], vehicle, maxCapRoadMatrixCustomers, c[0])
            print(f'route: ')
            for key, value in route.items():
                value['totalD'] = demand[value['nodes']].sum()
                print(f'{" " * 8}{key}:{value}')
               #  print('key: ', key)
               #  print('value: ', value['Cap'])
                # create matrix for each route
                costMatrixForRoute = updateCost(costMatrix, maxCapRoadMatrix, value['nodes'], value['Cap'], costRoadErr)
                timeRunTabu = len(value['nodes']) * unitTime
                # tabu search
                result = TSP.find_way(costMatrixForRoute, timeRunTabu)
                totalCost += result[1]

                # Update index for customers
                shortestPath = Routing.updateIndexCustomer(result[0], value['nodes'])

                print(f'{" " * 8}The shortest path: ', shortestPath)
                print(f'{" " * 8}Total cost: ', result[1])

                # rout = None
                # route['capacity'] = key
                # rout['rout'] = shortestPath
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

            print(f'\nThe remaining vehicles: {vehicle}\nThe remaining customers:{vehicleFixCustomer}')
            for key,value in vehicleFixCustomer.items():
                noiseSaving.append(key)
            print("===========================")

        print("Run time: ", time.process_time() - startime)
        print("Total Cost: ", totalCost)
        return lstRerult,noise,noiseSaving

