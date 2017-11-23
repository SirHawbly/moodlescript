#!/usr/bin/python3

# ----------------------------------------------------------------------------- 

import os
import sys 
import psycopg2
import json

from moodleVariables import * 
from moodleFunctions import *

# ----------------------------------------------------------------------------- 
# the location of the db credentials.
swosqz   = 'swosqz.csv'
intranet = 'intranet.csv'

# ----------------------------------------------------------------------------- 
# empty list for holding the db credentials.

swosCred = []
intraCred = []

# ----------------------------------------------------------------------------- 
# Check to see that you are master

# if we arent the master, 
# just kill the script
if (os.system("amimaster") != 0):
    sys.exit(0)
    
# ----------------------------------------------------------------------------- 
# Query all the Databases

# store all of the headers, and
# query/store database output

# Get Login Data from Swosqz
loginData = [LastLogin,]
queryDatabase(swosqz, getLastLogin, "lastLogin", loginData)

# Get Score Data from Swosqz
attemptData = [AllAttempts,]
queryDatabase(swosqz, getAllAttempts, "attemptInfo", attemptData)

# Get QuizId, Name from Swosqz
quizData = [QuizInfo,]
queryDatabase(swosqz, getQuizInfo, "quizInfo", quizData)

# Get passing score from Swosqz
moduleData = [PassingScore,]
queryDatabase(swosqz, getPassingScore, "moduleInfo", moduleData)

# Get dept+source from Intranet
sourceData = [Source,]
queryDatabase(intranet, getSource, "sourceInfo", sourceData)

# ----------------------------------------------------------------------------- 
# Generate Student Output

# create a dictionary to hold 
# all the user data from moodle
condenseDict = {}

# for all quizzes (skipping the headerline)...
for quiz in quizData[1:]:

    # create a subdictionary for the quiz,  
    # and a passing score variable
    condenseDict[quiz[QUIZNAME]] = {}
    passingScore = 0.0

    # find the right entry/score, check that the item is a quiz,
    # and has the same name as the current quiz (skip headers)
    for entry in moduleData[1:]:
        if (entry[MODULETYPE] == "quiz" and \
                entry[MODULENAME] == quiz[QUIZNAME]):
            passingScore = entry[PASSINGSCORE]
            break

    # copy over the passing score and quiz name,
    # then create a subdictionary for attempts
    condenseDict[quiz[QUIZNAME]]['passingScore'] = float(passingScore)
    condenseDict[quiz[QUIZNAME]]['quizName'] = str(quiz[QUIZNAME]) 
    condenseDict[quiz[QUIZNAME]]['attempts'] = {} 
   
    # for the given attempt (skip Headers)
    for user in loginData[1:]:
       
        # create a variable to see if a 
        # user has had an attempt or not
        found = False
       
        # set d to contain all user info that is
        # common across all userGroups
        d = {'uid': user[USERUID], 
            'uname': user[USERUNAME], 
            'lastname': user[USERLAST], 
            'firstname': user[USERFIRST], 
            'email': user[USERMAIL],
            'lastlog': float(user[USERLOG])}
        
        # for all attempts (skipping the headerline) 
        # check to see that they are on the current quiz,
        # then check their score with the passingScore
        for attempt in attemptData[1:]:
            if ((attempt[ATTEMPTUID] == user[USERUID]) and\
                (attempt[ATTEMPTQID] == quiz[QUIZQID])):

                    
                d['attemptScore'] = float(attempt[ATTEMPTSCORE])
                d['attemptTime']  = attempt[ATTEMPTTIME]
                    
                found = True
                    
                # if their score is higher, they go into the passed section
                if (attempt[ATTEMPTSCORE] >= passingScore):
                    userField = passedUsers
                    
                # else they go into the failed section (not yet passed)
                else:
                    userField = failedUsers

        # if found is false, we need to 
        # add them to the other lists
        if (found == False):

            # if the users login time is greater than 
            # zero add them to the users that are AWOL 
            # (there have been no quiz attempts).
            if (user[USERLOG] > 0):
                userField = awolUsers

            # else they havent gotten on the quizsite
            else:
                userField = noLogUsers

        # write down the group they are in, 
        # and add them to the dictionary
        d['group'] = userField
        condenseDict[quiz[QUIZNAME]]['attempts'][d['uid']] = d 


# ----------------------------------------------------------------------------- 
# Put the users into dictionaries

# create a list of users that where recorded
# as adding someone to Moodle using sourceData
sourceUsers = []

# for all people in source data get the adder, if
# the adder is not in sourceUsers list add them.
for source in sourceData[1:]:
    if source[4] not in sourceUsers:
        sourceUsers += [source[4]]

# ----------------------------------------------------------------------------- 
# Create the output Dictionary

# set up the output dictionary, with dictionaries for 
# all users that added people, per quiz and per userGroup.

outputDict = {}

for user in sourceData[1:]:

    # create a dictionary per user
    outputDict[user[4]] = {}
    
    for quiz in condenseDict:
    
        # create a dictionary per user for the quizzes
        outputDict[user[4]][quiz] = {}
        # copy over the passing score
        outputDict[user[4]][quiz]['passingScore'] = condenseDict[quiz]['passingScore'] 
       
        # add slots for all userGroups per quiz per user
        for userGroup in userGroups:
            outputDict[user[4]][quiz][userGroup] = {}

# ----------------------------------------------------------------------------- 
# Add users into the output Dictionary

# add users to the outputDict according to their emails
# (the source file ties user name of adder, to new acct.)
for user in sourceData[1:]:
    for quiz in condenseDict:
        for uid in condenseDict[quiz]['attempts']:
           
            # find the user in the source data via their emails
            if (user[SOURCEMAIL] == condenseDict[quiz]['attempts'][uid]['email']):  
       
                # loop through the usergroups and 
                # find out where to add the data
                for userGroup in userGroups: 
                    if (condenseDict[quiz]['attempts'][uid]['group'] == userGroup):
                        outputDict[user[SOURCENAME]][quiz][userGroup][uid] = condenseDict[quiz]['attempts'][uid]

# ----------------------------------------------------------------------------- 

# write the ouput in outputDict 
# to the output.json file
with open('output.json', 'w+') as outfile:
    json.dump(outputDict, outfile)

# ----------------------------------------------------------------------------- 

# write the output again, just make 
# it more human readable
with open('output.json', 'r') as outfile:
    with open('human-output.json', 'w+') as outfile2:
        for line in outfile:
            indent = 0
            for char in line:
                
                temp = ''
               
                if (char == '{'):
                    temp += '\n'
                    indent += 1
                    for i in range(indent):
                        temp += '\t'

                if (char == ','):
                    temp += '\n'
                    for i in range(indent):
                        temp += '\t'

                if (char == '}'):
                    indent -= 1

                outfile2.write(char + temp)

# ----------------------------------------------------------------------------- 

# return out of python
sys.exit(0)

# ----------------------------------------------------------------------------- 
