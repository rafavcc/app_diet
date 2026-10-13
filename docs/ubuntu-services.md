# Run app_diet as Ubuntu services in WSL

This guide registers the backend and frontend as two **systemd services** inside Ubuntu. Systemd is the part of Ubuntu that starts and watches background programs. Think of each service as a small recipe that says which user runs a program, where it runs, and what to do if it crashes.

The commands below use this checkout's current location:

```text
/home/rafavcc/app_diet
```

If you move the project or use another Ubuntu account, update that path and the `User` and `Group` values in both service files.

## Why are there two virtual environments?

That is a reasonable setup. The backend and frontend have separate dependency lists, so each `.venv` can hold the packages its side needs without affecting the other. A virtual environment uses a Python installation as its base, but gives the project its own Python command and installed packages.

You do not need to run `source .venv/bin/activate` in a service. Point systemd directly at the venv's Python executable. This is more reliable because services do not start an interactive shell that reads shell startup files.

## 1. Make sure systemd is enabled in WSL

Recent WSL versions support systemd. In Ubuntu, check whether it is already running as process 1:

Systemd requires WSL 2 and a recent WSL release. From PowerShell, `wsl --version` shows your WSL version; if that command is unavailable, update WSL with `wsl --update`. Microsoft's [WSL systemd guide](https://learn.microsoft.com/en-us/windows/wsl/systemd) has more detail.

```bash
ps -p 1 -o comm=
```

If the output is `systemd`, skip to step 2. Otherwise, open the WSL configuration:

```bash
sudo nano /etc/wsl.conf
```

Add this section. If the file already has a `[boot]` section, add `systemd=true` under that section instead of creating a second one.

```ini
[boot]
systemd=true
```

Save and exit Nano (`Ctrl+O`, `Enter`, `Ctrl+X`). Then, from **Windows PowerShell**, stop WSL completely:

```powershell
wsl --shutdown
```

Open Ubuntu again and check:

```bash
ps -p 1 -o comm=
```

It should now say `systemd`. WSL must be running for its Ubuntu services to run. When WSL starts, systemd starts enabled services; when WSL stops, those services stop too.

## 2. Create the backend service

Create a service file in Ubuntu's system service directory:

```bash
sudo nano /etc/systemd/system/app-diet-backend.service
```

Paste this in:

```ini
[Unit]
Description=app_diet backend API
After=network.target

[Service]
Type=simple
User=rafavcc
Group=rafavcc
WorkingDirectory=/home/rafavcc/app_diet/backend
ExecStart=/home/rafavcc/app_diet/backend/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

The important pieces:

- `User` and `Group` run the process as your regular Ubuntu account, not as root.
- `WorkingDirectory` sets the backend folder as the process's current folder.
- `ExecStart` runs Uvicorn using the backend venv. `main:app` means “import `app` from `main.py`.”
- `Restart=on-failure` asks systemd to try again if the process exits with an error.
- `WantedBy=multi-user.target` lets Ubuntu start it during normal boot when the service is enabled.

The backend reads its settings from `backend/.env` if that file exists. Its default SQLite database is `backend/food_intake.db`.

## 3. Create the frontend service

Create another file:

```bash
sudo nano /etc/systemd/system/app-diet-frontend.service
```

Paste this in:

```ini
[Unit]
Description=app_diet NiceGUI frontend
Wants=app-diet-backend.service
After=app-diet-backend.service

[Service]
Type=simple
User=rafavcc
Group=rafavcc
WorkingDirectory=/home/rafavcc/app_diet/frontend
ExecStart=/home/rafavcc/app_diet/frontend/.venv/bin/python /home/rafavcc/app_diet/frontend/main.py
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=DIET_API=http://127.0.0.1:8000
Environment=FOOD_INTAKE_HOST=127.0.0.1

[Install]
WantedBy=multi-user.target
```

The frontend calls the backend at `127.0.0.1:8000` and listens at `127.0.0.1:8001`. `Wants` and `After` tell Ubuntu to start the backend when starting the frontend, and to start the backend first. If the backend needs a moment to come up, the frontend's health check will retry.

Both addresses use `127.0.0.1`, so the app stays local to this machine. The app currently has no login. Do not change the host to `0.0.0.0` unless you intend to make it reachable from other devices and have added suitable access controls.

## 4. Tell systemd about the files and start the app

Whenever you create or change a service file, run `daemon-reload`. This is like asking systemd to reread its recipes.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now app-diet-backend.service app-diet-frontend.service
```

`enable` means “start this service automatically when Ubuntu boots.” `--now` also starts it immediately, so you do not have to reboot to try it.

Open the app from Windows at:

```text
http://localhost:8001
```

WSL normally forwards localhost ports to Windows. The backend API is at `http://localhost:8000`; its health check is `http://localhost:8000/health`.

## 5. Check, stop, and restart services

See whether a service is running:

```bash
systemctl status app-diet-backend.service
systemctl status app-diet-frontend.service
```

Read recent logs. Add `-f` to keep watching new lines as they arrive; press `Ctrl+C` to stop watching.

```bash
journalctl -u app-diet-backend.service -n 50 --no-pager
journalctl -u app-diet-frontend.service -n 50 --no-pager
journalctl -u app-diet-backend.service -f
```

Restart after changing application code or a service file:

```bash
sudo systemctl restart app-diet-backend.service app-diet-frontend.service
```

After editing a service file, run `sudo systemctl daemon-reload` before the restart. A code-only change does not need `daemon-reload`.

Stop now, but keep automatic startup enabled:

```bash
sudo systemctl stop app-diet-frontend.service app-diet-backend.service
```

Prevent automatic startup and stop now:

```bash
sudo systemctl disable --now app-diet-frontend.service app-diet-backend.service
```

## If something does not start

1. Check the service status and logs using the commands above. The log usually says what failed.
2. Check that the paths in `WorkingDirectory` and `ExecStart` exist:

   ```bash
   ls -l /home/rafavcc/app_diet/backend/.venv/bin/python
   ls -l /home/rafavcc/app_diet/frontend/.venv/bin/python
   ```

3. Try the same commands manually to see Python errors directly:

   ```bash
   cd /home/rafavcc/app_diet/backend
   .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```

   In a second Ubuntu terminal:

   ```bash
   cd /home/rafavcc/app_diet/frontend
   DIET_API=http://127.0.0.1:8000 .venv/bin/python main.py
   ```

4. If port 8000 or 8001 is already occupied by a manually started copy, stop that copy before starting the service.

Once both services are enabled, systemd manages the two Python processes for you. The backend is explicitly launched by **Uvicorn**, while the frontend is launched directly with its venv's Python.
