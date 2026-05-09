import urllib.request
try:
    ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    print(f"\n[+] Your current Public IP is: {ip}\n")
except Exception as e:
    print(f"Error fetching IP: {e}")
