from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from chatbot import Chat, reflections, multiFunctionCall
import requests, os
from django.views.decorators.csrf import csrf_exempt
from .models import Conversation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from slackclient import SlackClient   


SLACK_VERIFICATION_TOKEN = getattr(settings, 'SLACK_VERIFICATION_TOKEN', None)
SLACK_BOT_USER_TOKEN = getattr(settings, 'SLACK_BOT_USER_TOKEN', None)
Client = SlackClient(SLACK_BOT_USER_TOKEN)


def whoIs(query, sessionID="general"):
    if query[-2] == '?':
        query = query[:len(query)-2]
    try:
        response = requests.get('http://api.stackexchange.com/2.2/tags/' + query + '/wikis?site=stackoverflow')
        data = response.json()
        return data['items'][0]['excerpt']
    except:
        pass
    return "Oh, You misspelled somewhere!"


def results(query, sessionID="general"):
    query_list = query.split(' ')
    query_list = [x for x in query_list if x not in ['posted', 'questions', 'recently', 'recent', 'display', '', 'in', 'of', 'show']]
    if len(query_list) == 1:
        # print('con 1')
        try:
            response = requests.get('https://api.stackexchange.com/2.2/questions?pagesize=5&order=desc&sort=activity&tagged=' + query_list[0] + '&site=stackoverflow')
            data = response.json()
            data_list = [str(i+1)+'. ' + data['items'][i]['title'] for i in range(5)]
            return '<br/>'.join(data_list)
        except:
            pass
    elif len(query_list) == 2 and 'unanswered' not in query_list:
        query_list = sorted(query_list)
        n = query_list[0]
        tag = query_list[1]
        try:
            response = requests.get('https://api.stackexchange.com/2.2/questions?pagesize='+ n +'&order=desc&sort=activity&tagged=' + tag + '&site=stackoverflow')
            data = response.json()
            data_list = [str(i+1)+'. ' + data['items'][i]['title'] for i in range(int(n))]
            return '<br/>'.join(data_list)
        except:
            pass

    else:
        query_list = [x for x in query_list if x not in ['which', 'where', 'whos', 'who\'s' 'is', 'are', 'answered', 'not', 'unanswered', 'for']]
        if len(query_list) ==1:
            try:
                response = requests.get(
                    'https://api.stackexchange.com/2.2/questions/no-answers?pagesize=5&order=desc&sort=activity&tagged=' + query_list[0] + '&site=stackoverflow')
                data = response.json()
                data_list = [str(i+1)+'. ' + data['items'][i]['title'] for i in range(5)]
                return '<br/>'.join(data_list)
            except:
                pass
        elif len(query_list) == 2:
            query_list = sorted(query_list)
            n = query_list[0]
            tag = query_list[1]
            try:
                response = requests.get(
                    'https://api.stackexchange.com/2.2/questions/no-answers?pagesize='+ n +'&order=desc&sort=activity&tagged=' + tag + '&site=stackoverflow')
                data = response.json()
                data_list = [str(i+1)+'. ' + data['items'][i]['title'] for i in range(int(n))]

                return '<br/>'.join(data_list)
            except:
                pass
    return "Oh, You misspelled somewhere!"


#Display recent 3 python questions which are not answered
firstQuestion = "Hi, How may i help you?"

call = multiFunctionCall({"whoIs": whoIs,
                              "results": results})

chat = Chat(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "chatbotTemplate",
                         "Example.template"
                         ),
            reflections, call=call)


def Home(request):
    return render(request, "alpha/home.html", {'home': 'active', 'chat': 'chat'})


@csrf_exempt
def Post(request):
    while len(chat.conversation["general"])<2:
        chat.conversation["general"].append('initiate')
    if request.method == "POST":
        query = request.POST.get('msgbox', None)
        store = Conversation()
        store.query = query
        response = chat.respond(query)
        store.response = response
        store.save()
        chat.conversation["general"].append('<br/>'.join(['ME: '+query, 'BOT: '+response]))
        if query.lower() in ['bye', 'quit', 'bbye', 'seeya', 'goodbye']:
            chat_saved = chat.conversation["general"][2:]
            response = response + '<br/>' + '<h3>Chat Summary:</h3><br/>' + '<br/><br/>'.join(chat_saved)
            chat.conversation["general"] = []
            return JsonResponse({'response': response, 'query': query})
        #c = Conversation(query=query, response=response)
        return JsonResponse({'response': response, 'query': query})
    else:
        return HttpResponse('Request must be POST.')


'''
def Post(request):
    if request.method == "POST":
        msg = request.POST.get('msgbox', None)
        c = Chat(message=msg)
        if msg != '':
            c.save()
        return JsonResponse({'msg': msg, 'user': 'user'})
    else:
        return HttpResponse('Request must be POST.')
'''




class Events(APIView):
    
    def post(self, request, *args, **kwargs):

        slack_message = request.data

        if slack_message.get('token') != SLACK_VERIFICATION_TOKEN:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # verification challenge
        if slack_message.get('type') == 'url_verification':
            return Response(data=slack_message,
                            status=status.HTTP_200_OK)
        # greet bot
        if 'event' in slack_message:                              #4
            event_message = slack_message.get('event')            #
            
            # ignore bot's own message
            if event_message.get('subtype') == 'bot_message':     #5
                return Response(status=status.HTTP_200_OK)        #
            
            # process user's message
            user = event_message.get('user')                      #6
            text = event_message.get('text')                      #
            channel = event_message.get('channel')                #
            bot_text = 'Hi <@{}> :wave:'.format(user)             #
            if 'hi' in text.lower():                              #7
                Client.api_call(method='chat.postMessage',        #8
                                channel=channel,                  #
                                text=bot_text)                    #
                return Response(status=status.HTTP_200_OK)        #9

        return Response(status=status.HTTP_200_OK)
		
		