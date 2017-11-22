#!/usr/bin/python3

# ----------------------------------------------------------------------------- 

import os
import csv
import psycopg2
import pprint
import smtplib
import datetime
import json

# ----------------------------------------------------------------------------- 
# the location of the db credentials.
swosqz   = 'swosqz.csv'
intranet = 'intranet.csv'

# ----------------------------------------------------------------------------- 
# empty list for holding the db credentials.

swosCred = []
intraCred = []

# ----------------------------------------------------------------------------- 
# email fields

SENDNAME = 'SWOSreport'
SENDFROM = 'cbar'
SENDTO = ''
SENDCECS = '@cecs.pdx.edu'
SENDCAT = '@cat.pdx.edu'

# ----------------------------------------------------------------------------- 
# the indecies for the database output.

HOST = 0
DBNAME = 1
USER = 2
PASS = 3

QUIZNAME = 2

MODULETYPE = 3
MODULENAME = 4

ATTEMPTQID = 0
ATTEMPTUID = 1
ATTEMPTSCORE = 2
ATTEMPTTIME = 3

USERUID = 0
USERLAST = 1
USERFIRST = 2
USERUNAME = 3
USERMAIL = 4
USERLOG = 5

QUIZQID = 0

SOURCEMAIL = 2
PASSINGSCORE = 5

DATANAME = 0
DATAPASS = 1
DATAFAIL = 2
DATAAWOL = 3
DATANLOG = 4

passedUsers = 'passedUsers'
failedUsers = 'failedUsers'
awolUsers = 'awolUsers'
noLogUsers = 'noLogUsers'

userGroups = [passedUsers, failedUsers, awolUsers, noLogUsers]

# ----------------------------------------------------------------------------- 
# specific queries for databases

# pull user information from the moodle user table
LastLogin    =   ["userid", "lastname", "firstname", "username", "email", "lastlogin"]
getLastLogin = """select id,lastname,firstname,username,email,lastlogin \
                    from public.mdl_user where email like '%@pdx.edu'"""

# pull all headers from moodle quiz grades
AllAttempts    =    ["quizid","userid","grade","timemodified"]
getAllAttempts =  """select quiz,userid,grade,timemodified from public.mdl_quiz_grades"""

# pull the all quiz info (id, course, name, grade)
QuizInfo    =    ["quizid","course","quizname","grade"]
getQuizInfo =  """select id,course,name,grade from public.mdl_quiz"""

# pull info to be able to get a quiz's passing grade
PassingScore    = ["id", "courseid", "itemtype", "itemmodule", "itemname", "gradepass"]
getPassingScore = """select id,courseid,itemtype,itemmodule,itemname,gradepass from mdl_grade_items;""" 

# pull info for a users department and their source user
Source     = ["last_name", "first_name", "email", "dept", "source"]
getSource  = """select last_name,first_name,email,dept,source from stuwork;"""

# ----------------------------------------------------------------------------- 
# functions
# ----------------------------------------------------------------------------- 

def writeToFile(filename, variable):
    with open('db' + filename + '.csv', 'w') as out:
        writer = csv.writer(out)
        for line in variable:
            writer.writerow(line)

# ----------------------------------------------------------------------------- 

def queryDatabase(credentialFile, query, filename, outputVar):
    
    # variable to store credentials
    cred = []

    # open up the credentials file, pull the first item on each row
    # and save those into the cred variable
    with open(credentialFile, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            cred += row

    # open up a connection with the db described in the cred variable
    conn = psycopg2.connect(host=cred[HOST], dbname=cred[DBNAME], \
                            user=cred[USER], password=cred[PASS])

    # get a cursor for conn
    cur = conn.cursor()

    # execute the given query
    cur.execute(query)

    # fetch all the output of the command
    outputVar += cur.fetchall()
    
    writeToFile(filename, outputVar)

    # close the connection
    conn.close()

# ----------------------------------------------------------------------------- 
# Query all the Databases

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

condenseDict = {}

# for all quizzes (skipping the headerline)...
for quiz in quizData[1:]:

    passingScore = 0.0
    condenseDict[quiz[QUIZNAME]] = {}

    # find the right entry/score, check that the item is a quiz,
    # and has the same name as the current quiz (skip headers)
    for entry in moduleData[1:]:
        if (entry[MODULETYPE] == "quiz" and \
                entry[MODULENAME] == quiz[QUIZNAME]):
            passingScore = entry[PASSINGSCORE]
            break

    condenseDict[quiz[QUIZNAME]]['passingScore'] = float(passingScore)
    condenseDict[quiz[QUIZNAME]]['quizName'] = str(quiz[QUIZNAME]) 
    condenseDict[quiz[QUIZNAME]]['attempts'] = {} 
   
    # for the given attempt (skip Headers)
    for user in loginData[1:]:
       
        # the variable that stores whether a 
        # particular user has had an attempt of not
        found = False

        # set the data variable to contain all user info
        data = [user[USERUID], user[USERLAST], user[USERFIRST], user[USERUNAME], user[USERMAIL]]
        
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
            if (attempt[ATTEMPTUID] == user[USERUID]):
                if (attempt[ATTEMPTQID] == quiz[QUIZQID]):

                    d['attemptScore'] = float(attempt[ATTEMPTSCORE])
                    d['attemptTime']  = attempt[ATTEMPTTIME]
                    
                    found = True
                    
                    # if their score is higher, they go into the first list
                    if (attempt[ATTEMPTSCORE] >= passingScore):
                        userField = passedUsers
                    
                    # else they go into the second list (not yet passed)
                    else:
                        userField = failedUsers

        # if found is false, we need to add them to the other lists
        if (found == False):

            # if the users login time is greater than zero
            # add them to the users that are AWOL (no quiz attempts).
            if (user[USERLOG] > 0):
                userField = awolUsers

            # else they havent gotten on the quizsite
            else:
                userField = noLogUsers

        d['group'] = userField
        condenseDict[quiz[QUIZNAME]]['attempts'][d['uid']] = d 


# ----------------------------------------------------------------------------- 
# Put the users into dictionaries

# create a list of users that where recorded
# as adding someone to the Moodle
sourceUsers = []

for source in sourceData[1:]:
    if source[4] not in sourceUsers:
        sourceUsers += [source[4]]

# ----------------------------------------------------------------------------- 

# {'quiz': {'pcore': 17, 'attempts': {'name':ricky, 'score':18}}}
# {'whoadd', {'quiz': thing, {'passed': {'name': ricky,}, 'failed':{}, 'awol':{}, ...}}}

outputDict = {}

for user in sourceData[1:]:
    outputDict[user[4]] = {}
    for quiz in condenseDict:
        outputDict[user[4]][quiz] = {}
        outputDict[user[4]][quiz]['passingScore'] = condenseDict[quiz]['passingScore'] 
        for userGroup in userGroups:
            outputDict[user[4]][quiz][userGroup] = {}


for user in sourceData[1:]:
    for quiz in condenseDict:
        for uid in condenseDict[quiz]['attempts']:
            if (user[2] == condenseDict[quiz]['attempts'][uid]['email']):  
                for userGroup in userGroups: 
                    if (condenseDict[quiz]['attempts'][uid]['group'] == userGroup):
                        outputDict[user[4]][quiz][userGroup][uid] = condenseDict[quiz]['attempts'][uid]

# ----------------------------------------------------------------------------- 

with open('output.json', 'w+') as outfile:
    json.dump(outputDict, outfile)

with open('output.json', 'r') as outfile:
    with open('output2.json', 'w+') as outfile2:
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
