def run_terminal(app):
    from flask import request, jsonify, render_template_string, session, redirect, url_for
    import subprocess
    import os

    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin2550"

    def get_system_info():
        info = {}
        try:
            info['os'] = subprocess.check_output("lsb_release -d", shell=True).decode().strip().split(":")[1].strip()
            info['host'] = subprocess.check_output("hostname", shell=True).decode().strip()
            info['kernel'] = subprocess.check_output("uname -r", shell=True).decode().strip()
            info['uptime'] = subprocess.check_output("uptime -p", shell=True).decode().strip()
            info['packages'] = subprocess.check_output("dpkg -l | wc -l", shell=True).decode().strip() + " (dpkg)"
            info['shell'] = subprocess.check_output("echo $SHELL", shell=True).decode().strip()
            info['resolution'] = subprocess.check_output("xdpyinfo | grep dimensions", shell=True).decode().strip().split()[1]
            info['de'] = subprocess.check_output("echo $XDG_CURRENT_DESKTOP", shell=True).decode().strip()
            info['wm'] = subprocess.check_output("wmctrl -m | grep Name", shell=True).decode().strip().split(":")[1].strip()
            info['cpu'] = subprocess.check_output("lscpu | grep 'Model name:'", shell=True).decode().strip().split(":")[1].strip()
            info['memory'] = subprocess.check_output("free -m | awk '/Mem:/ {print $3\"MiB / \"$2\"MiB\"}'", shell=True).decode().strip()
            info['gpu'] = subprocess.check_output("lspci | grep -i 'vga'", shell=True).decode().strip()
        except Exception as e:
            info['error'] = str(e)
        return info
    
    def get_prompt(cwd):
        user = os.getlogin() if os.name != 'nt' else os.environ.get("USERNAME", "Unknown")
        venv = os.environ.get("VIRTUAL_ENV")
        env_name = os.path.basename(venv) if venv else ""
        prompt = f"({env_name}) " if env_name else ""
        prompt += f"{user}@{os.uname().nodename}:{cwd}$ "
        return prompt

    LOGIN_FORM = """<!DOCTYPE html>
    <html><head><title>Admin Login</title>
    <style>
        body {
            background-color: black;
            color: #00FF00;
            font-family: monospace;
            padding: 20px;
        }
        .ubuntu-logo {
            white-space: pre;
            font-size: 12px;
            color: #FF6C00;
        }
        input {
            background-color: black;
            color: #00FF00;
            border: 1px solid #00FF00;
            font-family: monospace;
            padding: 4px;
            margin: 4px 0;
        }
        input[type=submit] {
            cursor: pointer;
            font-weight: bold;
        }
        .blink {
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0; }
            100% { opacity: 1; }
        }
    </style>
    </head><body>
    <pre class="ubuntu-logo">
        _______  _______  _______  _______  _______  _______ 
        (  ____ \\(  ____ \\(  ___  )(       )(  ____ )(  ___  )
        | (    \\/| (    \\/| (   ) || () () || (    )|| (   ) |
        | (_____ | |      | (___) || || || || (____)|| |   | |
        (_____  )| |      |  ___  || |(_)| ||     __)| |   | |
                ) || |      | (   ) || |   | || (\\ (   | |   | |
        /\\____) || (____/\\| )   ( || )   ( || ) \\ \\__| (___) |
        \\_______)(_______/|/     \\||/     \\||/   \\__/(_______)
    </pre>
    <h2>Login to <span class="blink">Admin Terminal</span></h2>
    <form method="post" action="/admin_door/login">
        Username: <input name="username"><br>
        Password: <input type="password" name="password"><br>
        <input type="submit" value="Login">
    </form>
    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
    </body></html>"""

    TERMINAL_HTML = """<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Hacker Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
    <style>
        body {
            background: black;
            color: #00FF00;
            font-family: 'VT323', monospace;
            font-size: 1.2em;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            position: relative;
        }

        #terminal-container {
            width: 80%;
        }

        #terminal {
            white-space: pre-wrap;
        }

        .input-line {
            display: flex;
        }

        .prompt {
            flex-shrink: 0;
        }

        #commandInput {
            background-color: black;
            color: #00FF00;
            border: none;
            outline: none;
            font-family: 'VT323', monospace;
            font-size: 1.2em;
            width: 100%;
            caret-color: #00FF00;
        }

        #commandInput::placeholder {
            color: #00FF00;
            opacity: 0.5;
        }

        body, #terminal, .prompt {
            text-shadow: none;
        }

        #neofetch-ascii {
            position: fixed;
            top: 0;
            right: 0;
            background-color: black;
            padding: 10px;
            font-size: 10px;
            white-space: pre;
            z-index: 100;
            text-align: left;
            color: #00FF00;
            border-left: 1px solid #00FF00;
            border-bottom: 1px solid #00FF00;
        }
        #nvtop-output {
            position: fixed;
            bottom: 10px;
            right: 10px;
            color: #00FF00;
            background-color: black;
            border: 1px solid #00FF00;
            padding: 10px;
            font-family: monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
        }

        #neofetch-ascii {
            position: fixed;
            top: 30%;
            right: 0%; /* <<< ปรับจากเดิม (เช่น 10px หรือ 5%) เป็น 25% */
            transform: translateY(-50%);
            font-family: monospace;
            font-size: 20px;
            padding: 10px;
            z-index: 999;
            line-height: 1.3;
            white-space: pre;
            max-width: 8000px;
            overflow-y: auto;

            background: linear-gradient(90deg, red, orange, yellow);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-fill-color: transparent;

            border: none;
        }

    </style>
    </head>
    <body>
        <div id="terminal-container">
            <div id="terminal"></div>
            <div class="input-line">
                <span class="prompt" id="prompt">{{ prompt }}</span>
                <input id="commandInput" autofocus autocomplete="off" spellcheck="false" placeholder="▮">
            </div>
        <div id="neofetch-ascii">
            <pre>
                            .-/+oossssoo+/-.               maybe@maybe
                        `:+ssssssssssssssssss+:`           -----------
                    -  +sssssssssssssssssyyyssss+-         OS: {{ info.os }}
                    .osssssssssssssssssdMMMNysssso.        Host: {{ info.host }}
                   /ssssssssssshdmmNNmmyNMMMMhssssss/      Kernel: {{ info.kernel }}
                  +ssssssssshmydMMMMMMMNddddyssssssss+     Uptime: {{ info.uptime }}
                 /sssssssshNMMMyhhyyyyhmNMMMNhssssssss/    Packages: {{ info.packages }}
                .ssssssssdMMMNhsssssssssshNMMMdssssssss.   Shell: {{ info.shell }}
                +sssshhhyNMMNyssssssssssssyNMMMysssssss+   Resolution: {{ info.resolution }}
                ossyNMMMNyMMhsssssssssssssshmmmhssssssso   DE: {{ info.de }}
                ossyNMMMNyMMhsssssssssssssshmmmhssssssso   WM: {{ info.wm }}
                +sssshhhyNMMNyssssssssssssyNMMMysssssss+   WM Theme: {{ info.wm_theme }}
                .ssssssssdMMMNhsssssssssshNMMMdssssssss.   Theme: {{ info.theme }}
                 /sssssssshNMMMyhhyyyyhdNMMMNhssssssss/    Icons: {{ info.icons }}
                  +sssssssssdmydMMMMMMMMddddyssssssss+     Terminal: {{ info.terminal }}
                   /ssssssssssshdmNNNNmyNMMMMhssssss/      CPU: {{ info.cpu }}
                    .ossssssssssssssssssdMMMNysssso.       GPU: {{ info.gpu }}
                      -+sssssssssssssssssyyyssss+-         GPU: {{ info.gpu2 }}
                        `:+ssssssssssssssssss+:`           Memory: {{ info.memory }}
                            .-/+oossssoo+/-.
            </pre>
        </div>


    <script>
        const terminal = document.getElementById("terminal");
        const input = document.getElementById("commandInput");
        const promptEl = document.getElementById("prompt");
        let history = [], historyIndex = -1;

        input.addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                const command = input.value;
                history.push(command);
                historyIndex = history.length;
                terminal.innerHTML += `<div>${promptEl.textContent}${command}</div>`;
                fetch("/admin_door/terminal", {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ command })
                }).then(res => res.json()).then(data => {
                    if (data.output) {
                        terminal.innerHTML += `<div>${data.output.replace(/\\n/g, "<br>")}</div>`;
                    }
                    promptEl.textContent = data.prompt;
                    input.value = "";
                    window.scrollTo(0, document.body.scrollHeight);
                }).catch(err => {
                    terminal.innerHTML += `<div>Error: ${err}</div>`;
                });
                event.preventDefault();
            } else if (event.key === "ArrowUp") {
                if (historyIndex > 0) { historyIndex--; input.value = history[historyIndex]; }
                event.preventDefault();
            } else if (event.key === "ArrowDown") {
                if (historyIndex < history.length - 1) {
                    historyIndex++; input.value = history[historyIndex];
                } else { input.value = ""; }
                event.preventDefault();
            } else if (event.key === "Tab") {
                event.preventDefault();
                const cmd = input.value.trim();
                if (cmd !== "") {
                    fetch("/admin_door/terminal", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({ command: `ls ${cmd}*` })
                    }).then(res => res.json()).then(data => {
                        let matches = data.output.trim().split("\\n").filter(name => name.startsWith(cmd));
                        if (matches.length === 1) { input.value = matches[0]; }
                        else if (matches.length > 1) {
                            terminal.innerHTML += `<div>${matches.join(" ")}</div>`;
                        }
                        window.scrollTo(0, document.body.scrollHeight);
                    });
                }
            }
        });
    </script>
    </body>
    </html>"""

    @app.route("/admin_door", methods=["GET"])
    def admin_door():
        if not session.get("admin_logged_in"):
            return render_template_string(LOGIN_FORM)
        cwd = session.get("cwd", os.path.expanduser("~"))
        prompt = get_prompt(cwd)
        sysinfo = get_system_info()
        return render_template_string(TERMINAL_HTML, prompt=prompt, info=sysinfo)

    @app.route("/admin_door/login", methods=["POST"])
    def admin_login():
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session["cwd"] = os.path.expanduser("~")
            return redirect(url_for("admin_door"))
        else:
            return render_template_string(LOGIN_FORM, error="Invalid credentials")


    @app.route("/admin_door/terminal", methods=["POST"])
    def terminal():
        if not session.get("admin_logged_in"):
            return jsonify({"output": "Unauthorized. Please login.", "prompt": "$ "}), 401

        command = request.json.get("command")
        cwd = session.get("cwd", os.path.expanduser("~"))

        if command.strip().startswith("cd"):
            parts = command.strip().split(maxsplit=1)
            try:
                if len(parts) == 1 or parts[1] == "~":
                    cwd = os.path.expanduser("~")
                else:
                    new_path = os.path.abspath(os.path.join(cwd, parts[1]))
                    if os.path.isdir(new_path):
                        cwd = new_path
                session["cwd"] = cwd
                return jsonify({"output": "", "cwd": cwd, "prompt": get_prompt(cwd)})
            except Exception as e:
                return jsonify({"output": str(e), "error": True, "cwd": cwd, "prompt": get_prompt(cwd)})

        try:
            result = subprocess.check_output(
                command,
                shell=True,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                universal_newlines=True,
                env=os.environ
            )
            return jsonify({"output": result, "cwd": cwd, "prompt": get_prompt(cwd)})
        except subprocess.CalledProcessError as e:
            return jsonify({"output": e.output, "error": True, "cwd": cwd, "prompt": get_prompt(cwd)})