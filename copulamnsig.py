#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#******************************************************************************
#* 
#* Copyright (C) 2015  Kiran Karra <kiran.karra@gmail.com>
#*
#* This program is free software: you can redistribute it and/or modify
#* it under the terms of the GNU General Public License as published by
#* the Free Software Foundation, either version 3 of the License, or
#* (at your option) any later version.
#*
#* This program is distributed in the hope that it will be useful,
#* but WITHOUT ANY WARRANTY; without even the implied warranty of
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#* GNU General Public License for more details.
#*
#* You should have received a copy of the GNU General Public License
#* along with this program.  If not, see <http://www.gnu.org/licenses/>.
#******************************************************************************

import math
import numpy as np

from cvolume import cvolume
import multivariate_stats

from ecdf import probability_integral_transform
from scipy.stats import entropy

def copulamnsig(family, K, *args):
    """
    Computes the copula multinomial signature as described in the paper
    "Highly Efficient Learning of Mixed Copula Networks" for a specified 
    copula family.  Essentially, it breaks up the unit grid into a K x K boxes, 
    and computes the probability of a sample from that copula pdf falling in 
    that grid.  This is then aggregated into a multinomial probability 
    distribution.  This so called "multinomial" signature of a copula is then 
    used to efficiently determine the structure of the Bayesian network, as well
    as the copula which would describe the dependency between the nodes.
    
    The grid over the unit cube is numbered as follows, for a 4 x 4 grid
      ___________________
      | 4 | 8 | 12 | 16 | 
      |---|---|----|----| 
      | 3 | 7 | 11 | 15 |
      |-----------------|
      | 2 | 6 | 10 | 14 |
      |-----------------|
      | 1 | 5 |  9 | 13 |
      |___|___|____|____|
    
    Currently, this computes the multinomial signature for a specified copula
    family of 2 dimensions.  It would be nice to expand this to multiple
    dimensions, and we can use the general formula for C-volume
    
      family - the copula type, must be:
        'Gaussian'
        'T'
        'Clayton'
        'Frank'
        'Gumbel'
      args - must be atleast of length 2, for which the first element in args
             is expected to be a string which describes the dependency value
             being provided, must be one of the following:
        'kendall' - means kendall's Tau is being provided
        'spearman' - means spearman's rho is being provided
        'native' - means that the dependency parameter of the copula family
                   itself is being provided directly
            the second argmuent  must be the value of the dependency type 
            provided. For kendall and spearman, a scalar value is expected.  
            For native, if the family type is Frank, Gumbel, or Clayton, then 
            a scalar value is expected, which represents the dependency
            parameter.  If the family type is Gaussian, then a 2 x 2 numpy array
            is expected, which represents the correlation matrix defining the
            Gaussian copula.  If the family is T, then the 2nd argument is the
            2x2 numpy array representing the correlation matrix, and the 3rd
            argument is the degrees of freedom
    """
    coords_list = _makeCoordsList(K)
            
    # mnsig is a list of dictionaries.  The (list index+1) corresponds to the
    # grid of interest in the unit cube.  In the dictionary, the actual lower
    # left coordinates of the box and the upper right coordinates of the box
    # are stored as keys 'u1v1' and 'u2v2', and then the actual value of the 
    # multinomial signature in that grid is stored as 'val'
    #mnsig = []
    
    mnsig = []
    for coord in coords_list:
        # compute the C-volume and store
        u1v1 = coord[0]
        u1v2 = coord[1]
        u2v1 = coord[2]
        u2v2 = coord[3]
        val = cvolume(family, u1v1, u1v2, u2v1, u2v2, *args)

        mnsig.append(val[0])
    
    return mnsig

