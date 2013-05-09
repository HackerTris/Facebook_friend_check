# -*- coding: utf-8 -*-

"""This module's functionality shows who likes a logged on Facebook user's posts, and who comments on the posts.

    Use case:  You got sucked into Facebook... Why you?  Well, since you have limited time, you don't want to waste it liking or
    commenting on your friends posts who never do the same for you.  What's fair is fair... Use friend_check to figure out who your
    most active friends are!
    
    To use this module, you must first have a valid access token.  See facebook__login.py.  This access token
    should include all of the permissions shown in the facebook__login.py module.  Please refer to the module's documentation for
    restrictions and further usage information.

    Data is stored in a mongo db database.  Currently, this exists on the local host, but the connection string can
    be changed accordingly.  (Eventually, this functionality is intended to be hosted in the cloud. 

    The main functions in this module include:
    cleanup_data:  Reinitalizes the database.
    get_access_token: Retrieves a valid Facebook access token for the logged on user.
    get_my_friends:  Get a list of the logged on user's Facebook friends.
    get_my_posts_likes:  Get a list of your friends who have liked your posts.
    get_my_posts_comments:  Get a list of your friends who have commented on your posts.
    display_likes_info:  Display a sorted lists of the friends who have liked your posts, and the number of likes they have issued.
    display_comments_info:  Display a sorted list of friends who have commented on your posts, and the number of comments they issued.
    display_sielent_friends:  Display a list of your friends who never like or comment on your stuff.

    There are a few other functions in this module, that are currently under development.  I kept them in here for reference.
    
    
    
"""


import sys
import json
import urllib2
import operator # allows us to sort "dictionaries", used for mongo aggregate functions

import pymongo
from pymongo.errors import ConnectionFailure
from bson.son import SON  # used for sorting "dictionaries" returned by mongo aggregate functions

import facebook
from facebook__login import login

# create database connection which will be used for inserting facebook data
# into a mongodb database instance.  Note that currently, this happens on local host, but
# in a production type environment, it would not.  Also, we are not using db authorization to
# keep things simple; something else unlikely to be the case in a real production enviornment

try:
    connection=pymongo.Connection("mongodb://localhost",safe=True)
except ConnectionFailure, e:
    sys.stderr.write("Could not connect to MongoDB: %s" % e)
    sys.exit(1)
    
db = connection.Facebook


ACCESS_TOKEN=""


def get_access_token():
    """Retrieve a previously stored access token, which gives this app permission to look at your data.

    This function currently expects an access token stored in a file.  This will need to change once this
    app is hosted in the cloud.

    """
    global ACCESS_TOKEN
    print("get_access_token, reporting for duty")
    try:
        ACCESS_TOKEN = open('out/facebook.access_token').read()
    except:
        print >> sys.stderr, "Could not find access token.  Regnerating..."
        ACCESS_TOKEN=login()
    #return ACCESS_TOKEN

        
def get_groups(group_name):

    """Get groups associated with this users.  This function is not currently being used; it is for reference only.
       Arguments:  Facebook group name
    """
    LIMIT = 100

    gapi = facebook.GraphAPI(ACCESS_TOKEN)

    # Find groups with the query term in their name

    group_ids = []
    i = 0
    while True:
        results = gapi.request('search', 
                                {'q': group_name,
                                'type': 'group',
                                'limit': LIMIT,
                                'offset': LIMIT * i,
                                })
        if not results['data']:
            break

        ids = [group['id'] for group in results['data'] if group['name'
           ].lower().find('programming') > -1]

        # once groups stop containing the term we are looking for in their name, bail out

        if len(ids) == 0:
            break
        group_ids += ids

        i += 1


    if not group_ids:
        print 'No results'
        return
    
    # Get details for the groups
    
    groups = gapi.get_objects(group_ids, metadata=1)

    # Count the number of members in each group. The FQL API documentation at
    # http://developers.facebook.com/docs/reference/fql/group_member hints that for
    #groups with more than 500 members, we'll only get back a random subset of up
    # to 500 members.

    i =0 ;
    for g in groups:
        if i > 9:
            break
        else:
            i += 1 
        group = groups[g]
        conn = urllib2.urlopen(group['metadata']['connections']['members'])
        try:
            members = json.loads(conn.read())['data']
        finally:
            conn.close()
        print group['name'], len(members)

        
def get_my_friends():

    """Get friends associated with the logged in user.

    This function will get the first 500 of the
    logged on user's freinds.  The data will be rearragned so
    it is a FB id/name dictionary, with the id as the key.   This is useful in some of the other functionality
    which only provides FB id's.
    
    """
    #print("get my friends, reporting for duty")
    graph=facebook.GraphAPI(ACCESS_TOKEN)
    me=graph.get_object("me")
    friends_data=graph.get_connections(me["id"],"friends",limit = 500)
    friends_list=friends_data["data"]

    # We ignore paging data since we limit the list to 500 friends
    
    friends = {}
    for friend in friends_list:
        friends[int(friend["id"])] = friend["name"]
        
    return friends


