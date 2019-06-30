"""
Author: Weld Lucas Cunha
Created on Tue Mar 14 10:42:06 2017

This library provides some useful definitions that will be used by other classes.
"""
#______________________________________________________________________________
#Importing necessary files and classes:
#Basic python classes:
import random
import numpy as np
import pylab
import math

#Plotting related classes:
import matplotlib.pyplot as plt

#______________________________________________________________________________
#Definitions:
    
#------------------------------------------------------------------------------
#That classical first program:
    
def hello_world():
    print("Hello world!")
    
#------------------------------------------------------------------------------    
#Search and sorting definitions:    
    
def linear_search(value,data):
    #This subroutine should receive a single value to be searched in 
    #a list of values defined by the data variable
    #value - single value (string, int of float)
    #data - list  
    #a linear search will be performed
    #The function will return the index of the position where the value 
    #was first found in data.
    #It will return an index just in case an exactly equal value was found
    
    #In case the value is not found "False" will be returned:
    index = []
    #Searching value in data:
    for i in range(len(data)):
        if value == data[i]:
            index = i
            break
    return index
    

def linear_search2(value,data):
    #This subroutine should receive a single value to be searched in 
    #a list of values defined by the data variable
    #value - single value (string, int of float)
    #data - list  
    #a linear search will be performed, the difference is that it will start 
    #searching from the beggining and from the end of data at the same time 
    #towards the middle of the data list
    #The function will return the index of the position where the value 
    #was first found in data. 
    #It will return an index just in case an exactly equal value was found
    
    #In case the value is not found "False" will be returned:
    index = []
    #Searching value in data:
    for i in range(int(len(data)/2)+1):
        if value == data[i]:
            index = i
            break
        elif value == data[len(data) -1 - i] and (len(data) -1 - i)>i:
            index = len(data) -1 - i
            break
    return index    
    

def bisec_search(value,data):
    #This subroutine should receive a single value to be searched in a set of 
    #values defined by the data variable
    #value - int or float
    #data - list of ints and/or floats 
    #data has to be sorted in increasing order
    #The function will return the index of the closest value found in data.
    
    index = []
    if data == []:
        return False
    elif len(data) == 1:
        return 0
    else: 
        found = False
        min_ = 0
        max_ = len(data)-1
        while found == False:
            half = int((max_ + min_)/2)
           #The exact value was found:
            if data[half]==value:
                found = True
                index = half
            #The closest value was found:
            elif half == min_:
                val_1 = data[min_]
                val_2 = data[min_+1]
                if abs(val_1 - value)<abs(val_2 - value):
                    index = min_
                else:
                    index = min_+1
                found = True
            #Re-dividing the set of data and trying again:
            elif data[half]>value:
                max_ = half
            elif data[half]<value:
                min_ = half
    return index

    
def bubble_sort(array,order=0):
    #This subroutine performs a buble sort algorithm.
    #array must be a list of floats or ints
    #order must be an int or float, recommended values: 1 and -1
    #for order >=0 the array will be sorted in increasing order
    #for order <0 the array will be sorted in decreasing order 
    
    #Sorting in increasing order 
    if order>=0:    
        swap = False
        while not swap:
            swap = True
            for j in range(1, len(array)):
                if array[j-1] > array[j]:
                    swap = False
                    temp = array[j]
                    array[j] = array[j-1]
                    array[j-1] = temp    
    #Sorting in decreasing order 
    else: 
        swap = False
        while not swap:
            swap = True
            for j in range(1, len(array)):
                if array[j-1] < array[j]:
                    swap = False
                    temp = array[j]
                    array[j] = array[j-1]
                    array[j-1] = temp  
    return array
    