def empirical_copulamnsig(X, K):
    """
    Computes an empirical copula multinomial signature based on the dataset
    provided by U.  U must be a numpy array of dimensions [M x N], where M is 
    the number of data points in the dataset and, N is the dimensionality of the
    data
    """
    M = X.shape[0]
    N = X.shape[1]
    
    # convert X to U by using the probability integral transform:  F(X) = U
    U = probability_integral_transform(X)
    
    # generate the coordinates so we can then compare and see where each sample
    # falls into in the unit cube
    coords_list = _makeCoordsList(K)
    
    # this will be a list of dictionaries which has all the combinations of the
    # empirical binomial signature 
    esig = []
    
    # for all i < j, compute pairwise bivariate multinomial signature
    for dim1 in range(0,N-1):
        for dim2 in range(dim1+1,N):
            # to compute the pairwise bivariate multinomial signature, what
            # we do is essentially grid as before, and compute a histogram 
            # for each grid .. whcih is our empirical estimate
            # the grid is lay-ed out in the exact same way as described before,
            # so the index of mnsig from copulamnsig and the index of the value
            # generated here will be directly comparable
            #     ___________________
            #     | 4 | 8 | 12 | 16 | 
            #     |---|---|----|----| 
            #     | 3 | 7 | 11 | 15 |
            #     |-----------------|
            #     | 2 | 6 | 10 | 14 |
            #     |-----------------|
            #     | 1 | 5 |  9 | 13 |
            #     |___|___|____|____|
            tmp = {}
            # RV 1 that we are comparing
            tmp['rv1'] = dim1+1
            # RV 2 that we are comparing
            tmp['rv2'] = dim2+1
            # the value for the zone -- initialize to 0
            esig_vec = np.zeros(K*K)
            
            # there is probably a more efficient way to do this than to loop
            # over each value, but this is a first cut at implementing this
            u = U[:,dim1]
            v = U[:,dim2]
            
            for ii in range(0,M):
                # find which zone this specific (u,v) sample falls in
                for jj in range(0,K*K):
                    u1 = coords_list[jj][0][0][0]
                    v1 = coords_list[jj][0][0][1]
                    u2 = coords_list[jj][3][0][0]
                    v2 = coords_list[jj][3][0][1]
                    
                    if(u[ii] >= u1 and u[ii] < u2 and 
                       v[ii] >= v1 and v[ii] < v2):
                        # add one to the zone that it falls into
                        esig_vec[jj] = (esig_vec[jj] + 1.0/M)
                        # process the next pair by kicking out of this loop
                        break
            tmp['esig'] = esig_vec
            
            esig.append(tmp)
        
    return esig

def _makeCoordsList(K):
    eps = np.finfo(float).eps
    u = np.linspace(0+eps, 1-eps, K+1)
    v = np.linspace(0+eps, 1-eps, K+1)
    
    coords_list = []
    for ii in range(0,len(u)-1):
        for jj in range(0,len(v)-1):
            u1 = u[ii]
            u2 = u[ii+1]
            v1 = v[jj]
            v2 = v[jj+1]
            u1v1 = np.array([[u1,v1]])
            u1v2 = np.array([[u1,v2]])
            u2v1 = np.array([[u2,v1]])
            u2v2 = np.array([[u2,v2]])
            x = []
            x.append(u1v1)
            x.append(u1v2)
            x.append(u2v1)
            x.append(u2v2)
            coords_list.append(x)
    
    return coords_list

