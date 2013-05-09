import sys
import json
import facebook
import urllib2
from facebook__login import login

try:
    ACCESS_TOKEN=open('out/facebook.access_token').read()
    Q=sys.argv[1]
except IOError,e:
    try:
        #if you pass in the access token from the FB app as a command line
        #parameter, be sure to wrap it in single quotes so the shell doesn't
        #try to interpret it

        ACCESS_TOKEN=sys.argv[1]
        Q=sys.argv[2]
    except:
        print >>sys.stderr,"Coud not find access token in file or parsing args"
        ACCESS_TOKEN=login()
        Q=sys.argv[1]

LIMIT=100

gapi=facebook.GraphAPI(ACCESS_TOKEN)


#find groups with the query term in their name

group_ids=[]
i = 0
while True:
    results=gapi.request('search',{
                                    'q':Q,
                                    'type':'group',
                                    'limit':LIMIT,
                                    'offset':LIMIT*i
                                    })
    if not results['data']:
        break
    ids=[group['id'] for group in results['data'] if group['name'].lower().find('programming')>-1]
    # once groups stop containing the term we are looking for in their name, bail out
    if len(ids)==0:
        break
    group_ids+=ids
    i += 1

if not group_ids:
    print 'No results'
    sys.exit()

#get details for the groups

groups=gapi.get_objects(group_ids, metadata=1)
#count the number of members in each group.  We will probably get a random
#selection for those groups with more than 500 members.

c=1;
for g in groups:
    group=groups[g]
    if c==1:
        print ("**** Dump ****")
        print(group)
        print("**********")
        print(group['metadata']['connections']['members'])
    c+=1
    
    conn = urllib2.urlopen(group['metadata']['connections']['members'])
    try:
        members=json.loads(conn.read())['data']
    finally:
        conn.close()
    print group['name'],len(members)

    

    

    
