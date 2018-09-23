#######################################
########## 1. Load Libraries ##########
#######################################

###a. flask modules
from flask import Flask, render_template, url_for, flash, redirect, request, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import expression, functions
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import MetaData, or_, and_, func, create_engine

###b. python modules
from datetime import datetime
import pandas as pd
import numpy as np
import pymysql
from datetime import datetime #not important
import os, cgi, json, urllib.parse, urllib.request, textwrap
pymysql.install_as_MySQLdb()


##################################
########## 2. App Setup ##########
##################################
###General 
dev = False
entry_point = '/join-dev' if dev else '/join'
app = Flask(__name__, static_url_path=os.path.join(entry_point, 'app/static'))

##### Database setup 
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
#turn off modification tracker
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db = SQLAlchemy(app)
engine = db.engine
Session = sessionmaker(bind=engine)
metadata = MetaData()
metadata.reflect(bind=engine)
tables = metadata.tables


#################################
########## 3. Methods  ##########
#################################

################################################
###1. Add color to tags/keywords ###
def add_color(df):
    # https://brandcolors.net/
    # CHANNEL 4 COLOR PALETTE 
    df['color'] = ""
    for  index, row in df.iterrows():
        row['color'] = "#352935"
        df.at[index, 'color'] = row['color']      
    return df
################################################

################################################
###2. Get top referenced tags in database. used for sidebar. ###
def get_top_tags():
    #query
    subject_query = "SELECT k.keyword, k.id as keyword_id FROM keyword k WHERE k.display = 1"
    
    #load into df
    s = pd.read_sql_query(subject_query, engine)
    
    # Add Color (method above)
    s = add_color(s)
    
    #Get list of primary keys. (In future: don't put this line of code below set_index(),it'll mess it up)
    ids = s['keyword_id'].tolist()
    
    #reset index to primary key
    s.set_index('keyword_id', inplace=True, drop=True)
    
    #df to list 
    s['count'] = 0
    temp = pd.DataFrame()
    for i in ids:
        count_query = "SELECT keyword_id_fk FROM keyword_notebook kn WHERE kn.keyword_id_fk = %d;" %i
        temp = pd.read_sql_query(count_query, engine)
        num = len(temp.index)
        s.at[i, 'count']= num
    s = s.sort_values(['count'], ascending=False)
    
    #Convert to dictionary
    tags = s.to_dict(orient = 'records')
    return tags
################################################

################################################
###3. Get the github url path for a collection of notebooks. ###
def github_collection(df):
    #Empty column to append to
    df['github_url'] = ''
    for index, row in df.iterrows():
        #github path + issue no.
        row['github_url'] = 'https://github.com/theJOIN/join-collection-' + str(row['collection'])
        df.at[index, 'github_url'] = row['github_url']  
    return df
################################################

################################################
###4. Get the github url path for a specific notebook if it is part of a collection. ###
def github_notebook(df):
    #emtpy column to append to
    df['github_url'] = ""
    for index, row in df.iterrows():
        #if part of a collection
        if row['collection_id_fk']:
            t = urllib.parse.quote(row['title'])
            row['github_url'] = 'https://github.com/theJOIN/join-collection-' + str(row['collection_id_fk']) +'/blob/master/' + t + '.ipynb'
            df.at[index, 'github_url'] = row['github_url']

    return df
################################################

################################################
###5. Get all tags associated with a particular notebook. Add color. ###
### This method takes in a dataframe (n) associated with search results, notebooks, keywords etc.
### and returns a dataframe of tags (t).
def get_notebook_tags(n):
    #empty df to append to
    t = pd.DataFrame()
    for index, row in n.iterrows():
        num = n.at[index, 'id']
        tag_query = "SELECT k.keyword, k.id as keyword_id, n.id as notebook_id FROM notebook n  LEFT JOIN keyword_notebook kn on n.id = kn.notebook_id_fk LEFT JOIN keyword k on kn.keyword_id_fk = k.id WHERE (n.id = %d) AND (k.display=1);" %num
        temp = pd.read_sql_query(tag_query, engine)
        t = t.append(temp)
    #Add Color
    t =  add_color(t)
    return t
################################################


