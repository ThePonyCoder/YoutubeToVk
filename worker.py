#!/usr/bin/env python3
import json
import os
import re
import threading
import time
from pprint import pprint
import webbrowser

import requests

from collections import deque
import subprocess as sp


class Worker:
    def __init__(self, link, edit_data, token=None):
        """
        edit_data example :
        edit_data = {
            'artist': self.artistEdit.text(),
            'title': self.titleEdit.text(),
            'text': self.lyricsEdit.toPlainText()
        }"""
        self.link = self.youtube_url_validation(link)
        self.edit_data = edit_data
        self.token = self.get_token()
        self.path = 'load'
        self.get_token_url = 'https://oauth.vk.com/authorize?client_id=6031099' \
                             '&scope=audio,status,friends,offline&response_type=token&v=5.95'

        self.test_auth()

        if self.link:
            self.setstatus('[info] Link is correct')
            self.start_work()
        else:
            self.setstatus('[error] Link is incorrect')

    @staticmethod
    def get_token():
        if not os.path.isfile('token.txt'):
            open('token.txt', 'w').close()
        with open('token.txt', 'r') as f:
            return f.read().strip()

    def test_auth(self):
        testAuth = self.do_request('account.getProfileInfo')
        if 'error' in testAuth:
            self.setstatus(
                'Auth is incorrect.\nAccept access from youtubetovk than '
                'paste to console '
                'link from adress '
                'bar '
                'or\nwrite your token in "token.txt"')
            webbrowser.open(self.get_token_url)
            self.token = input('PASTE HERE:\n')
            self.token = re.findall('access_token=.*&expires_in', self.token)[
                0][13:-11]
            print(self.token)
            if 'error' not in self.do_request('account.getProfileInfo'):
                self.setstatus('Auth successful')
                with open('token.txt', 'w') as f:
                    f.write(self.token)
                self.setstatus('Token was written to token.txt')
            else:
                self.alert_err(
                    'Still incorrect token!\nWrite your token in "token.txt"',
                    iscritical=True)
                exit(0)
        else:
            self.setstatus('[auth] Auth successful')

    def check_token(self):
        pass

    def start_work(self):
        self.setstatus('[info] Downloading song')
        self.download_song()

    def download_song(self):
        # cmd = 'tools/youtube-dl.exe --extract-audio ' \
        #       '--audio-format mp3 --audio-quality 320k -f bestaudio ' \
        #       '--youtube-include-dash-manifest --write-info-json ' \
        #       '-o "load/{self.link}.%(ext)s" ' + link
        downloading = False

        def update_donwload_status():
            while downloading:
                try:
                    self.setstatus(
                        self.main_process.stdout.__next__().decode().strip())
                    time.sleep(0.2)
                except StopIteration:
                    break

        downloading = True

        self.main_process = sp.Popen([
            'youtube-dl',
            '--extract-audio', '-k',
            '--audio-format', 'mp3',
            '--audio-quality', '320k',
            '-f bestaudio',
            '--youtube-include-dash-manifest',
            '--write-info-json',
            '-o', f'{self.path}/{self.link}.%(ext)s',
            self.link
        ], stdout=sp.PIPE, stderr=sp.PIPE)
        threading.Thread(target=update_donwload_status).start()
        self.main_process.wait()
        downloading = False

        if os.path.isfile(f'{self.path}/{self.link}.mp3'):
            self.setstatus('[info] Downloaded')
            self.upload_song()
        else:
            self.setstatus('[error] Can\'t download song')

    def upload_song(self):
        # getting upload server
        upload_server = self.do_request('audio.getUploadServer')
        file = open(f'{self.path}/{self.link}.mp3', 'rb')

        # uploading audio to the server
        self.setstatus('[info] Uploading to server')
        uploaded_file = requests.post(upload_server['response'][
            'upload_url'],
            files={'file': file}).json()
        del uploaded_file['redirect']
        uploaded_file_data = self.do_request('audio.save', uploaded_file)
        self.setstatus('[info] Uploaded')
        self.edit_song(uploaded_file_data)

    def edit_song(self, uploaded_file_data):
        self.setstatus('[info] Editing song')
        json_metadata = json.load(open(f'load/{self.link}.info.json'))
        if self.edit_data['artist'] == '':
            self.edit_data['artist'] = json_metadata['uploader']
        if self.edit_data['title'] == '':
            self.edit_data['title'] = json_metadata['title']
        if self.edit_data['text'] == '':
            self.edit_data['text'] = json_metadata['description']
        self.edit_data['owner_id'] = uploaded_file_data['response']['owner_id']
        self.edit_data['audio_id'] = uploaded_file_data['response']['id']
        self.setstatus('[info] Edited')
        self.do_request('audio.edit', self.edit_data)
        pprint(self.do_request('audio.edit', self.edit_data))
        self.setstatus(
            '"' + self.edit_data['title'] + ' - ' + self.edit_data[
                'artist'] + '" uploaded successfully')
        self.edit_data.clear()

    @staticmethod
    def youtube_url_validation(url):
        youtube_regex = (
            r'(https?://)?(www\.)?'
            '(youtube|youtu|youtube-nocookie)\.(com|be)/'
            '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

        youtube_regex_match = re.match(youtube_regex, url)
        if youtube_regex_match:
            return youtube_regex_match.group(6)

        return youtube_regex_match

    def setstatus(self, line):
        print(line)

    # doing request to vkApi
    def do_request(self, method, data={}):
        data['access_token'] = self.token
        data['v'] = 5.74
        link = 'https://api.vk.com/method/' + method
        return requests.post(link, data=data).json()


if __name__ == '__main__':
    url = input('URL:').strip()

    artist, title, text = ['', '', '']
    # artist = input('Artist:   (Nothing will get from author)').strip()
    # title = input('Title:    (Nothing will get from video title)').strip()
    # text = input('Lyrics:   (Nothing will get from video description)').strip()
    Worker(url,
           {'artist': artist, 'title': title, 'text': text})
