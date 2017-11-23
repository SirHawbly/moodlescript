# ----------------------------------------------------------------------------- 
# indecies for database output.
# ----------------------------------------------------------------------------- 

HOST = 0
DBNAME = 1
USER = 2
PASS = 3

# ----------------------------------------------------------------------------- 

QUIZNAME = 2

# ----------------------------------------------------------------------------- 

MODULETYPE = 3
MODULENAME = 4

# ----------------------------------------------------------------------------- 

ATTEMPTQID = 0
ATTEMPTUID = 1
ATTEMPTSCORE = 2
ATTEMPTTIME = 3

# ----------------------------------------------------------------------------- 

USERUID = 0
USERLAST = 1
USERFIRST = 2
USERUNAME = 3
USERMAIL = 4
USERLOG = 5

# ----------------------------------------------------------------------------- 

QUIZQID = 0

# ----------------------------------------------------------------------------- 

SOURCEMAIL = 2
SOURCENAME = 4 
PASSINGSCORE = 5

# ----------------------------------------------------------------------------- 

DATANAME = 0
DATAPASS = 1
DATAFAIL = 2
DATAAWOL = 3
DATANLOG = 4

# ----------------------------------------------------------------------------- 
# User Group Variables
# ----------------------------------------------------------------------------- 

passedUsers = 'passedUsers'
failedUsers = 'failedUsers'
awolUsers = 'awolUsers'
noLogUsers = 'noLogUsers'

userGroups = [passedUsers, failedUsers, awolUsers, noLogUsers]

# ----------------------------------------------------------------------------- 
# Queries for Databases
# ----------------------------------------------------------------------------- 

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