################################################
###6. Get the binder url path for a specific notebook if it is part of a collection. ###
def binder_notebook(df):
    #emtpy column to append to
    df['binder_link'] = ""
    for index, row in df.iterrows():
        #if part of a collection
        if row['collection_id_fk']:
            t = urllib.parse.quote(row['title'])
            row['binder_url'] = 'https://mybinder.org/v2/gh/theJOIN/join-collection-' + str(row['collection_id_fk']) +'/master?filepath=' + t + '.ipynb'
            df.at[index, 'binder_url'] = row['binder_url']

    return df
################################################


#################################
########## 4. Templates #########
#################################

################################################
###a. Home - Landing page w/ links to /notebooks
@app.route(entry_point)
@app.route(entry_point+'/') 
def home():
 #mysql query to get all notebooks posted, multiple authors of a notebook will be added together to reduce redundancies 
    unique_posts_query = "SELECT n.id, n.collection_id_fk, n.title, n.url, n.date_posted, n.display, n.abstract, GROUP_CONCAT(DISTINCT a.name ORDER BY rank SEPARATOR ', ') AS author_names, GROUP_CONCAT(DISTINCT a.id) as author_ids FROM notebook n LEFT JOIN author_notebook an ON n.id = an.notebook_id_fk LEFT JOIN author a ON an.author_id_fk = a.id LEFT JOIN keyword_notebook kn on n.id = kn.notebook_id_fk LEFT JOIN keyword k on kn.keyword_id_fk = k.id WHERE n.display=1 AND k.display=1 GROUP BY n.id;"
    #read in query into dataframe
    posts_df = pd.read_sql_query(unique_posts_query, engine)
    posts_df = posts_df.sort_values(by='date_posted', ascending=False)
    
    #To sort by date, we need to get a list of all unique dates posted
    distinct_date_query = " SELECT DISTINCT n.date_posted as posted from notebook n WHERE n.display = 1 GROUP BY n.date_posted DESC; "
    d = pd.read_sql_query(distinct_date_query, engine)

    #convert r'date' columns in dataframes to look better 
    posts_df['date_posted'] = posts_df['date_posted'].dt.strftime('%m/%d/%Y')
    d['posted'] = d['posted'].dt.strftime('%m/%d/%Y')
    
    #get urls
    github_notebook(posts_df)
    binder_notebook(posts_df)

    collection_query = "SELECT * FROM collection ORDER BY collection.id DESC LIMIT 1"
    c = pd.read_sql_query(collection_query, engine)
    for index, row in c.iterrows():
        row['description'] = textwrap.shorten(row['description'], width = 175, placeholder = "...")
        c.at[index, 'description'] = row['description']

    #Get Associated tags
    t = get_notebook_tags(posts_df)
    #get sidebar of subjects
    top_tags = get_top_tags()
    #Change to dictionary
    posts = posts_df.to_dict(orient = 'records')
    tags = t.to_dict(orient = 'records')
    collections = c.to_dict(orient='records')
    dates = d.to_dict(orient = 'records')

    return render_template('home.html', posts = posts, top_tags = top_tags, tags=tags,  dates = dates, collections = collections)
################################################

################################################
###b. About page
@app.route(entry_point+'/abstract') 
def abstract():
    return render_template('abstract.html')
################################################