def sort_by(data1,data2):
    #This subroutine sorts the first set of data in increasing order and the 
    #second according to the first data.
    
    raw_data1 = data1[:]
    raw_data2 = data2[:]
    #Sorting the distances:            
    data1.sort()
    data2 = list()
    for val in data1:
        i=0
        while i<len(raw_data1):
            if raw_data1[i]==val:
                data2.append(raw_data2[i])
                raw_data1 = raw_data1[0:i]+raw_data1[i+1:]
                raw_data2 = raw_data2[0:i]+raw_data2[i+1:]
                break
            i+=1        
    return (data1,data2)


#------------------------------------------------------------------------------
#Miscelaneous:

def get_numvalues(string_vals):
    #This subroutine identifies all the numeric values in a string and returns
    #them as a list:
        
    num_chars = '.0123456789'
#    num_sgnals = ['+','-']
    num_vals = []
    each_num = ''
    exp_found = False
    exp_value = ''
    exp_signal = '+'    #standard exp signal
    for char in string_vals:
        if char in num_chars and exp_found == False:
            each_num += char
        elif char in num_chars and exp_found == True:
            exp_value += char           
        elif char=='e':
            exp_found = True            
        elif exp_found == False and each_num != '':
            num_vals.append(float(each_num))
            each_num = '' 
        elif exp_found == True and each_num != '' and exp_value != '':
            if exp_signal == '-':
                exp_value = -float(exp_value)
            else:
                exp_value = float(exp_value)
            num_vals.append(float(each_num)*(10**exp_value))
            exp_found = False
            each_num = '' 
            exp_value = ''
            exp_signal = '+' 
        elif exp_found == True and each_num != '' and exp_value == '' and char=='+':
            exp_signal = '+'
        elif exp_found == True and each_num != '' and exp_value == '' and char=='-':
            exp_signal = '-'
    return num_vals


#def get_numvalues(string_vals):
#    #This subroutine identifies all the numeric values in a string and returns
#    #them as a list:
#        
#    num_chars = '.0123456789'
##    num_sgnals = ['+','-']
#    num_vals = []
#    each_num = ''
#    exp_found = False
#    exp_value = ''
#    exp_signal = '+'    #standard exp signal
#    for i in range(len(string_vals)):
#        if string_vals[i] in num_chars and exp_found == False:
#            each_num += string_vals[i]
#        elif string_vals[i] in num_chars and exp_found == True:
#            exp_value += string_vals[i]            
#        elif string_vals[i]=='e':
#            exp_found = True            
#        elif exp_found == False and each_num != '':
#            num_vals.append(float(each_num))
#            each_num = '' 
#        elif exp_found == True and each_num != '' and exp_value != '':
#            if exp_signal == '-':
#                exp_value = -float(exp_value)
#            else:
#                exp_value = float(exp_value)
#            num_vals.append(float(each_num)**exp_value)
#            exp_found = False
#            each_num = '' 
#            exp_value = ''
#            exp_signal = '+' 
#        elif exp_found == True and each_num != '' and exp_value == '' and string_vals[i]=='+':
#            exp_signal = '+'
#        elif exp_found == True and each_num != '' and exp_value == '' and string_vals[i]=='-':
#            exp_signal = '-'
#    return num_vals


def get_numval(string_vals):
    #This subroutine gets all the numeric values in a string with other elements
    #and return them as a number in string form:
        
    num_chars = '.0123456789'
    each_num = ''
    for i in range(len(string_vals)):
        if string_vals[i] in num_chars:
            each_num += string_vals[i]
    if each_num == '':
        each_num = None
    return each_num

    
def dot2comma(dot_number):
    #This subroutine must receive a number and in case the decimal devision is 
    #made with dot, it will be changed to comma.
    #dot_number - int,float,str
    #comma_number - str 
    
    comma_number = ''
    #Passing the dot_number to string:
    dot_number = str(dot_number)
    if type(dot_number)==int:
        comma_number = dot_number + ',0'
    else:
        for i in range(len(dot_number)):
            if dot_number[i]=='.':
                char=','
            else:
                char = dot_number[i]  
            comma_number+=char
        #In case the number was sent as an int string 
        if dot_number == comma_number and ',' not in comma_number:
            comma_number+=',0'
    return comma_number


