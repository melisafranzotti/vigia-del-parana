#!/usr/bin/env python3
"""Actualiza el ?v= de app.js/app.css en index.html y el nombre del cache en sw.js.
Correr después de cambiar app.js o app.css, antes de commitear."""
import re, hashlib, os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
h=hashlib.sha1(open(os.path.join(R,"app.js"),"rb").read()+open(os.path.join(R,"app.css"),"rb").read()).hexdigest()[:8]
p=os.path.join(R,"index.html"); s=open(p,encoding="utf-8").read()
s=re.sub(r'href="app\.css(\?v=[^"]*)?"','href="app.css?v=%s"'%h,s); s=re.sub(r'src="app\.js(\?v=[^"]*)?"','src="app.js?v=%s"'%h,s)
open(p,"w",encoding="utf-8").write(s)
p=os.path.join(R,"sw.js"); s=open(p,encoding="utf-8").read()
open(p,"w",encoding="utf-8").write(re.sub(r'var CACHE = "vigia-[^"]*";','var CACHE = "vigia-%s";'%h,s))
print("version",h)