################################################
###c. Upload page. This is where users can upload their own Jupyter Notebooks. 
@app.route(entry_point+'/upload', methods=['GET', 'POST']) 
def upload():

    if (request.method == 'POST'):

        #We need to do three things here. 
        # 1. Upload authors to SQL database. 
        # 2. Upload notebooks to SQL database.
        # 3. Find a way to connect authors and notebook using mySQL primary key and foreign key.
        #     I'll do that by first uploading notebooks and authors, reading a query back into the script that
        #     will contain their primary keys, sending it to a junction table using those values as foreign keys,
        #     and uploading that link to the junction table SQL database.  
        
        #dictionary from submissions (sub)
        sub_dict = request.form

        #turn dictionary into dataframe
        sub_df = pd.DataFrame.from_dict(sub_dict, orient='index')
        
        ################################################
        ###1. Upload KEYWORDS ###
        #get tags (Series)
        ##The request form pulls in tags as an array. One row (tags) in the dataframe, with one cell containing the array. We first have to parse out the array and turn it into a dataframe
        #locate tag row in request dataframe
        tags = sub_df.at['tags-input', 0] #dtype of 'tags': string
        #split by comma
        tags = tags.split(",") #dtype of 'tags': list
        #length of array
        k_count = len(tags) #used for jct table
        keywords = pd.DataFrame(columns = ['keyword']) 
        keywords['keyword'] = tags #append list to col in dataframe
        #upload tags. Try/pass ensures that there are no duplicate entries (2 keywords that are the same in the database but will point to different notebooks)
        for i in range(k_count):
            try:
                #try inserting the row
                keywords.iloc[i:i+1].to_sql('keyword', engine, if_exists = 'append', index=False)
            except IntegrityError:
                pass
        ################################################
       
        ################################################
        ###2. Upload AUTHORS ###
        #parse author data from submission. start from author's index
        authors = sub_df.ix['author-1':]
        #change index for dataframe
        authors.columns = ['name']
        #length of dataframe
        a_count = len(authors) #used for jct table
        #send to sql table        
        #Try/pass ensures that there are no duplicate entries (2 authors that are the same in the database but will point to different notebooks)
        for i in range(a_count):
            try:
                #try inserting the row
                authors.iloc[i:i+1].to_sql('author', engine, if_exists = 'append', index=False)
            #if integrity error comes up (duplicate entry), skip
            except IntegrityError:
                pass
        ################################################

        ################################################
        ###3. Upload Notebooks####
        #transpose original df to make life easy w/notebook parsing
        sub_df = sub_df.transpose()
        #parse notebook data from submission
        notebook = sub_df.ix[:, :'abstract']
        #to sql
        notebook.to_sql('notebook', engine, if_exists = 'append', index = False)
        ################################################
        
        
        ################################################
        ###4. Author-Notebook Junction Table ###
        #Queries
        # a.  Author Query. This gets primary keys from authors table.
        #takes names from part 2.
        name = authors['name'].tolist()
        session = Session()
        #empty df to append to 
        authors = pd.DataFrame()
        for n in name:
            db_query = session.query(tables['author'].columns['id'])\
                .filter(\
                tables['author'].columns['name'].like('%'+n+'%'), \
                )
            #finish query
            temp = pd.DataFrame(db_query.all())
            authors = authors.append(temp)
        session.close()
        #change to list
        a = authors.values.tolist()

        #b.notebook query 
        notebook_query = "SELECT notebook.id FROM notebook ORDER BY id DESC LIMIT 1"
        notebook = pd.read_sql_query(notebook_query, engine)
        #only one notebook posted
        n = notebook.iloc[0][0]
        #creating junction table's dataframe
        author_notebook = pd.DataFrame(columns= {'author_id_fk', 'notebook_id_fk'})
        author_notebook['author_id_fk'] = a        
        author_notebook['notebook_id_fk'] = n
        
        #send to sql
        author_notebook.to_sql('author_notebook', engine, if_exists='append', index=False)
        ################################################
        
        ################################################
        ###5. second junction table for tags
        #c. Tag Query. 
        session = Session()
        #Because of how annoying quotations are, we have to use sqlalchmey instead of pandas to read in this query.
        keywords = pd.DataFrame()
        for i in tags:
            db_query = session.query(tables['keyword'].columns['id'])\
                .filter(\
                tables['keyword'].columns['keyword'].like('%'+i+'%'), \
                )
            #finish query
            temp = pd.DataFrame(db_query.all())
            keywords = keywords.append(temp)
        session.close()
        k = keywords.values.tolist()
        keyword_notebook = pd.DataFrame(columns = {'keyword_id_fk', 'notebook_id_fk'})
        keyword_notebook['keyword_id_fk'] = k
        keyword_notebook['notebook_id_fk'] = n

        #send to sql
        keyword_notebook.to_sql('keyword_notebook', engine, if_exists = 'append', index=False)
        ################################################

    return render_template('upload.html', title = 'Upload')
################################################


################################################
###d. Submssion Guidelines. 
@app.route(entry_point+'/submission_guidelines')
def submission_guidelines():
    return render_template('submission_guidelines.html')
################################################