# the master function, which computes the correct copula family to choose from
# will compare the empirical signatures to the actual signature for refernence
# will do the following:
#  1.) compute the empirical kendall's tau
#  2.) load the precomputed multinomial signature for that kendall's tau
#      for all the copula families
#  3.) minimize the distance metric
def optimalCopulaFamily(X, K=4, family_search=['Gaussian', 'Clayton', 'Gumbel', 'Frank']):
    """
    This function, given a multivariate data set X, computes the best copula family which fits
    the data, using the procedure described in the paper "Highly Efficient Learning of Mixed
    Copula Networks," by Gal Elidan
      
      X - the multivariate dataset for which we desire the copula.  Must be a numpy array of 
          dimension [M x N], where M is the number of data points, and N is the dimensionality
          of the dataset
      K - the square root of the number of grid points (for now, we assume square gridding of the
          unit cube)
      family_search - a list of all the copula families to search.  Currently, what is supported is
          Gaussian, Clayton, Gumbel, and Frank.  As more copula's are added, the default list will
          be expanded.
    """
    # compute the empirical Kendall's Tau
    tau_hat = multivariate_stats.kendalls_tau(X)
    
    # compute empirical multinomial signature
    empirical_mnsig = empirical_copulamnsig(X, K)
    empirical_mnsig = empirical_mnsig[0]['esig']
    # replace any 0 values w/ smallest possible float value
    empirical_mnsig[empirical_mnsig==0] = np.spacing(1)
    
    # compute the multinomial signature for each of the copula families specified
    # and simultaneously compute the kullback leibler divergence between the empirical
    # and the computed, and store that info
    distances = {}
    for family in family_search:
        # because the Clayton and Gumbel Copula's have restrictions for the valid values of
        # Kendall's tau, we do checks here to ensure those restrictions are met, because there
        # will be a certain variance associated with the tau_hat measurement
        
        if(family.lower()=='clayton'):
            # here we add some additional optimizatons as follows.  We know that the Clayton copula
            # captures only positive concordance.  Like any estimator, tau_hat will have some variance
            # associated with it.  Thus, the optimization we make is as follows, if tau_hat is within
            # a configurable amount less than 0, then we will set tau_hat to 0 and continue processing.  
            # However, if tau_hat is greater than that, we theoretically wouldn't have to test against 
            # the Clayton copula model, so we set the KL-divergence to be infinity to exclude 
            # this family from being selected
            if(tau_hat<-0.05):
                distances[family] = np.inf
                continue
            elif(tau_hat>=-0.05 and tau_hat<0):
                tau_hat = 0
            elif(tau_hat>=1):
                tau_hat = 1 - np.spacing(1)     # as close to 1 as possible in our precision
        elif(family.lower()=='gumbel'):
            # here we add some additional optimizatons as follows.  We know that the Gumbel copula
            # captures only positive concordance.  Like any estimator, tau_hat will have some variance
            # associated with it.  Thus, the optimization we make is as follows, if tau_hat is within
            # a configurable amount less than 0, then we will set tau_hat to 0 and continue processing.  
            # However, if tau_hat is greater than that, we theoretically wouldn't have to test against 
            # the Gumbel copula model, so we set the KL-divergence to be infinity to exclude 
            # this family from being selected
            if(tau_hat<-0.05):
                distances[family] = np.inf
                continue
            elif(tau_hat>=-0.05 and tau_hat<0):
                tau_hat = 0
            elif(tau_hat>=1):
                tau_hat = 1 - np.spacing(1)     # as close to 1 as possible in our precision
        # any other copula families with restrictions can go here
        
        mnsig = copulamnsig(family,K,'kendall',tau_hat)
        # replace any 0 values w/ smallest possible float value
        mnsig[mnsig==0] = np.spacing(1)
        
        # compute KL divergence, see
        # http://docs.scipy.org/doc/scipy-dev/reference/generated/scipy.stats.entropy.html
        distances[family] = entropy(mnsig, empirical_mnsig)
        
    # search for the minimum distance, that is the optimal copula family to use
    minDistance = np.inf
    for family, distance in distances.iteritems():
        if distance<minDistance:
            minDistance = distance
            optimalFamily = family
    
    depParams = invcopulastat(optimalFamily, 'kendall', tau_hat)
    
    return (optimalFamily, depParams, tau_hat)

def testHELM(tau, M, N, familyToTest, numMCSims, copulaFamiliesToTest):
    results = {}
    for fam in copulaFamiliesToTest:
        results[fam.lower()] = 0
    
    for ii in range(0,numMCSims):
        # generate samples of the requested copula with tau same as the
        # empirical signature we calculated above
        if(familyToTest.lower()=='gaussian'):
            r = invcopulastat(familyToTest, 'kendall', tau)
            
            # TODO: make the below block of code more efficient :)
            Rho = np.empty((N,N))
            for jj in range(0,N):
                for kk in range(0,N):
                    if(jj==kk):
                        Rho[jj][kk] = 1
                    else:
                        Rho[jj][kk] = r
            
            U = copularnd(familyToTest, M, Rho)
        else:       # assume Clayton, Frank, or Gumbel
            alpha = invcopulastat(familyToTest, 'kendall', tau)
            U = copularnd(familyToTest, M, N, alpha)
        
        lst = []
        for jj in range(0,N):
            if(jj%2==0):
                lst.append(norm.ppf(U[:,jj]))
            else:
                lst.append(expon.ppf(U[:,jj]))
        
        # combine X and Y into the joint distribution w/ the copula
        X = np.vstack(lst)
        X = X.T
            
        ret = optimalCopulaFamily(X, family_search=copulaFamiliesToTest)
        ret_family = ret[0].lower()
        # aggregate results
        results[ret_family] = results[ret_family] + 1.0
        
        # display some progress
        sys.stdout.write("\rComputing " + str(familyToTest) + " Copula (DIM=%d) (tau=%f)-- %d%%" % (N,tau,ii+1))
        sys.stdout.flush()
    
    sys.stdout.write("\r")
    return results

