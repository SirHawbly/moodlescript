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
# location of the scores csv
scores = '/tmp/scores.csv'

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
# Classes
# ----------------------------------------------------------------------------- 

# encode decimals in json 
# SRC: 
# https://stackoverflow.com/questions/1960516/python-json-serialize-a-decimal-object
class DecimalEncoder(json.JSONEncoder):
    def _iterencode(self, o, markers=None):
        if isinstance(o, decimal.Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(o) for o in [o])
        return super(DecimalEncoder, self)._iterencode(o, markers)

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
# Email Departments about User Progress

def sendEmail(dictionary, key):
    
    today = datetime.datetime.now()
    
    #{'user', ['user', [passed], [failed], ...]} 
    SENDTO = str((dictionary[key])[0][0])

    sender = SENDTO + SENDCECS
    receivers = [SENDFROM+SENDCECS]
    message = """From: {1} <{0}>
To: {2} <{3}>
Subject: Automated SWOS Status Report for {1}""".format(sender, SENDTO, SENDNAME, receivers[0])

    message += "\nThis is an automated status report for the Student Worker Onboarding System (SWOS)."
    message += "\nThis email was generated on {0:%Y-%m-%d at %I:%M %p}".format(today)

    message += "\nIf you need any help please contact support@cat.pdx.edu.\n"

    title = ["\nPassed (recieved a passing score)",\
            "Failed (has yet to pass the quiz)",\
            "Awol (has not tried the quiz yet)",\
            "No Login Data (has not logged into SWOS)"]

    headers = "\tQuizName, UserId, LastName, FirstName, UserName, Email, AttemptScore, PassingScore\n\
\t------------------------------------------------------------------------------------------------------------------------------------"

    # print out all user attempts and headers
    for entry,ind in zip((dictionary[key])[1:], range(0,4)):
    
        message += title[ind] + '\n' + headers + '\n'
        
        length = len(message)
        
        # go through all the attempts and decide
        # whether they can be output into the email
        for j in entry:
           
            # variable to see if an entry is to be added
            unique = True
           
            # check to see if the user is in the list
            # of users already reported passing
            with open("passedUsers.csv", 'a+') as inp:
                reader = csv.reader(inp, delimiter=',')
                for line in reader:
                   
                    # test if both emails are equal
                    # both email locations are at 5
                    if (j[5] == line[5]):
                        unique = False

                if (unique):
                    message += '\t' + str(j) + '\n'

            # if this is the people that passed the quiz save 
            # all of their entries so they are never spammed again
            if (ind == 0 and unique == True): 
                with open("passedUsers.csv", 'a+') as outp:
                    writer = csv.writer(outp, delimiter=',')
                    writer.writerow(j)
        
        # if nothing was added to the message, print "none"
        if (length == len(message)):
            message += '\tNONE\n'

        message += '\n\n'

    # send the email, if it fails catch the exception
    try:
        smtpObj = smtplib.SMTP('localhost')
        smtpObj.sendmail(sender, receivers, message)         
        print ("Successfully sent email")
    except SMTPException:
        print ("Error: unable to send email")

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

condenseData = []

#NEW
condenseDict = {}

