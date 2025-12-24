#......... Tkinter GUI for the Desktop Assistant...........
import sys
import os
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from tkinter import PhotoImage
import threading
import queue
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
  sys.path.append(str(BASE_DIR))

from core.voice import VoiceAssistant
from core.commands import CommandParser

class AssistantApp(tk.Tk):
  def __init__(self):
    super().__init__()
    icon_path = str(BASE_DIR / "assets"/ "icon.ico")
    try:
      self.iconbitmap(icon_path)
    except Exception:
      pass
    
    self.title("Namaste Assistant")
    self.configure(bg="#f5f5f5")
    #Project root
    self.project_root = BASE_DIR
    #Core modules
    self.voice=VoiceAssistant(hotword="",hotword_enabled=False)
    self.parser=CommandParser(project_root=self.project_root)
    
    #threading/queues
    self.q=queue.Queue()
    self.listening = False
    self.stop_listening=None
    self.listening_mode = "idle"
    self._build_ui()
    self.center_window(600,400)
    
    # Start periodic GUI poll to handle items from worker threads
    self.after(200, self._process_queue)

  def center_window(self, width=600, height=400):
    # Ensure geometry info is current
    self.update_idletasks()
    screen_w = self.winfo_screenwidth()
    screen_h = self.winfo_screenheight()
    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)
    self.geometry(f"{width}x{height}+{x}+{y}")
    
  def _build_ui(self):
    
    # Welcome label (add this as the first widget)
    welcome = ttk.Label(self, text="Welcome to Your Desktop Assistant!", font=("Segoe UI", 25, "bold"), foreground="#1976d2",background="#f5f5f5",anchor="center")
    welcome.pack(side=tk.TOP, fill=tk.X, pady=(10, 5))
    
    # Global ttk style for slightly larger, responsive buttons
    style = ttk.Style(self)
    try:
      style.theme_use("clam")
    except tk.TclError:
      pass
    style.configure(
      "Accent.TButton",
      font=("Segoe UI", 12, "bold"),
      foreground="#ffffff",         # white text
      background="#1976d2",         # blue background
      padding=(16, 12),
      borderwidth=0
    )
    style.map("Accent.TButton",background=[("pressed", "#125ca1"), ("active", "#1565c0")],foreground=[("disabled", "#cccccc")])
    
    # Normal Button Style
    style.configure("TButton",font=("Segoe UI", 12),padding=(12, 8))
    
    # Search Entry style
    style.configure("Search.TEntry", padding=(8, 10))
    # Larger font globally for entries and buttons
    default_font = ("Segoe UI", 12)
    self.option_add("*TEntry*Font", default_font)
    self.option_add("*TButton*Font", default_font)
    
    #Top frame with controls
    top=ttk.Frame(self,padding=8)
    top.pack(side=tk.TOP,fill=tk.X,expand=True) 
    self.once_btn=ttk.Button(top,text="Start Listening",command=self._listen_once,style="Accent.TButton")
    self.once_btn.pack(side=tk.LEFT,padx=4,pady=2,expand=True,fill='x')
    ttk.Button(top, text="Settings", command=self._open_settings, style="Accent.TButton").pack(side=tk.LEFT, padx=4, pady=2, expand=True, fill='x')
    
    #Quick app buttons
    quick=ttk.Frame(self,padding=8)
    quick.pack(side=tk.TOP,fill=tk.X,expand=False)
    
    #Manual command entry
    entry_wrap=ttk.Frame(self,padding=8)
    entry_wrap.pack(side=tk.TOP,fill=tk.X,expand=True)
    entry_frame = ttk.Frame(entry_wrap)
    entry_frame.pack(anchor="center")
    
    entry_frame.columnconfigure(0, weight=1)
    entry_frame.columnconfigure(1, weight=0)
    
    self.cmd_var=tk.StringVar()
    entry = ttk.Entry(entry_frame, textvariable=self.cmd_var, style="Search.TEntry",width=50)
    entry.grid(row=0, column=0, padx=(0, 8), pady=10, sticky="ew")
    entry.bind('<Return>',lambda e: self._on_entry())
    
    go_btn = ttk.Button(entry_frame, text="Go",command=self._on_entry, style="Accent.TButton")
    go_btn.grid(row=0, column=1, padx=(0, 0), pady=10, sticky="e")
    
    #Log area
    log_frame=ttk.Frame(self,padding=8)
    log_frame.pack(side=tk.TOP,fill=tk.BOTH,expand=True)
    self.log = tk.Text(log_frame, wrap=tk.WORD,state=tk.DISABLED, height=18, font=("Consolas", 12))
    self.log.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
    scrollbar=ttk.Scrollbar(log_frame,command=self.log.yview)
    scrollbar.pack(side=tk.RIGHT,fill=tk.Y)
    self.log['yscrollcommand'] = scrollbar.set
    
  def _log(self,text):
    self.log.configure(state=tk.NORMAL)
    self.log.insert(tk.END,text + "\n")
    self.log.configure(state=tk.DISABLED)
    self.log.see(tk.END)
    
  def _on_entry(self):
    text=self.cmd_var.get().strip()
    if not text:
      return
    self.cmd_var.set("")
    self._execute_text(text)
    
  def _execute_text(self,text):
    self._log(f"> {text}")
    # run parsing/execution in background thread to avoid UI freeze
    threading.Thread(target=self._bg_parse_execute,args=(text,), daemon=True).start()
    
  def _bg_parse_execute(self,text):
    try:
      resp=self.parser.parse_and_execute(text)
      self.q.put(resp)
    except Exception as e:
      self.q.put(f"Error: {e}")
  
  def _extract_speakable(self, item: str) -> str:
    # For app launches
    if item.startswith("Launched "):
      return item.replace("Launched ", "").strip()
    # For Store app launches
    if item.startswith("Opened store app"):
      parts = item.split(" ")
      if len(parts) >= 4:
         return parts[-1].strip()
    # For web launches
    if item.startswith("Opened http"):
      # Try to return just the domain
      import re
      match = re.search(r"https?://(www\.)?([^/\s]+)", item)
      if match:
        return match.group(2)
    return "Website"
    # For google search fallback
    if item.startswith("Opened ") and "search?q=" in item:
      # Try to extract query after 'q='
      import urllib.parse
      q_idx = item.find("q=")
      if q_idx != -1:
        query = item[q_idx+2:].replace("+", " ")
        return f"Google search for {query}"
    return item

  def _get_speakable_text(self, item: str) -> str:
    # Handle launched apps: "Launched notepad" → "notepad"
    if item.lower().startswith("launched "):
      return item.split(" ", 1)[1].strip()
    # Handle opened urls: "Opened https://www.youtube.com" → "YouTube"
    if item.lower().startswith("opened http"):
      import re
      match = re.search(r"https?://(www\.)?([^/\s]+)", item)
      if match:
        domain = match.group(2)
        # Make it friendlier (e.g., "youtube.com" → "YouTube")
        base = domain.split(".")[0]
        return base.capitalize()
    # Handle Google search URLs: say only the intent
    if "search?q=" in item:
      query = item.split("search?q=")[-1].replace("+", " ")
      return f'Searching for {query}'
    # Optionally handle UWP/store: "Opened store app key" → "key"
    if item.lower().startswith("opened store app"):
      return item.split("opened store app", 1)[1].strip()
    return item  # fallback, speak as-is

  
  def _process_queue(self):
    try:
      while not self.q.empty():
        item = self.q.get_nowait()
        if item:
          self._log(item)
          if not item.strip().startswith(">"):
            speak_text = self._get_speakable_text(item)
            self.voice.speak(speak_text)
    except Exception as e:
      print(f"Error {e}")
    # re-schedule
    self.after(200, self._process_queue)
    
  def toggle_listening(self):
    if self.listening_mode=="idle":
      self._log(f"Say the hotword to trigger: '{self.voice.hotword}'.")
      self.listen_btn.config(text="Start continuous Listening")
      self.listening_mode = "hotword"
    elif self.listening_mode == "hotword":
      # Second press: start continuous listening
      self._log("Continuous listening started.")
      self.stop_listening = self.voice.start_background_listening(self._on_transcript)
      self.listen_btn.config(text="Stop Listening")
      self.listening_mode = "continuous"
      self.log.delete("1.0", tk.END)
    elif self.listening_mode=="continuous":
      if self.stop_listening:
        self.stop_listening(wait_for_stop=False)
      self._log("Stopped continuous listening.")
      self.listen_btn.config(text="Start Listening")
      self.listening_mode = "idle"
        
  def _listen_once(self):
    self._log("Listen once..")
    threading.Thread(target=self._bg_listen_once, daemon=True).start()
    
  def _bg_listen_once(self):
    txt=self.voice.listen_once()
    if txt:
      self._log(f"Heard: {txt}")
      self._bg_parse_execute(txt)
    else:
      self._log("(no speech captured)")
  
  def _on_transcript(self,transcript):
    self.q.put(f"Heard (BG): {transcript}")
    # parse and execute
    threading.Thread(target=self._bg_parse_execute,args=(transcript,), daemon=True).start()
  
  def _open_settings(self):
    # small settings dialog to toggle hotword and set it
    win = tk.Toplevel(self)
    win.title("Settings")
    win.geometry("420x160")

    hotword_var = tk.StringVar(value=self.voice.hotword)
    hotword_enabled_var = tk.BooleanVar(value=self.voice.   hotword_enabled)


    ttk.Checkbutton(win, text="Enable hotword",variable=hotword_enabled_var).pack(pady=6)
    ttk.Label(win, text="Hotword (phrase):").pack()
    ttk.Entry(win, textvariable=hotword_var, width=40).pack(pady=4)

    def save_settings():
      self.voice.hotword = hotword_var.get().strip().lower()
      self.voice.hotword_enabled = hotword_enabled_var.get()
      self._log(f"Settings updated. Hotword: '{self.voice.hotword}', enabled: {self.voice.hotword_enabled}")
      win.destroy()

    ttk.Button(win, text="Save", command=save_settings).pack(pady=8)
    
    
