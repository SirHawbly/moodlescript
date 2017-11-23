
# ----------------------------------------------------------------------------- 
# libraries
# ----------------------------------------------------------------------------- 

import csv
import psycopg2

from moodleVariables import * 

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
