from __future__ import print_function
import pywhatkit
import speedtest
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import datetime
import pickle
import os.path
import re
import sys
import os
import bs4
import requests
import random
import speech_recognition as sr
import pyttsx3
import pytz
import subprocess
import wikipedia

SCOPES = ['https://www.googleapis.com/auth/calender.readonly']
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAYS_EXTENTIONS = ["rd", "th", "st", "nd"]


def say(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    newVoicerate = 140
    engine.setProperty('rate', newVoicerate)


def get_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
        said = ""
        try:
            said = r.recognize_google(audio)
            print(said)
            # print(r.recognize_google(audio,language='bn-BD'))
        except Exception as e:
            error = [
                "I don't know what you mean",
                "Excuse me?",
                "Can you repeat it please?"
            ]
            print("Exception: " + str(random.choice(error)))
    return said.lower()


def google_authenticationCalender():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentialsaa.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


def get_events(day, service):
    # Call the Calendar API
    date = datetime.datetime.combine(day, datetime.datetime.min.time())
    end_date = datetime.datetime.combine(day, datetime.datetime.max.time())
    utc = pytz.UTC
    date = date.astimezone(utc)
    end_date = end_date.astimezone(utc)

    events_result = service.events().list(calendarId='primary', timeMin=date.isoformat(), timeMax=end_date.isoformat(),
                                          singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        pyttsx3.speak('No upcoming events found.')
    else:
        pyttsx3.speak(f"You have {len(events)} events on this day.")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])
            start_time = str(start.split("T")[1].split("-")[0])
            if int(start_time.split(":")[0]) < 12:
                start_time = start_time + "am"
            else:
                start_time = str(int(start_time.split(":")[0]) - 12) + start_time.split(":")[1]
                start_time = start_time + "pm"
            pyttsx3.speak(event["summary"] + "at" + start_time)


def get_time():
    currenTime = datetime.datetime.now()  # .srtftime('%I:%M %p')
    # print("\n " + currenTime + "\n")
    print(str(currenTime))
    if 5 < currenTime.hour < 12:
        pyttsx3.speak('Good morning')
    elif 12 <= currenTime.hour < 18:
        pyttsx3.speak('Good afternoon')
    elif 18 < currenTime.hour <= 24:
        pyttsx3.speak('Good evening')
    else:
        pyttsx3.speak("You must sleep")
        print("You must sleep")


def get_date(text):
    text = text.lower()
    today = datetime.date.today()

    if text.count("today") > 0:
        return today
    day = -1
    day_of_week = -1
    month = -1
    year = today.year

    for word in text.split():
        if word in MONTHS:
            month = MONTHS.index((word)) + 1
        elif word in DAYS:
            day_of_week = DAYS.index(word)
        elif word.isdigit():
            day = int(word)
        else:
            for ext in DAYS_EXTENTIONS:
                found = word.find(ext)
                if found > 0:
                    try:
                        day = int(word[:found])
                    except:
                        pass

    if month < today.month and month != -1:
        year = year + 1
    if day < today.day and month == -1 and day != -1:
        month = month + 1
    if month == -1 and day == -1 and day_of_week != -1:
        current_day_of_week = today.weekday()
        diff = day_of_week - current_day_of_week
        if diff < 0:
            diff += 7
            if text.count("next") >= 1:
                diff += 7
        return today + datetime.timedelta(diff)
    if month == -1 or day == -1:
        return None
    return datetime.datetime(month=month, day=day, year=year)


def note(text):
    date = datetime.datetime.now()
    file_name = str(date).replace(":", "-") + "-note.txt"
    with open(file_name, "w") as f:
        f.write(text)
    subline = "C:\Windows\system32\notepad.exe"
    subprocess.Popen(["notepad.exe", file_name])


def google_Search():
    reg_ex = re.search('open google and search(.*)', text)
    search_for = text.split("search", 1)[1]
    url = 'https://www.google.com/'
    if reg_ex:
        subgoogle = reg_ex.group(1)
        url = url + '/r' + subgoogle
    pyttsx3.speak("Searching. Please give me a moment")
    # driver = webdriver.Firefox(executable_path='/path/to/geckodriver')  *** code for firfox. having default browser***
    driver = webdriver.Chrome(executable_path=r'C:\Users\USER_NAME\AppData\Local\Programs\Python\Python38-32'
                                              r'\chromedriver.exe') #USER_NAME must be the computer user name.
    driver.get('https://www.google.com')
    search = driver.find_element_by_name('q')
    search.send_keys(str(search_for))
    search.send_keys(Keys.RETURN)


