import os
import shutil
import subprocess
import re
import json
from pathlib import Path
from urllib.parse import quote_plus
from core.webapps import open_website
    
# Handle drives, absolute paths, and special shell folders 
def open_path_or_shell(target:str)->str:
  t=target.strip().replace("/","\\")
  t_l=t.lower()
  # Detect if user asked to create folder
  create_mode= False
  if t_l.startswith("create folder "):
    create_mode=True
    t=t[len("create folder "):].strip()
    t_l=t_l[len("create folder "):].strip()
  elif t_l.startswith("make folder"):
    create_mode = True
    t = t[len("make folder "):].strip()
    t_l = t_l[len("make folder "):].strip()
  t = t.replace("/", "\\").strip()
  # 1) Absolute paths (D:\..., \\server\share)
  if re.match(r'^[a-zA-Z]:[\\\/]', t) or t.startswith("\\\\"):
    if create_mode:
      try:
        os.makedirs(t, exist_ok=True)
        subprocess.Popen(["explorer.exe", t])
        return f"Folder Created and opened {t}"
      except Exception as e:
        return f"Failed to create folder: {t} ({e})" 
    if os.path.exists(t):
      subprocess.Popen(["explorer.exe",t])
      return f"Opened {t}"
    return f"Path not found: {t}"
  
  # 2) Handle drive letters only when target is literally "D" or "D drive"
  m = re.match(r'^([a-zA-Z])(?::|\s*(?:drive)?(?:[\\\/](.*))?)?$', t_l)
  if m:
    letter = m.group(1).upper()
    subpath = m.group(2).strip().replace("/", "\\") if m.group(2) else ""
    path = f"{letter}:\\{subpath}" if subpath else f"{letter}:\\"
    path = os.path.normpath(path) 
    if create_mode:
      try:
        os.makedirs(path, exist_ok=True)
        subprocess.Popen(["explorer.exe", path])
        return f"Folder Created and opened {path}"
      except Exception as e:
        return f"Failed to create folder: {path} ({e})"
    # Check drive existence
    drive_root = f"{letter}:\\"
    if os.path.exists(drive_root):
      if subpath:
        full_path = f"{drive_root}{subpath}"
        if os.path.exists(full_path):
          subprocess.Popen(["explorer.exe", full_path])
          return f"Opened subfolder {subpath} on {letter} drive"
        else:
          # If subfolder doesn't exist, open drive root or parent
          parent = os.path.dirname(full_path) if os.path.dirname(full_path) != full_path else drive_root
          subprocess.Popen(["explorer.exe", parent])
          return f"Subfolder {subpath} not found on {letter} drive; opened {parent}"
      else:
        subprocess.Popen(["explorer.exe", drive_root])
        return f"Opened {letter} drive"
    return f"Drive {letter} not found"
    
  # 3) Explorer shell folders
  shell_map = {
      "this pc": "shell:MyComputerFolder",
      "my computer": "shell:MyComputerFolder",
      "desktop": "shell:Desktop",
      "downloads": "shell:Downloads",
      "documents": "shell:Personal",
      "pictures": "shell:PicturesLibrary",
      "music": "shell:MusicLibrary",
      "videos": "shell:VideosLibrary",
      "control panel": "shell:ControlPanelFolder",
      "recycle bin": "shell:RecycleBinFolder",
      "calculator": "shell:AppsFolder\\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
  }
  
  if t_l in shell_map:
    subprocess.Popen(["explorer.exe",shell_map[t_l]])
    return f"Opened {t.title()}"
  
  # If folder creation requested, create relative folder
  if create_mode:
    path = os.path.join(os.getcwd(), t)
    try:
      os.makedirs(path, exist_ok=True)
      subprocess.Popen(["explorer.exe", path])
      return f"Folder Created and opened {path}"
    except Exception as e:
      return f"Failed to create folder: {path} ({e})"

  return ""

# Aliases for known applications

