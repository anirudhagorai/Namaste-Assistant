def open_website(url:str):
  import webbrowser
  if not url:
    return "No URL provided"
  if not (url.startswith("http://") or url.startswith("https://")):
    if '.' not in url:
      url=f"https://www.{url}.com"
    else:
      url = 'https://' + url
  try:
    webbrowser.open(url,new=2)
    return f"Opened {url}"
  except Exception as e:
    return f"Failed to open {url}: {e}"