def plotPieChartResults(results, family, title):
    colors = ['yellowgreen', 'gold', 'lightskyblue', 'lightcoral']      # for the pie chart
    # explode the Gaussian portion fo the pychart
    expTup = [0,0,0,0]
    expTup[results.keys().index(family.lower())] = 0.1
    plt.pie(results.values(), explode=expTup, labels=results.keys(),
            colors=colors, autopct='%1.1f%%', shadow=True, startangle=90)
    plt.title(title)
    plt.show()
    

def testHELM_parametric():
    # some tests on the copula multinomial signature
    
    K = 4
    M = 1000
    N = 2
    
    # Monte-Carlo style simulations to test each copula generation
    numMCSims = 100
    # the families to test against and pick optimal copula
    families = ['Gaussian', 'Clayton', 'Gumbel', 'Frank']
        
    resultsAggregate = {}
    family_tauvec_mapping = {}
    for family in families:
        # we do this here b/c some values of tau don't make sense for some families
        # of copula's
        if(family=='Gaussian'):
            tauVec = np.arange(-0.9,0.9,0.05)
        elif(family=='Clayton'):
            tauVec = np.arange(0,0.9,0.05)
        elif(family=='Gumbel'):
            tauVec = np.arange(0,0.9,0.05)
        elif(family=='Frank'):
            tauVec = np.arange(-0.9,0.9,0.05)
        family_tauvec_mapping[family] = tauVec
        
        famResults = {}
        for tau in tauVec:
            results = testHELM(tau, M, N, family, numMCSims, families)
            famResults[tau] = results
        resultsAggregate[family] = famResults

    # plot the parametric results for fun
    for fam in families:
        tauVec = family_tauvec_mapping[fam]
        refGauVec = np.empty(tauVec.shape)
        refFraVec = np.empty(tauVec.shape)
        refClaVec = np.empty(tauVec.shape)
        refGumVec = np.empty(tauVec.shape)
        ii = 0
        for tau in tauVec:
            refGauVec[ii] = resultsAggregate[fam][tau]['gaussian']
            refFraVec[ii] = resultsAggregate[fam][tau]['clayton']
            refClaVec[ii] = resultsAggregate[fam][tau]['gumbel']
            refGumVec[ii] = resultsAggregate[fam][tau]['frank']
            ii = ii + 1
                
        plt.plot(tauVec, refGauVec, 'b.-', label='Gaussian Copula')
        plt.plot(tauVec, refFraVec, 'g.-', label='Clayton Copula')
        plt.plot(tauVec, refClaVec, 'r.-', label='Gumbel Copula')
        plt.plot(tauVec, refGumVec, 'k.-', label='Frank Copula')
        plt.legend()
        plt.title(fam + ' Reference Copula')
        plt.grid()
        plt.xlabel(r"Kendall's $\tau$")
        plt.ylabel('Selection Percentage')
        plt.show()
        
    return resultsAggregate


if __name__=='__main__':
    from copularnd import copularnd
    from invcopulastat import invcopulastat
    from scipy.stats import norm
    from scipy.stats import expon
    import sys
    import matplotlib.pyplot as plt

    # some tests on the copula multinomial signature
    tau = 0.4
    K = 4
    mnsig = copulamnsig('Gumbel',K,'kendall',tau)
    # iterate through mnsig to make sure we add upto 1 as a simple sanity check
    val_total = 0
    for ii in range(0,len(mnsig)):
        val_total = val_total + mnsig[ii]  #['val']
        
    if(np.isclose(val_total, 1.0)):
        print 'CopulaMNSig total probability check passed!'
    else:
        print 'CopulaMNSig total probability check failed!'
    
    
    M = 1000
    N = 2
    
    # Monte-Carlo style simulations to test each copula generation
    numMCSims = 100
    # the families to test against and pick optimal copula
    families = ['Gaussian', 'Clayton', 'Gumbel', 'Frank']
    
    """
    for family in families:
        title = 'Reference Bivariate ' + str(family) + ' Copula - HELM Identification Breakdown'
        results = testHELM(tau, M, N, family, numMCSims, families)
        plotPieChartResults(results, family, title)
    
    N = 3
    for family in families:
        title = 'Reference Bivariate ' + str(family) + ' Copula - HELM Identification Breakdown'
        results = testHELM(tau, M, N, family, numMCSims, families)
        plotPieChartResults(results, family, title)
    """
    resultsAggregate = testHELM_parametric()
    
    
    