def wikisearch():
    reg_ex = re.search('search in wikipedia(.+)', text)
    if reg_ex:
        query = text.split()
        response = requests.get("https://en.wikipedia.org/wiki/" + query[3])

        if response is not None:
            html = bs4.BeautifulSoup(response.text, 'html.parser')
            title = html.select("#firstHeading")[0].text
            paragraphs = html.select("p")
            for para in paragraphs:
                print(para)
            intro = '\n'.join([para.text for para in paragraphs[0:5]])
            print(intro)


def wikisummary():
    look_in = text.replace("tell me about", '')
    info = wikipedia.summary(look_in, 3)
    print(info)
    pyttsx3.speak(info)




def playsong():
    music_dir = r"DIRECTORY"  #***ADD AUDIO DIRECTORY***
    songs = os.listdir(music_dir)
    file_count = len(songs)
    i = random.randrange(0, file_count)
    os.startfile(os.path.join(music_dir, songs[i]))


def internetspeed():
    test = speedtest.Speedtest()
    down = (test.download() / 1024) / 1024
    upload = (test.upload() / 1024) / 1024
    print(f"Download Speed: {down}Mbps")
    print(f"Upload Speed :{upload}Mbps")


def youtuber():
    song = text.replace("web play", '')
    pyttsx3.speak('playing' + song)
    pywhatkit.playonyt(song)


Wake = "comrade"

service = google_authenticationCalender()

print("Listening")
while True:
    text = get_audio()
    if text.count(Wake) > 0:
        pyttsx3.speak("Command")
        text = get_audio()
        greet = ["hello", "hi comrade", "greetings comrade"]
        for phrase in greet:
            if phrase in text:
                pyttsx3.speak("Hello.\n")
                get_time()

        intro = ["who are you", 'what is your meaning', 'tell about yourself']
        for phrase in intro:
            if phrase in text:
                print("I am ComRade\n")
                pyttsx3.speak("I am ComRade. ")
                identity="I am not any military of soviet union or USSR. I am a voice assistant."
                print(identity)
                pyttsx3.speak(identity)

        open_googleSearching = ["open google and search"]
        for phrase in open_googleSearching:
            if phrase in text:
                google_Search()

        wikip = ["search in wikipedia"]
        for phrase in wikip:
            if phrase in text:
                wikisearch()
        # applanch=['launch']
        # for phrase in applanch:
        # if phrase in text:
        # applaunch()
        plm = ['play music', 'i want to listen music', 'can you play some music']
        for phrase in plm:
            if phrase in text:
                playsong()
        aim = ["what is your aim", "what can you do", "what is your positive side"]
        for phrase in aim:
            if phrase in text:
                pyttsx3.speak("My aim is to help you by listening you. I can work hard to help you.")
        CALENDAR_SRTS = ["what do I have", "do I have plans", "am I busy"]
        for phrase in CALENDAR_SRTS:
            if phrase in text.lower():
                date = get_date(text)
                if date:
                    get_events(date, service)
                else:
                    pyttsx3.speak("Pardon please. I did not understand you.")
        NOTE_STRS = ["make a note", "write this down", "remember this", "memorise it"]
        for phrase in NOTE_STRS:
            if phrase in text:
                pyttsx3.speak("What would you like to me to write down")
                note_text = get_audio()
                note(note_text)
                pyttsx3.speak("I have made a note of that.")
        SpeedNet = ["check the internet speed", "check internet", "show internet speed"]
        for phrase in SpeedNet:
            if phrase in text:
                hh = "Checking the Internet Speed"
                pyttsx3.speak(hh)
                internetspeed()
        youtub = ["YouTube play", "web play"]
        for phrase in youtub:
            if phrase in text:
                youtuber()
        wikiquestion = ["tell me about"]
        for phrase in wikiquestion:
            if phrase in text:
                wikisummary()
        Ext = ["bye", "stop", "you may stop"]
        for phrase in Ext:
            if phrase in text:
                txt = "Bye. See you again."
                pyttsx3.speak(txt)
                print(":::\n"
                      ":::::\n", txt)
                sys.exit()