def dot2comma_list(dot_number_list):
    #This subroutine must receive a number and in case the decimal devision is 
    #made with dot, it will be changed to comma.
    #dot_number - int,float,str
    #comma_number - str 
    
    comma_number_list = list()
    for dot_number in dot_number_list:  
        comma_number = ''
        #Passing the dot_number to string:
        dot_number = str(dot_number)
        if type(dot_number)==int:
            comma_number = dot_number + ',0'
        else:
            for i in range(len(dot_number)):
                if dot_number[i]=='.':
                    char=','
                else:
                    char = dot_number[i]  
                comma_number+=char
            #In case the number was sent as an int string 
            if dot_number == comma_number and ',' not in comma_number:
                comma_number+=',0'
        comma_number_list.append(comma_number)
    return comma_number_list
        
        
def generate_randcolors(self,n):
    #This subroutine generates and Nx3 random number list of RGB colors:
        
    line_colors = []    
    for i in range(n):
        line_colors.append([random.randint(0,1000)/1000,random.randint(0,1000)/1000,random.randint(0,1000)/1000])
    return line_colors        
        

def split_data(orig_data,Ts):
    #This subroutine splits the orig_data in x (=len(Ts)+1) parts, 
    #where the parts division marks are given in Ts.
    
    N = len(orig_data)
    if Ts==[]:
        return orig_data
    else:
        Ts_mark = 0
        data_parts = []
        part = []
        for i in range(N):
            part.append(orig_data[i])
            if Ts_mark<len(Ts) and (i+1)==Ts[Ts_mark]:
                Ts_mark+=1
                data_parts.append(part)
                part = []
        data_parts.append(part)
        return data_parts


def split_intervals(orig_data):
    #This subroutine splits the orig_data with N elements in N-1 intervals.

    N = len(orig_data)    
    data_parts = []
    part = []
    for i in range(N-1):
        part = (orig_data[i],orig_data[i+1])
        data_parts.append(part)
    return data_parts


def split_intervals_norepeat(orig_data,orig_data2):
    #This subroutine splits the orig_data with N elements in N-1 intervals.

    N = len(orig_data)
    data_parts = list()
    data_parts2 = list()
    repeat_found = False
    temp_save = None
    for i in range(N-1):
        if orig_data[i]!=orig_data[i+1] and repeat_found == False:
            data_parts.append((orig_data[i],orig_data[i+1]))
            data_parts2.append((orig_data2[i],orig_data2[i+1]))
        elif orig_data[i]==orig_data[i+1] and repeat_found == False:
            temp_save=orig_data2[i]
            repeat_found = True
        elif orig_data[i]!=orig_data[i+1] and repeat_found == True:
            data_parts.append((orig_data[i],orig_data[i+1]))
            data_parts2.append((temp_save,orig_data2[i+1]))
            repeat_found = False
#        else: 
#            print(orig_data[i],orig_data[i+1])
    return (data_parts,data_parts2)  


def del_repeated(array):
    #This subroutine receives an array with N numbers and returns another array 
    #with the same numbers but eliminating the repeated ones.
    
    #Creating a new array:
    new_array = list()
    #Getting only one element from each:
    for number in array:
        if number not in new_array:
            new_array.append(number)
    return new_array


#------------------------------------------------------------------------------
#Statistics:
    
def MeanSquareError(data, predicted):
    #This subroutine calculates the accumulated mean-square error.
    
    error = 0.0
    for i in range(len(data)):
        error += (data[i] - predicted[i])**2
    return error


def aveMeanSquareError(data, predicted):
    #This subroutine calculates the average mean-square error.
    
    error = 0.0
    for i in range(len(data)):
        error += (data[i] - predicted[i])**2
    return error/len(data)


