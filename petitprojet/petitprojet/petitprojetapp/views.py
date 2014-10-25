# -*- coding: utf-8 -*-

from django.conf import settings
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_GET

import oauth2 as oauth
import json
import operator

# Authentication for the Twitter API with oauth2
consumer = oauth.Consumer(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
client = oauth.Client(consumer)


def home(request):    
    return render_to_response('home.html', context_instance=RequestContext(request))

@require_GET
def api_user_timeline(request):
    # only GET requests make it this far thanks to the decorator above
    screen_name = request.GET['screen_name']
    if screen_name is not None:
        #retrieve the user_timeline with the last 50 tweets
        resp, json_user_timeline_content = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=50&screen_name='+screen_name, "GET")
        content = json.loads(json_user_timeline_content)
        
        if 'sorting' in request.GET and request.GET['sorting'] == 'byRetweet' :
            # sort the retrieved timeline by number of retweet_count
            content.sort(key=operator.itemgetter("retweet_count"), reverse=True)
        
        json_user_timeline_content = json.dumps(content)
        
        return HttpResponse(json_user_timeline_content, content_type="application/json")
    else:
        return HttpResponseNotFound

@require_GET
def api_user_score(request):
    # only GET requests make it this far thanks to the decorator above
    screen_name = request.GET['screen_name']
    if screen_name is not None:
        #resp, json_followers_content = client.request('https://api.twitter.com/1.1/followers/ids.json?cursor=-1&count=5000&screen_name='+screen_name, "GET")
        #resp, json_user_content = client.request('https://api.twitter.com/1.1/users/show.json?screen_name='+screen_name, "GET")
        
        user_timeline_content = get_full_user_timeline(screen_name)
        # i'll do something to modify/search content
        # 1. extract #followers, #followers' score, #content's score
        # 2. format a simple json to return the score
        #print json_content
       # content = json.loads(json_content)
        #print "here content data"
        #print content
        
        score = {'score' : '69' }
        json_score = json.dumps(score)
        return HttpResponse(json_score, content_type="application/json")
    else:
        return HttpResponseNotFound

def get_full_user_timeline(screen_name):
    # return the full timeline of the user given as screen_name
        resp, json_user_timeline_content = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=200&screen_name=' + screen_name, "GET")
        user_timeline_content = json.loads(json_user_timeline_content)
        
        print len(user_timeline_content)
        statuses_count = int(user_timeline_content[0]['user']['statuses_count'])
        print statuses_count
        
        while len(user_timeline_content) < statuses_count:
            # get the last (ie. smallest) id of the returned tweets and substract it by one
            # max_id is going to be fixed as the max cursor for the next request on the user timeline
            max_id = long(user_timeline_content[-1]['id_str']) - 1
            resp, json_user_timeline_content = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=200&screen_name=' + screen_name + '&max_id=' + str(max_id), "GET")
            additional_timeline_content = json.loads(json_user_timeline_content)

            if len(additional_timeline_content) == 0:
                break
            
            user_timeline_content.extend(additional_timeline_content)
            
        return user_timeline_content
        
        