def pretty_print(doc):
    """Debugging printing aid.

    Arguments:  doc.  This is the datastructure stored in the database.
    
    This function is for debugging purposes only.  It pretty prints
    the facebook 'container' - such as statuses, videos, photos- that we are
    interested in.
    
    """
    for k,v in doc.items() :
        print("Key: ",k)
        
        if v is type(list):
            print("Value(s): ")
            for l_item in v:
                for k1,v1 in l_item:
                    print("    key:   "  , k1)
                    print("    value: ", v1)
        else:
            print("Value: ",v)

            
def check_liked_object(id,friends):
    """Check the liked object to ensure it belongs to the user, and get all of the likers.

    This function takes the liked object and checks that a friend actually liked the object (which will exclude
    likes from people who are not friends.  This function will also check the exact number of likes.  When Facebook stores an
    object's likes, it only stores a count of the likes and the first couple of users who liked the object... so an additional FQL
    based query is done to get ALL of the likes.

    Arguments:
    id:  Facebook's object id.
    friends: List of logged on user's friends.  Actually a dict with facebook user id as key, facebook user name as value.
    
    """
    #print("Check object, reporting for duty.")
   
    
    #we have to extract the object from the object id. The object id is actually in the
    #format of a connection object.  We need to get the actual object by stripping off the first part of the id
    #which belongs to the user.  The id is in the format of xxx_yyy , where xxx refers to the user id portion,
    #and yyy refers to the object that was liked.

    #Important Note:  FB seems to have some issues with stale data.  We can probably improve our accuracy here, overcoming
    #some of the stale data issues, but we will leave it as is for now.
    
    obj_id = id.split('_')
 
    #we don't really need the object_type here... remove it when we do clean up
    
    query_string="select user_id, object_type from like where object_id="+obj_id[1]
 
    graph = facebook.GraphAPI(ACCESS_TOKEN)
    result = graph.fql(query_string)
    likes=[]
    for user in result:
        d = { }
        if user["user_id"] in friends:
            d["id"] = user["user_id"]
            d["name"] = friends[user["user_id"]]
            likes.append(d)
    return likes


def process_post_like_data(data,friends):
    """Process the post's liked data, for insertion into mongo db.

    The structure of the mongo doc to be stored includes the object's id, created_time, and a list of "likers".  The list consists of a set of
    key/value pairs:  Key is the user id who liked the object, value is the name of the user who liked the object.

    Arguments:
    data:  a dictionary containing the a value for all of the likes data for a particular post.
    friends:  List of key/value pairs were each pair (facebook id, name) reference a valid friend.
    
    """
 
    #print("Process_post_like_data,reporting for duty")
 
    for dict in data:
        doc = {}
        if 'likes' in dict:
            list_of_likes =check_liked_object(dict["id"], friends)
            if len(list_of_likes) == 0:
                continue
            doc["_id"] = dict["id"]
            doc["created_time"] = dict["created_time"]
            doc["item_data"] = list_of_likes
            db.likes.insert(doc)

            

    
def display_info(description,ranked_friends):
    """Pretty print information to console.

    Pretty print the ranked friends likes.  Always a list of tuples with the
    structure (name,count)

    Arguments:
    description:  Textual description to label the data.
    ranked_friends:  List of friends.  The friend structure is the friend name, followed by a count - the count usually refers to the
    number of likes or number of comments that the friend has issued.
    
    """
    print("\n" + description + "\n")
    for friend in ranked_friends:
        print '{0:30} {1:10d}'.format(friend[0],friend[1])
    print("\n")

    
def get_my_posts_likes(friends):
    """Get posts for the user, and find out who liked the post.

    Steps:
    1. Reach out to the likes connection of posts:  me/posts?fields=likes
    2. Process the set of likes for each post

    Do the above for each page of data.  Keep getting datapages until there aren't any left.  Please note
    that Facebook pagination is undergoing modifications.  Different object types accept different types of
    paging mechanisms.

    Arguments:
    friends:   List of key/value pairs were each pair (facebook id, name) reference a valid friend.

    """

    
    #print("get my posts, reporting for duty")
    graph = facebook.GraphAPI(ACCESS_TOKEN)
    me = graph.get_object("me")
    posts = graph.get_connections(me["id"],"posts",limit=100,fields="likes")
    data = posts["data"]
    paging = posts["paging"]

    while (data):
        process_post_like_data(data,friends)
        if "next" in paging:
            next_page=graph.fetch_next_page(paging["next"])
            data = next_page["data"]
            if "paging" in next_page:
                paging = next_page["paging"]
            else:
                paging = {}
        else:
            break

        
def get_my_posts_comments():
    """Get comment data (a grouping of users who commented user's posts/

    This is similiar to getting the likes, but the structure of the
    data is different.  The likes data is associated with a count, whereas the
    comment data is associated with a paging structure.  Alternatively,
    we could query the FQL tables for each post associated with a comment, which would
    be slower.

    The comments connection supports cursor based pagination, which has a slightly different structure than
    earlier pagination mechanisms.  The other graph api endpoints, such
    as posts, do not support cursor based pagination at this time.
    
    """
    #print("get my posts comments, reporting for duty")
    
    graph = facebook.GraphAPI(ACCESS_TOKEN)
    me = graph.get_object("me")
    posts = graph.get_connections(me["id"],"posts",limit=100,fields="comments")
    data = posts["data"]
    paging = posts["paging"]

    while (data):
        process_post_comment_data(data)
        if "next" in paging:
            next_page = graph.fetch_next_page(paging["next"])
            data = next_page["data"]
            if "paging" in next_page:
                paging = next_page["paging"]
            else:
                paging = {}
        else:
            break

        