def _augment_aliases(name_l: str) -> set:
  aliases = {
    name_l,
    name_l.replace(" ", ""),
    name_l + ".exe",
    name_l.replace(" ", "") + ".exe",
  }
  #Chrome
  if any(k in name_l for k in ["chrome", "google"]):
    aliases.update({"chrome", "chrome.exe", "googlechrome","google chrome", "googlechrome.exe"})
  # VLC
  if any(k in name_l for k in ["vlc", "media", "player"]):
    aliases.update({"vlc", "vlc.exe", "videolan", "vlc media player", "vlcmediaplayer"})
  # VS Code
  if any(k in name_l for k in ["visual studio", "vscode", "vs code", "code"]):
    aliases.update({"code", "code.exe", "vscode", "visual studio code"})

  # Calculator common names
  if "calculator" in name_l or name_l in {"calc"}:
    aliases.update({"calc", "calculator"})
  # MS word
  if any(k in name_l for k in ["winword", "word", "ms word", "microsoft word"]):
    aliases.update({"word", "winword.exe", "ms word", "microsoft word"})
  
  # MS excel
  if any(k in name_l for k in ["excel", "ms excel", "microsoft excel"]):
    aliases.update({"excel", "excel.exe", "ms excel", "microsoft excel"})
  
  # Powerpoint
  if "powerpoint" in name_l or "ppt" in name_l:
    aliases.update({"powerpnt", "powerpnt.exe", "microsoft powerpoint"})
  # Notepad++
  if "notepad++" in name_l:
    aliases.update({"notepad++", "notepad++.exe"})
  # Git Bash (common for developers)
  if "git" in name_l:
    aliases.update({"git", "git.exe", "git bash"})
  return aliases


def _search_dirs() -> list: 
  start_menu_all = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs")
  start_menu_user = os.path.join(os.environ.get("APPDATA", ""),r"Microsoft\Windows\Start Menu\Programs")
  code_user = os.path.join(os.environ.get("LOCALAPPDATA", ""),r"Programs\Microsoft VS Code")
  notepadpp = os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Notepad++")
  chrome_user = os.path.join(os.environ.get("LOCALAPPDATA", ""),r"Google\Chrome\Application")
  roots=[
    os.environ.get("ProgramFiles", r"C:\Program Files"),
    os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    code_user,
    chrome_user,
    notepadpp,
    start_menu_all,
    start_menu_user,
  ]
  #Adds D:\ or E:\ or F:\ or G:\ or H:\ roots if they exists (bounded scan will apply)
  for drive in ["D:\\","E:\\","F:\\","G:\\","H:\\"]:
    if os.path.exists(drive):
      roots.extend([drive,os.path.join(drive,"Apps"), os.path.join(drive,"Programs")])
  return roots

# --------------Universal Launcher----------------

