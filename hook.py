import openai, os, threading, re, datetime
from flask import Flask, request, Response
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

''' message queues format:
    {
        "id" {
            "guard": mutex
            "conversasion" [
                {
                    "ask": "question",
                    "answer": "answer"
                    "time": ""
                },
                ...
            ] # keep up to 20 pairs of q&a
        },
        ...
    }
'''
messageQueues = {}
max_conversation_length = 20
datetime_format = '%Y-%m-%d %H:%M:%S.%f'

if not os.path.exists('conversations.txt'):
    with open('conversations.txt', 'w') as f: pass
else:
    with open('conversations.txt', 'r') as f:
        for line in f:
            time, id, question, answer = line.split('\t')
            
            answer = answer.replace('\\n', '\n').replace('\\t', '\t')
            
            if id not in messageQueues:
                messageQueues[id] = {
                    "guard": threading.Lock(),
                    "conversation": []
                }

            with messageQueues[id]["guard"]:
                messageQueues[id]["conversation"].append({
                    "ask": question,
                    "answer": answer,
                    "time": datetime.datetime.strptime(time, datetime_format)
                })
    
    for id, item in messageQueues.items():
        with item["guard"]:
            item["conversation"] = item["conversation"][-max_conversation_length:]     
                
file_stream = open('conversations.txt', 'a')
stream_guard = threading.Lock()

def renderMessagesQueue(id):
    global messageQueues
    messages = []
    with messageQueues[id]['guard']:
        for item in messageQueues[id]['conversation']:
            messages += [{ 'role': 'user', 'content': item['ask'] }, { 'role': 'assistant', 'content': item['answer'] }]            
    return messages

def getAnswer(id, question):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", # "text-davinci-003", 
        messages = renderMessagesQueue(id) + [{'role': 'user', 'content': question}], 
        temperature=0, max_tokens=150
    )
    
    return response.choices[0].message['content']

def standardize(text):
    return text.strip().replace('\t', '\\t').replace('\r', '\n').replace('\n', '\\n')

def mkpretty(text):
    return text.replace('\\n', '\n').replace('\\t', '\t')

def render_conversation(id):
    global messageQueues
    if id not in messageQueues:
        return ''
    
    conversation = ''
    with messageQueues[id]["guard"]:
        conversation = f'\n{"-" * 50}\n'.join(
            f'**{datetime.datetime.strftime(item["time"], "%Y-%m-%d %H:%M:%S")}**\n**Question:** {mkpretty(item["ask"])}\n**Answer:**{mkpretty(item["answer"])}' 
            for item in messageQueues[id]["conversation"]
        ) 

    return conversation

def enqueue(id, question):
    global messageQueues, stream_guard, file_stream
    if id not in messageQueues:
        messageQueues[id] = {
            "guard": threading.Lock(),
            "conversation": []
        }

    question = standardize(question)
    
    current = datetime.datetime.now()
    
    if (question == '!'):
        return render_conversation(id)
    
    if not len(question):
        return '**{}**\n**System message:** {}'.format(datetime.datetime.strftime(current, "%Y-%m-%d %H:%M:%S"), 'Please give a prompt or command!')
    
    raw_answer = getAnswer(id, question)
    answer = standardize(raw_answer)
    
    with messageQueues[id]["guard"]:
        messageQueues[id]["conversation"].append({
            "ask": question,
            "answer": answer,
            "time": current
        })
        
        if len(messageQueues[id]["conversation"]) > max_conversation_length:
            messageQueues[id]["conversation"] = messageQueues[id]["conversation"][-max_conversation_length:]
    
    with stream_guard:
        file_stream.write(f'{current}\t{id}\t{question}\t{answer}\n')
        file_stream.flush()
        
    return '**{}**\n**Question:** {}\n**Answer:** {}'.format(
        datetime.datetime.strftime(current, "%Y-%m-%d %H:%M:%S"), 
        question, raw_answer
    )

@app.route('/call/', methods=['POST', 'GET'])
def call():
    if request.method == 'POST' and request.get_json()['token'] == os.environ['SECRET']:
        data = request.get_json()
        id, message = data.get('user_name', 'Anonymous'), data.get('text', '!')
        return Response(enqueue(id, message), mimetype='text/plain')

    return {'message': 'hello world!'}, 200

errors_dict = {
    400: 'Bad Request',
    404: 'Not Found',
    500: 'Internal Server Error',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
}

for key, val in errors_dict.items():
    app.register_error_handler(key, lambda e: Response('Code: {}\nType: {}\nDetails: {}'.format(e.code, error_dict[e.code], e.description), mimetype='text/plain'))