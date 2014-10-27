# -*- coding: utf-8 -*-

from django.conf import settings
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import Http404, HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_GET

import math
import oauth2 as oauth
import json
import operator
import re


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
        resp, json_user_timeline = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=50&screen_name='+screen_name, "GET")
        user_timeline = json.loads(json_user_timeline)
        
        if 'sorting' in request.GET and request.GET['sorting'] == 'byRetweet' :
            # sort the retrieved timeline by number of retweet_count
            user_timeline.sort(key=operator.itemgetter("retweet_count"), reverse=True)
        
        json_user_timeline = json.dumps(user_timeline)
        
        return HttpResponse(json_user_timeline, content_type="application/json")
    else:
        return HttpResponseNotFound

@require_GET
def api_user_score(request):
    # only GET requests make it this far thanks to the decorator above
    screen_name = request.GET['screen_name']
    if screen_name is not None:
        user_timeline = get_full_user_timeline(screen_name)
        ##### 1. extract followers_count
        followers_count = long(user_timeline[0]['user']['followers_count'])
        
        ##### 2. extract content's score.
        # In order that the user's ranking is not impacted by its old tweets (everyone can change mood in his life)
        # I am going to consider only the recent tweets
        last_tweet_texts = [tweet['text'].lower() for tweet in user_timeline[:1]]
        content_score = get_content_score(last_tweet_texts)
        print 'content_score is ' + str(content_score)
        
        ##### 3. extract followers' score
        # Based on 1 iteration of a simplified Pagerank algorithm considering only the latest 20 1-degree nodes relative to the screen_name
        cursor = -1
        resp, json_followers = client.request('https://api.twitter.com/1.1/followers/list.json?cursor='+str(cursor)+'&count=20&screen_name='+ screen_name +'&skip_status=false&include_user_entities=false', "GET")
        followers = json.loads(json_followers)

        for user in followers['users']:
            follower_score(user)
        
        followers_score = 1
        
        ##### 4. format a simple json to return the score
        score = {'score' : str(score_equation(followers_count, followers_score, content_score))}
        json_score = json.dumps(score)
        return HttpResponse(json_score, content_type="application/json")
    else:
        return HttpResponseNotFound

def get_full_user_timeline(screen_name):
    # return the full timeline of the user given as screen_name
    resp, json_user_timeline = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=200&screen_name=' + screen_name, "GET")
    user_timeline = json.loads(json_user_timeline)
    
    print len(user_timeline)
    statuses_count = int(user_timeline[0]['user']['statuses_count'])
    print statuses_count
    
    while len(user_timeline) < statuses_count:
        # get the last (ie. smallest) id of the returned tweets and substract it by one
        # max_id is going to be fixed as the max cursor for the next request on the user timeline
        max_id = long(user_timeline[-1]['id_str']) - 1
        resp, json_user_timeline = client.request('https://api.twitter.com/1.1/statuses/user_timeline.json?count=200&screen_name=' + screen_name + '&max_id=' + str(max_id), "GET")
        additional_timeline = json.loads(json_user_timeline)
        
        if len(additional_timeline) == 0:
            break
        
        user_timeline.extend(additional_timeline)
        
    return user_timeline

def follower_score(user):
    print user['screen_name'] + " has " + str(user['friends_count']) + " friends and " + str(user['followers_count']) + " followers"
    
    content_score = get_content_score([user['status']['text']])
    
    s = score_equation(long(user['followers_count']), 1, content_score)
    print (s) / user['friends_count']
    return s
    
def score_equation(followers_count, followers_score, content_score):
    # return the score of a user based on followers_count, followers_score (ie. quality of its followers) and content_score (ie. quality of its tweets)
    return int(math.ceil((math.log(followers_count+1) * followers_score) + content_score))

def get_content_score(tweet_texts):
    # return the score based on the content of a list of tweet_texts given in input
    # tweet_texts is expected to be a list of non-capitalized texts
    # the value returned can be positive or negative.
    word_count = 0
    
    for text in tweet_texts :
        
        for positive_word in settings.POSITIVE_WORDS :
            if re.search(r'\b' + positive_word + r'\b', text) :
                print '+++ ' + positive_word
                word_count += 1
    
        for negative_word in settings.NEGATIVE_WORDS :
            if re.search(r'\b' + negative_word + r'\b', text) :
                print '--- ' + negative_word
                word_count -= 1
                
    return float(word_count) / len(tweet_texts) * 100