################################################
###e. Individual Notebook Page. This is a subroute for each notebook.
@app.route(entry_point+'/notebooks/<int:key>/')
def book(key):
    #select primary key in notebook
    query = "SELECT n.id, n.citation, n.collection_id_fk, GROUP_CONCAT(DISTINCT k.keyword) AS keywords, n.title, n.url, n.date_posted, n.display, n.abstract, GROUP_CONCAT(DISTINCT a.name ORDER BY rank SEPARATOR ', ') AS author_names, GROUP_CONCAT(DISTINCT a.id) as author_ids FROM notebook n LEFT JOIN author_notebook an ON n.id = an.notebook_id_fk LEFT JOIN author a ON an.author_id_fk = a.id LEFT JOIN keyword_notebook kn on n.id = kn.notebook_id_fk LEFT JOIN keyword k on kn.keyword_id_fk = k.id WHERE n.id = %d;" %key
    n = pd.read_sql_query(query, engine)
    
    #Change date_posted to only show date, not time
    n['date_posted'] = n['date_posted'].dt.date

    #notebook will only show on website if 'display' bool is True, or if it isn't empty:
    if n['display'].empty == False:
        try:            
            #get urls
            github_notebook(n)
            binder_notebook(n)
            
            #convert to notebook
            notebook = n.to_dict(orient ='records')

            #get sidebar of subjects
            top_tags = get_top_tags()

            #page URL route - liable to change - used for share buttons
            page = "http://amp.pharm.mssm.edu/join/notebooks/%d/" %key
            
            return render_template('/nbframe.html', notebook=notebook, page=page, top_tags = top_tags )
        except Exception as e:
            return (str(e))
################################################

################################################
###f. Keyword page. This is a subroute for each keyword/subject area ('bioinformatics', 'biochemistry', etc.)
@app.route(entry_point+'/keywords/<string:key>')
def subject(key):
    try:
        #finding highlighted keyword
        keyword_query = "SELECT * FROM keyword WHERE keyword.keyword = '%s'" %key
        k = pd.read_sql_query(keyword_query, engine)
        # keyword
        keyword = k['keyword'].tolist()
       
        #query to find notebooks with relevant keyword - maybe later on we can update to select multiple keywords? for loop for different %s
        notebook_query = "SELECT n.id, n.collection_id_fk, n.title, n.url, n.date_posted, n.display, n.abstract, k.keyword, GROUP_CONCAT(DISTINCT a.name ORDER BY rank SEPARATOR ', ') AS author_names, GROUP_CONCAT(DISTINCT a.id) as author_ids FROM notebook n LEFT JOIN author_notebook an ON n.id = an.notebook_id_fk LEFT JOIN author a ON an.author_id_fk = a.id LEFT JOIN keyword_notebook kn on n.id = kn.notebook_id_fk LEFT JOIN keyword k on kn.keyword_id_fk = k.id WHERE k.keyword = '%s' GROUP BY n.id ORDER BY n.date_posted DESC;" %key
        n= pd.read_sql_query(notebook_query, engine)        
        
        #Get urls    
        github_notebook(n)
        binder_notebook(n)
        
        #convert to dictionary
        notebooks = n.to_dict(orient = 'records')

        #Get tags associated w/notebooks
        t = get_notebook_tags(n)
        tags = t.to_dict(orient='records')

        #get sidebar of subjects
        top_tags = get_top_tags()
        
        return render_template('/keyframe.html', keyword = keyword, top_tags = top_tags, notebooks = notebooks, tags = tags)
    except Exception as e:
        return (str(e))
################################################