def r_squared(y, estimated):
    """
     Calculate the R-squared, or coefficient of determination, error term.
    Args:
        y: list with length N, representing the y-coords of N sample points
        estimated: a list of values estimated by the regression model
    Returns:
        a float for the R-squared error term
    """
    
    ysum = 0
    N = len(y)
    for i in range(N):
        ysum+=y[i]
    mean = ysum/N
    var_model=0
    var_orig=0
    for i in range(N):
        var_model+=(y[i] - estimated[i])**2
        var_orig+=(y[i] - mean)**2
    #In case there is no variation in the original data:
    if var_orig==0:
        var_orig = 1e-6
        
    return 1 - (var_model/var_orig)


def poliregression_fit(orig_vals,the_title):
    #This subroutine creates a polynomial regression model.
    
    n_parts = len(orig_vals[0])-1
    x_data_parts = split_data(orig_vals[0],n_parts)
    y_data_parts = split_data(orig_vals[1],n_parts)
    
    best_models = [[] for x in range(n_parts)]
    for i in range(n_parts):
        j = 0
        R2 = -math.inf        
        while R2<0.9999:
            j+=1
            model = np.polyfit(x_data_parts[i], y_data_parts[i], j)
            estYVals = pylab.polyval(model, x_data_parts[i])
            R2_new = r_squared(y_data_parts[i], estYVals)
            if R2_new>R2:
                R2 = R2_new
        best_models[i] = [model,list(estYVals),R2,j]

#    #Plotting the results:
#    plt.figure('Polyfit test')    
#    plt.clf()
#    plt.plot(orig_vals[0], orig_vals[1],'ko',label = 'Orig. values', linewidth = 1.0)
#    for i in range(n_parts):
#        plt.plot(x_data_parts[i],best_models[i][1],label = 'ord:'+str(best_models[i][-1])+', R2 = '+str(round(best_models[i][-2],4)), linewidth = 2.0)
#    plt.title(the_title+' Time-currente plot')
#    plt.xlabel('Current [A]')
#    plt.ylabel('Time [ms]')
#    plt.yscale('log')
#    plt.xscale('log')
#    plt.grid(True)
#    #plt.legend(loc='upper right')
#    #plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.19),fancybox=True, shadow=False, ncol=3)
#    plt.show()
#    plt.close('all')
    
    return [x_data_parts,best_models]


def poliregression_fit2(orig_vals,the_title):
    #This subroutine creates a polynomial regression model.
    
    n_parts = len(orig_vals[0])-1
    x_data_parts = split_intervals(orig_vals[0])
    y_data_parts = split_intervals(orig_vals[1])
    
    best_models = [[] for x in range(n_parts)]
    for i in range(n_parts):
        j = 0
        R2 = -math.inf        
        while R2<0.9999:
            j+=1
            model = np.polyfit(x_data_parts[i], y_data_parts[i], j)
            estYVals = pylab.polyval(model, x_data_parts[i])
            R2_new = r_squared(y_data_parts[i], estYVals)
            if R2_new>R2:
                R2 = R2_new
        best_models[i] = [model,list(estYVals),R2,j]

#    #Plotting the results:
#    plt.close('Polyfit test - '+the_title)    
#    plt.figure('Polyfit test - '+the_title)    
#    plt.clf()
#    plt.plot(orig_vals[0], orig_vals[1],'ko',label = 'Orig. values', linewidth = 1.0)
#    for i in range(n_parts):
#        plt.plot(x_data_parts[i],best_models[i][1],label = 'ord:'+str(best_models[i][-1])+', R2 = '+str(round(best_models[i][-2],4)), linewidth = 2.0)
#    plt.title(the_title+' probability plot')
#    if the_title == 'CSID_min':
#        plt.xlabel('Time [min]')
#    elif the_title == 'CSID_hr':
#        plt.xlabel('Time [hr]')
#    else:
#        plt.xlabel('Time [ms]')            
#    plt.ylabel('Probability')
#    plt.grid(True)
#    #plt.legend(loc='upper right')
#    plt.show()   

    return [x_data_parts,best_models]


#______________________________________________________________________________        
        