def process_post_comment_data(data):
    """Process comment data for storage in mongo db.

    This function will coordinate processing comment data.
    
    Arguments:
    data:  A list of dictionaries of comment data.  The data structure is how Facebook returns the data.  Use the Facebook Graph
    API Explorer to understand this structure.
    
    """
 
    #print("Process_post_comment_data,reporting for duty")
 
    for dict in data:
        doc = {}
        if 'comments' in dict:
            list_of_commenters = check_commented_object(dict["comments"])
            doc["_id"] = dict["id"]
            doc["created_time"] = dict["created_time"]
            doc["item_data"] = list_of_commenters
            db.comments.insert(doc)

            
def check_commented_object(comments_dict):
    """Check comment data, and create list of commenters for each post.

    This function will process comment information.  We are interested in the commenter's name and id. 

    Arguments:
    comments_dict: This is a list of dictionaries with two keys:   data, which points to the comment data- that is, who commented on it and what
    the comments are, and paging, which contains cursor based paging information.
 
    """

    #print("check_commented_object, reporting for duty")
    comments = comments_dict
    list_of_commenters = []
    data = comments["data"]

    while (data):
        for comment in data:
            d = {}
            d["id"] = comment["from"]["id"]
            d["name"] = comment["from"]["name"]
            list_of_commenters.append(d)
        #now see if there is any paging data to process
        if "next" in comments["paging"]:
            comments = graph.fetch_next_page(comments["paging"]["next"])
            data = comments["data"]
        else:
            break
    return list_of_commenters


def display_likes_info():
    """ Display the likes information to the console.  Actually, could be displayed in any format, using the correct display_info function.

    Consider refactoring this function to pass in the display_info function, which will allow flexibility for different user experiences (web page,
    console, etc.)

    """

    #print ("display_likes_info, reporting for duty")
    result = db.likes.aggregate([
                                {"$unwind":"$item_data"},
                                {"$group":{"_id":"$item_data.name","count":{"$sum":1}}},
                                {"$sort":SON([("count",-1)])}
                                ])

    
    likes_list = result["result"]
    likes = {}
    for l in likes_list:
        name = l["_id"]
        count = l["count"]
        likes[name] = count
    sorted_likes = sorted(likes.iteritems(),key=operator.itemgetter(1))
    sorted_likes.reverse()
    display_info("Friends who have liked your posts" ,sorted_likes)

    
def display_comments_info():
    """Display comment information to the console.  See above.

    This function will output a tally of those who have commented on your posts.
    
    """
    #print("display_comments_info, reporting for duty")
    result = db.comments.aggregate([
        
                                    {"$unwind":"$item_data"},
                                    {"$group":{"_id":"$item_data.name","count":{"$sum":1}}},
                                    {"$sort":SON([("count",-1)])}
                                ])
    
    comments_list = result["result"]
    comments = {}
    for c in comments_list:
        name = c["_id"]
        count = c["count"]
        comments[name] = count
    sorted_comments = sorted(comments.iteritems(),key=operator.itemgetter(1))
    sorted_comments.reverse()
    display_info("Friends who have commented on your posts",sorted_comments)

    
def display_silent_friends(friends):
    """Display to console those friends who haven't liked or commented on anything.

    Consider refactoring to allow flexibility for different user experiences.
    """
    
    #print("find_silent_friends, reporting for duty")
    setOfFriends = set(friends.keys())
    query ={ }
    selection = {"created_time":0,"_id":0}

    cursor = db.likes.find(query,selection)
    activeFriends = set()

    for doc in cursor:
        data = doc['item_data']
        for friend in data:
            activeFriends.add(friend['name'])

    
    cursor=db.comments.find(query,selection)
    
    for doc in cursor:
        data = doc['item_data']
        for friend in data:
            activeFriends.add(friend['name'])

    
    allFriends = set(friends.values())
    
    silentFriends = allFriends - activeFriends
    
    print("Your friends who have not liked or commented on your stuff: ")
    for friend in silentFriends:
        print(friend)

        
def cleanup_data():
    """Remove data from mongo db dictionary.

    The data is generated anew for each run.
    
    """
    print("cleanup_data, reporting for duty")
    db.likes.drop()
    db.comments.drop()
            
    
if __name__ =='__main__':
    """Mainline for console experience.
    """
    print ("Friend_check... reporting for duty")
    cleanup_data()
    get_access_token()
    friends = get_my_friends()
    get_my_posts_likes(friends)
    get_my_posts_comments()
    display_likes_info()
    display_comments_info()
    display_silent_friends(friends)
 
                          
                              
