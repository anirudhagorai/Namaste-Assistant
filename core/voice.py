import pyttsx3
import threading
import tempfile
import os
from playsound import playsound
import speech_recognition as sr

class VoiceAssistant:
  def __init__(self, hotword:str="",hotword_enabled:bool=False):
    self.recognizer=sr.Recognizer()
    self.microphone=sr.Microphone()
    #hotword
    self.hotword=hotword.lower() if hotword else ""
    self.hotword_enabled=hotword_enabled
    #hold stop function for background listening
    self._stop_listening_fn=None
    #small ambient noise adjustment
    try:
      with self.microphone as source:
        self.recognizer.adjust_for_ambient_noise(source,duration=1)
    except Exception:
      pass
  
  def speak(self, text: str):
    def _run():
      engine = pyttsx3.init()
      engine.setProperty('rate', 180)
      engine.say(text)
      engine.runAndWait()
      engine.stop()
    threading.Thread(target=_run, daemon=True).start()
    
  def listen_once(self,timeout:int=5,phrase_time_limit:int=8)->str:
    """Listen once (blocking) and return recognized text, or empty string."""
    try:
      with self.microphone as source:
        audio=self.recognizer.listen(source,timeout=timeout,phrase_time_limit=phrase_time_limit)
      try:
        text=self.recognizer.recognize_google(audio)
        return text
      except sr.UnknownValueError:
        return ""
      except sr.RequestError:
        return ""
    except Exception:
      return ""
    
  def _internal_callback(self,recognizer,audio,user_callback=None):
    try:
      text=recognizer.recognize_google(audio)
    except sr.UnknownValueError:
      return
    except sr.RequestError:
      return
    if not text:
      return
    
    if not self.hotword_enabled and user_callback:
      user_callback(text)
  
  def start_background_listening(self,user_callback):
    if self._stop_listening_fn:
      return self._stop_listening_fn
    
    def callback(recognizer,audio):
      try:
        self._internal_callback(recognizer,audio,user_callback)
      except Exception:
        pass
    self._stop_listening_fn=self.recognizer.listen_in_background(self.microphone,callback)
    return self._stop_listening_fn
  
  def stop_background(self):
    if self._stop_listening_fn:
      self._stop_listening_fn(wait_for_stop=False)
      self._stop_listening_fn=None
          