################################################
###g. Search Data
#Page for search results
@app.route(entry_point+'/search', methods=['GET'])
def search_data():

    #get search 
    q = request.args.get('q')
    
    #search result - will pass thru to html 
    search = str(q)
    searchlist = search.split(' ')

    df = pd.DataFrame()
    for s in searchlist:
        #Database query
        session = Session()

        #Because of how annoying quotations are, we have to use sqlalchmey instead of pandas to read in this query.
        db_query = session.query(tables['notebook'], tables['author'].columns['name'])\
                .join(tables['author_notebook'], tables['notebook'].columns['id'] == tables['author_notebook'].columns['notebook_id_fk'])\
                .join(tables['author'], tables['author_notebook'].columns['author_id_fk'] == tables['author'].columns['id'])\
                .filter(or_(\
                tables['notebook'].columns['title'].like('%'+s+'%'), \
                tables['notebook'].columns['abstract'].like('%'+s+'%'), \
                tables['author'].columns['name'].like('%'+s+'%')\
                ))

        #finish query
        temp = pd.DataFrame(db_query.all())
        session.close()
        #check to see that a search query returned something from the database
        results = len(temp.index)
        if (results):        
            
            ###append, drop duplicates
            df = df.append(temp)
            df = df.drop_duplicates()

            #drop any row where display = 0 (not selected to view on website)
            df = df[df.display != 0] 

            #aggregate by URL (can't take ID b/c multiple pks, fks)
            #add a quick index to the dataframe. will give errors otherwise.
            df = df.groupby('url').agg({'title':'first', 'abstract':'first'.join}).reset_index()

            #add back in the join id, keywords, date posted to dataframe
            #will iterate by url instead of join id. i know this isn't as good as iterating by id but it shouldn't be too big of an issue, since no two url's are alike.
            url = df['url'].tolist()

            #new frame to append into df 
            id_frame = pd.DataFrame()
            
            #for loop iterating thru url
            for u in url: 
                #query
                id_query = "SELECT n.id, n.collection_id_fk, n.display, n.date_posted, GROUP_CONCAT(DISTINCT a.name ORDER BY rank SEPARATOR ', ') AS author_names, GROUP_CONCAT(DISTINCT a.id) as author_ids FROM notebook n LEFT JOIN author_notebook an ON n.id = an.notebook_id_fk LEFT JOIN author a ON an.author_id_fk = a.id  WHERE (n.url = '%s') AND (n.display=1) GROUP BY n.id ORDER BY  n.date_posted DESC;" %u
                x = pd.read_sql_query(id_query, engine)
                #append to df
                id_frame = id_frame.append(x)

            #get indices leveled for both dataframes
            id_frame = id_frame.reset_index()

            #join df's together
            df = df.join(id_frame, how='left')

            #drop time from date posted (datetime) 
            df['date_posted'] = df['date_posted'].dt.date
            #Drop empty rows in dataframe
            df = df.dropna()
            #Get Associated tags
            t = get_notebook_tags(df)

            #Get urls
            github_notebook(df)
            binder_notebook(df)

            #turn to dictionary 
            posts = df.to_dict(orient = 'records')
            tags = t.to_dict(orient = 'records')
            #get sidebar of subjects
            top_tags = get_top_tags()
             
            return render_template('/search_data.html', posts=posts, search=search, results=results, tags = tags, top_tags = top_tags)   
    else:
        posts = {}
        top_tags = get_top_tags()
        return render_template('/search_data.html', posts=posts, top_tags = top_tags, search=search, results=results)
################################################

################################################
###h. Notebook page  - full list of all Jupyter notebooks
@app.route(entry_point+'/notebooks/') 
def notebooks():
    #mysql query to get all notebooks posted, multiple authors of a notebook will be added together to reduce redundancies 
    unique_posts_query = "SELECT n.id, n.collection_id_fk, n.title, n.url, n.date_posted, n.display, n.abstract, GROUP_CONCAT(DISTINCT a.name ORDER BY rank SEPARATOR ', ') AS author_names, GROUP_CONCAT(DISTINCT a.id) as author_ids FROM notebook n LEFT JOIN author_notebook an ON n.id = an.notebook_id_fk LEFT JOIN author a ON an.author_id_fk = a.id LEFT JOIN keyword_notebook kn on n.id = kn.notebook_id_fk LEFT JOIN keyword k on kn.keyword_id_fk = k.id WHERE n.display=1 AND k.display=1 GROUP BY n.id;"
    #read in query into dataframe
    posts_df = pd.read_sql_query(unique_posts_query, engine)
    posts_df = posts_df.sort_values(by='date_posted', ascending=False)

    #To sort by date, we need to get a list of all unique dates posted
    distinct_date_query = " SELECT DISTINCT n.date_posted as posted from notebook n WHERE n.display = 1 GROUP BY n.date_posted DESC; "
    d = pd.read_sql_query(distinct_date_query, engine)

    #convert r'date' columns in dataframes to look better 
    posts_df['date_posted'] = posts_df['date_posted'].dt.strftime('%m/%d/%Y')
    d['posted'] = d['posted'].dt.strftime('%m/%d/%Y')
    
    #Github urls
    github_notebook(posts_df)
    binder_notebook(posts_df)

    #Get Associated tags
    t = get_notebook_tags(posts_df)
    #get sidebar of subjects
    top_tags = get_top_tags()
    #Change to dictionary
    posts = posts_df.to_dict(orient = 'records')
    tags = t.to_dict(orient = 'records')
    dates = d.to_dict(orient = 'records')

    return render_template('notebooks.html', posts = posts, top_tags = top_tags, tags=tags,  dates = dates) 
################################################

