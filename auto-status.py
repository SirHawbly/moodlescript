#!/usr/bin/python

# ----------------------------------------------------------------------------- 

import csv
import psycopg2
import pprint

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
# the indecies for the database output.

HOST = 0
DBNAME = 1
USER = 2
PASS = 3

QUIZNAME   = 2

MODULETYPE   = 3
MODULENAME = 4

ATTEMPTQID = 0
ATTEMPTUID = 1
ATTEMPTSCORE = 2

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

# ----------------------------------------------------------------------------- 
# specific queries for databases

# pull user information from the moodle user table
LastLogin    =   ["userid", "lastname", "firstname", "username", "email", "lastlogin"]
getLastLogin = """select id,lastname,firstname,username,email,lastlogin \
                    from public.mdl_user where email like '%@pdx.edu'"""

# pull all headers from moodle quiz grades
AllAttempts    =    ["quizid","userid","grade"]
getAllAttempts =  """select quiz,userid,grade from public.mdl_quiz_grades"""

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

def queryDatabase(credentialFile, query, filename, outputVar):
    
    # variable to store credentials
    cred = []

    # open up the credentials file, pull the first item on each row
    # and save those into the cred variable
    with open(credentialFile, 'rb') as csvfile:
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

    # get a tempfile name to write to
    tempFile = '/tmp/db' + str(filename) + ".csv"

    # output the db entries to tempfile in /tmp
    with open(tempFile, 'w+') as out:
        writer = csv.writer(out, delimiter=',')
        for line in outputVar:
            writer.writerow(line)

    # close the connection
    conn.close()

# ----------------------------------------------------------------------------- 
# Get Login Data from Swosqz

loginData = [LastLogin,]
queryDatabase(swosqz, getLastLogin, "lastLogin", loginData)

# ----------------------------------------------------------------------------- 
# Get Score Data from Swosqz

attemptData = [AllAttempts,]
queryDatabase(swosqz, getAllAttempts, "attemptInfo", attemptData)

# ----------------------------------------------------------------------------- 
# Get QuizId, Name from Swosqz

quizData = [QuizInfo,]
queryDatabase(swosqz, getQuizInfo, "quizInfo", quizData)

# ----------------------------------------------------------------------------- 
# Get passing score from Swosqz

moduleData = [PassingScore,]
queryDatabase(swosqz, getPassingScore, "moduleInfo", moduleData)

# ----------------------------------------------------------------------------- 
# Get dept+source from Intranet

sourceData = [Source,]
queryDatabase(intranet, getSource, "sourceInfo", sourceData)

# ----------------------------------------------------------------------------- 
# Generate Student Output

condenseData = []

# for all quizzes (skipping the headerline)...
for quiz in quizData[1:]:

    quizData     = []
    passingScore = 0.0
    
    # print (quiz[2])

    # print(passingData)

    # find the right entry, check that the item is a quiz,
    # and has the same name as the current quiz (skip header)
    for entry in moduleData[1:]:
        
        # if the item is the same name as the quiz
        # has the same id as the quiz, and is a quiz...
        if (entry[MODULETYPE] == "quiz" and \
                entry[MODULENAME] == quiz[QUIZNAME]):
            
            passingScore = entry[PASSINGSCORE]
            break

    # create an item for the quiz, containing who has passed, 
    # failed, not attempted, and not logged in.
    quizData += [quiz[QUIZNAME], [], [], [], []]
    
    # get the user name, name and email 
    # for the given attempt (skip Headers)
    for user in loginData[1:]:
       
        # the variable that stores whether a 
        # particular user has had an attempt of not
        found = False

        # print(user)

        # set the data variable to contain all user info
        data = [user[USERUID], user[USERLAST], user[USERFIRST], user[USERUNAME], user[USERMAIL]]
        
        # for all attempts (skipping the headerline)...
        for attempt in attemptData[1:]:
   
            # print("attempt = " + str(attempt))

            # check to see if the quiz 
            if (attempt[ATTEMPTUID] == user[USERUID]):

                # if the attempt is the same as the quiz that was taken
                # append it to that quizzes list
                if (attempt[ATTEMPTQID] == quiz[QUIZQID]):
                    
                    # if they have recieved a passing grade        
                    if (attempt[ATTEMPTSCORE] >= passingScore):
                        
                        # enter teh user into the first category
                        quizData[DATAPASS] += [data + [int(attempt[ATTEMPTSCORE])] + [int(passingScore)],]
                        found = True

                    # else add it to the made an attempt
                    else:
                        # enter the user into the second category 
                        # (they havent met the goal)
                        quizData[DATAFAIL] += [data + [int(attempt[ATTEMPTSCORE])] + [int(passingScore)],]
                        found = True

        # if the found variable is false, we didnt find it 
        # attempts, if their last login time was 0, 
        # they havent gotten on the quizsite
        if (found == False):

            # if the users login time is greater than zero
            # add them to the users that are AWOL.
            if (user[USERLOG] > 0):
                quizData[DATAAWOL] += [data]
            else:
                quizData[DATANLOG] += [data]

    # add the quiz data to the entire list of data
    condenseData += [quizData]

# ----------------------------------------------------------------------------- 
# Print out the results to a file 

# get a tempfile name to write to
tempFile = '/tmp/db' + "condenseData" + ".csv"

# output the db entries to tempfile in /tmp
with open(tempFile, 'w+') as out:
    writer = csv.writer(out, delimiter=',')
    for line in condenseData:
        writer.writerow(line)

# ----------------------------------------------------------------------------- 
# Print out the results of the queries 

print(condenseData)

for quiz in condenseData:

    print(str(quiz[0]))

    print("\tPassed:\n\t"           + str(quiz[1]))
    print("\tFailed:\n\t"           + str(quiz[2]))
    print("\tNot Attempted:\n\t"    + str(quiz[3]))
    print("\tNoLogin:\n\t"          + str(quiz[4]))

print("\n\n")

# ----------------------------------------------------------------------------- 
# Put the users into dictionaries

# create a list of users that where recorded
# as adding someone to the Moodle
sourceUsers = []

for source in sourceData[1:]:
    if source[4] not in sourceUsers:
        sourceUsers += [source[4]]

# print(sourceUsers)

OutputData = {}

for source in sourceUsers:
    OutputData[source] = [[source], [],[],[],[]]

# print(OutputData)

# ----------------------------------------------------------------------------- 

"""for all users in the source list, look for all instances of them in the condensed data set, 
append all of those attempts (p/f/a) into the output data directory under the user namd that 
they where added by (use email as the key that ties them together)"""

#Source = ["last_name", "first_name", "email", "dept", "source"]
#data = [user[USERUID], user[USERLAST], user[USERFIRST], user[USERUNAME], user[USERMAIL]]
for user in sourceData[1:]:
    
    for quiz in condenseData:
        for i in range(1,4):
            for attempt in quiz[i]:

                # print(user, attempt)

                if (user[2] == attempt[4]):

                    # put that data into the the 
                    # output data in the right 
                    (OutputData[user[4]])[i] += [[quiz[0]] + attempt]


# print(sourceData)

for key,entry in OutputData.items():
    pprint.pprint(str(key) + "\n" + str(entry))

# ----------------------------------------------------------------------------- 
# Email Departments about User Progress
# ----------------------------------------------------------------------------- 


# ----------------------------------------------------------------------------- 