# for all quizzes (skipping the headerline)...
for quiz in quizData[1:]:

    quizData     = []
    passingScore = 0.0

    #NEW
    condenseDict[quiz[QUIZNAME]] = {}

    # find the right entry/score, check that the item is a quiz,
    # and has the same name as the current quiz (skip headers)
    for entry in moduleData[1:]:
        if (entry[MODULETYPE] == "quiz" and \
                entry[MODULENAME] == quiz[QUIZNAME]):
            passingScore = entry[PASSINGSCORE]
            break

    #NEW
    condenseDict[quiz[QUIZNAME]]['passingScore'] = float(passingScore)
    condenseDict[quiz[QUIZNAME]]['quizName'] = str(quiz[QUIZNAME]) 

    # create an item for the quiz, containing who has passed, 
    # failed, not attempted, and not logged in.
    quizData += [quiz[QUIZNAME], [], [], [], []]
   
    # for the given attempt (skip Headers)
    for user in loginData[1:]:
       
        # the variable that stores whether a 
        # particular user has had an attempt of not
        found = False

        # set the data variable to contain all user info
        data = [user[USERUID], user[USERLAST], user[USERFIRST], user[USERUNAME], user[USERMAIL]]
        
        #NEW
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

                    #print(user, attempt)

                    #NEW
                    d['attemptScore'] = float(attempt[ATTEMPTSCORE])
                    d['attemptTime']  = attempt[ATTEMPTTIME]
                    
                    found = True
                    
                    # if their score is higher, they go into the first list
                    if (attempt[ATTEMPTSCORE] >= passingScore):
                        quizData[DATAPASS] += [data + [int(attempt[ATTEMPTSCORE])] + [int(passingScore)],]
                        userField = passedUsers
                    
                    # else they go into the second list (not yet passed)
                    else:
                        quizData[DATAFAIL] += [data + [int(attempt[ATTEMPTSCORE])] + [int(passingScore)],]
                        userField = failedUsers

        # if found is false, we need to add them to the other lists
        if (found == False):

            # if the users login time is greater than zero
            # add them to the users that are AWOL (no quiz attempts).
            if (user[USERLOG] > 0):
                quizData[DATAAWOL] += [data]
                userField = awolUsers

            # else they havent gotten on the quizsite
            else:
                quizData[DATANLOG] += [data]
                userField = noLogUsers

        #NEW
        d['userGroup'] = userField
        condenseDict[quiz[QUIZNAME]][d['uid']] = d 

    # add the quiz data to the list for all attempts
    condenseData += [quizData]

#NEW 
# print the lengths of the lists
"""
for quiz in condenseDict:
    for userGroup in userGroups:
        print(len(condenseDict[quiz][userGroup]))
"""
"""
for quiz in condenseData:
    for i in range(1,5):
        print("\t" + str(len(quiz[i])))
"""
# ----------------------------------------------------------------------------- 
# Print out the results of the queries 

"""
print(condenseData)

for quiz in condenseData:

    print(str(quiz[0]))

    print("\tPassed:\n\t"           + str(quiz[1]))
    print("\tFailed:\n\t"           + str(quiz[2]))
    print("\tNot Attempted:\n\t"    + str(quiz[3]))
    print("\tNoLogin:\n\t"          + str(quiz[4]))

print("\n\n")
"""

# ----------------------------------------------------------------------------- 
# Put the users into dictionaries

# create a list of users that where recorded
# as adding someone to the Moodle
sourceUsers = []
OutputData = {}

for source in sourceData[1:]:
    if source[4] not in sourceUsers:
        sourceUsers += [source[4]]

for source in sourceData[1:]:
    for quiz in condenseDict:
        for entry in condenseDict[quiz]:
            if (['email'] == source[2]):
                OutputData[source[4]] = entry

# print(sourceUsers)

for source in sourceUsers:
    OutputData[source] = [[source], [],[],[],[]]

# print(OutputData)

outputDict = {}

# ----------------------------------------------------------------------------- 

# for all the people that added people, add people they added 
# to a dictionary in the same format as the condensed data
for user in sourceData[1:]:    
    for quiz in condenseData:

        # for the passed, failed, awol, and nolog lists in quiz...
        for i in range(1,4):
            for attempt in quiz[i]:
                # if the user was added by someone on the list...
                if (user[2] == attempt[4]):

                    # put that data into the the output data in the right list
                    (OutputData[user[4]])[i] += [[quiz[0]] + attempt]


#NEW
for user in sourceData[1:]:
    for quiz in condenseDict:
        
        # for the added by field
        outputDict[user[4]] = {}
        
        for attempt in condenseDict[quiz]:
            
            outputDict[user[4]][quiz] = {}
            
            for userGroup in userGroups:

                outputDict[user[4]][quiz][userGroup] = [[attempt],]

# ----------------------------------------------------------------------------- 
# Print the Dictionary

# print all of the entries in the dictionary (with keys)
# for key,entry in OutputData.items():
    # pprint.pprint(str(key) + "\n" + str(entry))

# ----------------------------------------------------------------------------- 
# Email all User Sources

#for i in OutputData:
    #sendEmail(OutputData, i)

#print(json.dumps(condenseDict))

print(condenseDict)

for quiz in condenseDict:
    for attempt in condenseDict[quiz]:
        print (attempt)

#print(json.dumps(outputDict))

# ----------------------------------------------------------------------------- 