def find_and_launch_app(app_name: str)->str:
  name_l = app_name.lower().strip()
  aliases = _augment_aliases(name_l)
  # --- Direct known app paths or URLs ---
  fastmap = {
    #Local apps
    "chrome": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "vlc media player": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "perplexity": r"C:\Users\aniru\AppData\Local\Programs\Perplexity\Perplexity.exe",
    "adobe photoshop": r"C:\Program Files (x86)\Adobe\Photoshop 7.0\Photoshop.exe",
    "microsoft word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "ms word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "microsoft excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "ms excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "ms powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "microsoft powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "notepad++": r"C:\Program Files\Notepad++\notepad++.exe",
    "git bash": r"C:\Program Files\Git\bin\sh.exe",

    # Web apps (open in browser)
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chat.openai.com",
    "openai": "https://chat.openai.com",
    "google": "https://www.google.com",
    "google search": "https://www.google.com",
    # --- System Tools ---
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "clock": "shell:Appsfolder\\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"
  }
  for key, val in fastmap.items():
    if key in name_l:
      if val.lower().startswith("http"):
        return open_website(val)
      elif val.lower().startswith("shell:"):
        subprocess.Popen(["explorer.exe", val])
        return f"Opened {key.title()}"
      elif val.lower().endswith(".exe") or os.path.exists(val):
        subprocess.Popen(val)
        return f"Launched {key.title()}"

  # ---------- 1) PATH / Execution alias (fast) ----------
  # Try several candidate names that often work via PATH/aliases
  for c in list(aliases):
    hit = shutil.which(c)
    if hit:
      subprocess.Popen(hit)
      return f"Launched {app_name}"
  
  # ---------- 2) Common locations incl. Start Menu .lnk ----------
  def file_matches(fl:str)->bool:
    fl_base = os.path.splitext(fl.lower())[0]
    fl_clean = fl_base.replace(" ", "")
    for a in aliases:
      a_base = os.path.splitext(a.lower())[0]
      a_clean = a_base.replace(" ", "")
      if a_clean in fl_clean or fl_clean in a_clean:
        return True
    return False
    
  for root_dir in _search_dirs():
    if not root_dir or not os.path.isdir(root_dir):
      continue
    # shallow on drive roots
    max_depth = 4 if "Users" in root_dir or "AppData" in root_dir else 2
    for root, dirs, files in os.walk(root_dir):
      depth = root[len(root_dir):].count(os.sep)
      if depth > max_depth:
        dirs[:] = []
        continue
      for f in files:
        if file_matches(f):
          path=os.path.join(root,f)
          try:
            if path.lower().endswith((".lnk", ".appref-ms")):
              os.startfile(path)
            else:
              subprocess.Popen(path)
            return f"Launched {app_name}"
          except Exception:
            pass
  
  # Step-3: UWP/Store apps: Get AUMIDs and launch via AppsFolder 
  try:
    ps=[
      "powershell", "-NoProfile", "-Command",
      "(Get-StartApps) | ConvertTo-Json -Compress"
    ]
    out = subprocess.run(ps, capture_output=True, text=True, timeout=5)
    if out.returncode == 0 and out.stdout.strip():
      data = json.loads(out.stdout)
      apps = data if isinstance(data, list) else [data]
      # Simple contains match on display name
      for it in apps:
        disp = (it.get("Name") or it.get("DisplayName") or "").lower()
        aumid = it.get("AppID") or it.get("AppId") or it.get("AppUserModelId") or ""
        if disp and name_l in disp and aumid:
          subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{aumid}"])
          return f"Launched {app_name}"
  except Exception:
    pass
  
  return f"Could not find or launch {app_name}"

class CommandParser:
  def __init__(self, project_root: Path):
    self.project_root=Path(project_root)
  
  def _clean_text(self, text:str) -> str:
    t=text.lower()
    t = re.sub(r"\b(please|could you|would you|hey|hi|hello)\b", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()
    
  def parse_and_execute(self,text:str)->str:
    t=self._clean_text(text)
    verbs = ['open', 'launch', 'start', 'play', 'go to', 'goto','show', 'search', 'run', 'create folder', 'make folder']
    target = t
    for v in verbs:
      if t.startswith(v+ ' '):
        target=t[len(v):].strip()
        verb_used = v
        break
      elif (' ' + v + ' ') in t:
        target=t.split(v,1)[1].strip() 
        verb_used = v
        break
    else:
      verb_used = ""
    
    if not target:
      return "I didn't catch what to open."
    
    # If it starts with create/make folder → handle manually(skip app search)
    if verb_used in ['create folder', 'make folder']:
      handled = open_path_or_shell(f"{verb_used} {target}")
      if handled:
        return handled
      return f"Could not create folder: {target}"
    # 1) Strict URL detection first (http/https/www), not any string with a dot
    if re.match(r"^(https?://|www\.)", target, re.I):
      return open_website(target)

    # 2) Handle drives/absolute paths/shell folders immediately
    handled = open_path_or_shell(target)
    if handled:
      return handled
    
    # 3) Try universal local launcher (PATH, Start Menu, Program Files, UWP/AUMID)
    result = find_and_launch_app(target)
    if not result.startswith("Could not"):
      return result
    
    # 4) Final fallback: web search
    url = f"https://www.google.com/search?q={quote_plus(text)}"
    return open_website(url)

     