################################################
###i. Author page - full list of all authors (should be moved to notebooks page search query?) - need to fix
@app.route(entry_point+"/search")
def authors(name, author_id):
    #author query
    author_query = "SELECT n.id ,n.date_posted, n.abstract, n.url, n.title, n.collection_id_fk FROM notebook n LEFT JOIN author_notebook an ON n.id = an.notebook_id_fk LEFT JOIN author a ON an.author_id_fk = a.id  WHERE (a.id LIKE 3) AND  (n.display=1) GROUP BY n.id ORDER BY  n.date_posted DESC;"
    df = pd.read_sql_query(author_query, engine)

    df = df.drop_duplicates()

    #convert dataframe to dictionary  
    posts =  df.to_dict(orient='records')  
    top_tags = get_top_tags()
    return render_template('search_data.html', posts=posts, name=search)
################################################

################################################
###j. Collections page - list of ALL COLLECTIONS
@app.route(entry_point+"/collections")
def collections():
    #get list of collections
    collection_query = "SELECT * FROM collection ORDER BY date_posted DESC"
    i = pd.read_sql_query(collection_query, engine)

    #get list of collections based on id
    collection_id = i['id']
    
    #how many notebooks in collection
    #set index
    i = i.set_index(['id'])
    i['notebook_count'] = 0
    
    # attach Github URL of collection to 'collections' dataframe 
    github_collection(i)

    #get notebooks from matching foreign keys
    #empty dataframe to append to
    n = pd.DataFrame()
    #loop thru foreign keys of collections
    for x in collection_id:
        notebook_query= "SELECT n.id ,n.date_posted, n.url, n.title, n.collection_id_fk FROM notebook n WHERE n.collection_id_fk = %d ORDER BY  n.date_posted DESC;" %x
        #temp dataframe
        temp = pd.read_sql_query(notebook_query, engine)
        n = n.append(temp) #append to empty dataframe
        #add # of notebooks in collection to dataframe
        i.at[x, 'notebook_count'] = len(temp)
    #Change date_posted to only show date, not time
    n['date_posted'] = n['date_posted'].dt.date
    i['date_posted'] = i['date_posted'].dt.date

    #convert to dictionary
    notebooks = n.to_dict(orient='records')
    collections = i.to_dict(orient='records')
    #Get subjects sidebar
    top_tags = get_top_tags()
    return render_template('collections.html', collections=collections,  notebooks = notebooks, top_tags = top_tags)
################################################

################################################
###k. collection page - one INDIVIDUAL collection containing a selected LIST of notebooks
@app.route(entry_point+'/collections/<int:key>')
def collection_template(key):
    #url route: subject to change
    page = "http://amp.pharm.mssm.edu/join/collections/%d/" %key

    #Get called collection
    collection_query = "SELECT * FROM collection WHERE id = %d" %key
    i = pd.read_sql_query(collection_query, engine)

    #Get associated notebooks
    notebook_query = "SELECT n.id ,n.date_posted, n.abstract, n.url, n.title, n.collection_id_fk,GROUP_CONCAT(DISTINCT a.name ORDER BY rank SEPARATOR ', ') AS author_names, GROUP_CONCAT(DISTINCT a.id) as author_ids FROM notebook n LEFT JOIN author_notebook an ON n.id = an.notebook_id_fk LEFT JOIN author a ON an.author_id_fk = a.id  LEFT JOIN keyword_notebook kn on n.id = kn.notebook_id_fk LEFT JOIN keyword k on kn.keyword_id_fk = k.id WHERE (n.collection_id_fk = %d) AND  (n.display=1) GROUP BY n.id ORDER BY  n.date_posted DESC;" %key
    n = pd.read_sql_query(notebook_query, engine)

    #Get urls of collection and notebooks
    github_collection(i)
    github_notebook(n)
    binder_notebook(n)

    #Get Associated tags
    t = get_notebook_tags(n)

    #Change date_posted to only show date, not time
    n['date_posted'] = n['date_posted'].dt.date
    i['date_posted'] = i['date_posted'].dt.date
    
    #convert to dictionary
    notebooks = n.to_dict(orient='records')
    collections = i.to_dict(orient='records')
    tags = t.to_dict(orient='records')

    return render_template('collectionframe.html', notebooks=notebooks, collections=collections, tags = tags, page=page)
################################################

#################################
########## 5. Errors  ###########
#################################

################################################
###a. 404 Error page
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404
################################################

################################################
###b. 500 Error page
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500
################################################
