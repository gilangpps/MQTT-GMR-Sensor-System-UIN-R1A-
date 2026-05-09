# GMR UIN R1A - MQTT Publisher
# Update patch: 2026-05-08

import serial
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import pandas as pd
import paho.mqtt.client as mqtt
import sys

# ============================================================
# DETEKSI PLATFORM
# ============================================================
if sys.platform.startswith("win"):
    DEFAULT_PORT = "COM3"
elif sys.platform.startswith("linux"):
    DEFAULT_PORT = "/dev/ttyUSB0"
else:
    DEFAULT_PORT = "/dev/tty.usbserial-0001"

BAUD_RATE         = 9600
MQTT_BROKER       = "localhost"
MQTT_PORT         = 1883
MQTT_TOPIC_DATA   = "gmr/data"
MQTT_TOPIC_STATUS = "gmr/status"
MQTT_CLIENT_ID    = "GMR-Publisher"

def tegangan_ke_b(v):
    return 5.3381 * v - 4.2983

# ============================================================
# STATE GLOBAL
# ============================================================
data_waktu     = []
data_b         = []
collecting     = False
start_time     = None
ser            = None
mqtt_client    = None
mqtt_connected = False

# ============================================================
# WARNA
# ============================================================
BG      = "#f0f4f8"
PANEL   = "#ffffff"
ACCENT  = "#0077b6"
GREEN   = "#2d9e5f"
RED     = "#e63946"
YELLOW  = "#f4a40a"
TEXT    = "#1a1a2e"
SUBTEXT = "#5a6a7a"
DIVIDER = "#cbd5e1"

# ============================================================
# MQTT
# ============================================================
def on_mqtt_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        update_mqtt_status("Terhubung", GREEN)
        client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "publisher_online"}), retain=True)
    else:
        mqtt_connected = False
        update_mqtt_status(f"Gagal rc={rc}", RED)

def on_mqtt_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    update_mqtt_status("Terputus", RED)

def connect_mqtt():
    global mqtt_client, MQTT_BROKER, MQTT_PORT
    MQTT_BROKER = broker_var.get().strip()
    try:
        MQTT_PORT = int(mqttport_var.get().strip())
    except ValueError:
        log("Port MQTT tidak valid.")
        return
    try:
        if mqtt_client:
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            except: pass
        mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
        mqtt_client.on_connect    = on_mqtt_connect
        mqtt_client.on_disconnect = on_mqtt_disconnect
        mqtt_client.will_set(MQTT_TOPIC_STATUS, json.dumps({"status": "publisher_offline"}), retain=True)
        mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        log(f"Menghubungkan MQTT ke {MQTT_BROKER}:{MQTT_PORT}...")
    except Exception as e:
        update_mqtt_status("Error", RED)
        log(f"Error MQTT: {e}")

def publish_data(t, v, b):
    if mqtt_client and mqtt_connected:
        payload = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "t_s":  round(t, 4),
            "v_V":  round(v, 4),
            "b_mT": round(b, 4)
        })
        mqtt_client.publish(MQTT_TOPIC_DATA, payload, qos=1)

# ============================================================
# SERIAL
# ============================================================
def connect_serial():
    global ser
    port = port_var.get().strip()
    try:
        baud = int(baud_var.get())
    except ValueError:
        log("Baud rate tidak valid.")
        return
    try:
        if ser and ser.is_open:
            ser.close()
        ser = serial.Serial(port, baud, timeout=1)
        ser.flush()
        update_serial_status("Terhubung", GREEN)
        log(f"Serial: {port} @ {baud}")
    except Exception as e:
        ser = None
        update_serial_status("Gagal", RED)
        log(f"Error serial: {e}")

# ============================================================
# GUI HELPERS
# ============================================================
def update_mqtt_status(text, color):
    try: lbl_mqtt_status.config(text=text, fg=color)
    except: pass

def update_serial_status(text, color):
    try: lbl_serial_status.config(text=text, fg=color)
    except: pass

def log(msg):
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        txt_log.config(state=tk.NORMAL)
        txt_log.insert(tk.END, f"[{ts}] {msg}\n")
        txt_log.see(tk.END)
        txt_log.config(state=tk.DISABLED)
    except: pass

# ============================================================
# KONTROL
# ============================================================
def mulai():
    global collecting, start_time
    if ser is None or not ser.is_open:
        messagebox.showwarning("Peringatan", "Hubungkan serial port terlebih dahulu.")
        return
    collecting = True
    if start_time is None:
        start_time = datetime.now()
    log("▶ Akuisisi dimulai")
    if mqtt_connected:
        mqtt_client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "collecting"}))

def berhenti():
    global collecting
    collecting = False
    log("Akuisisi dihentikan")
    if mqtt_connected and mqtt_client:
        mqtt_client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "stopped"}))

def reset_data():
    global data_waktu, data_b, start_time, collecting
    collecting = False
    data_waktu.clear(); data_b.clear()
    start_time = None
    line.set_data([], [])
    ax.relim(); ax.autoscale_view(); canvas.draw()
    log("Data direset.")
    lbl_count.config(text="0 sampel")
    lbl_last_b.config(text="B = - mT")
    lbl_last_v.config(text="V = - V")

def simpan_excel():
    if not data_waktu:
        messagebox.showwarning("Peringatan", "Belum ada data.")
        return
    fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
    if fp:
        try:
            pd.DataFrame({"t (s)": data_waktu, "B (mT)": data_b}).to_excel(fp, index=False)
            log(f"Excel: {fp}")
        except Exception as e:
            messagebox.showerror("Gagal", str(e))

def simpan_gambar():
    fp = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
    if fp:
        fig.savefig(fp, dpi=150)
        log(f"Gambar: {fp}")

def keluar():
    if messagebox.askokcancel("Keluar", "Yakin ingin keluar?"):
        berhenti()
        if mqtt_client:
            try:
                mqtt_client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "publisher_offline"}), retain=True)
                mqtt_client.loop_stop(); mqtt_client.disconnect()
            except: pass
        try:
            if ser and ser.is_open: ser.close()
        except: pass
        root.destroy()

# ============================================================
# ANIMASI
# ============================================================
def update(frame):
    global start_time
    if collecting and ser and ser.is_open:
        try:
            if ser.in_waiting:
                baris    = ser.readline().decode("utf-8").strip()
                tegangan = float(baris)
                b_mT     = tegangan_ke_b(tegangan)
                if start_time is None:
                    start_time = datetime.now()
                waktu = (datetime.now() - start_time).total_seconds()
                data_waktu.append(waktu); data_b.append(b_mT)
                publish_data(waktu, tegangan, b_mT)
                log(f"t={waktu:.2f}s V={tegangan:.4f} B={b_mT:.4f}mT")
                lbl_count.config(text=f"{len(data_waktu)} sampel")
                lbl_last_b.config(text=f"B = {b_mT:.4f} mT")
                lbl_last_v.config(text=f"V = {tegangan:.4f} V")
                line.set_data(data_waktu, data_b)
                ax.relim(); ax.autoscale_view(); canvas.draw()
        except Exception as e:
            log(f"Error: {e}")
    return line,

# ============================================================
# ROOT WINDOW
# ============================================================
root = tk.Tk()
root.title("GMR UIN R1A - MQTT Publisher")
root.configure(bg=BG)
root.resizable(True, True)

try:
    root.state("zoomed")
except tk.TclError:
    try:
        root.attributes("-zoomed", True)
    except tk.TclError:
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")

# HEADER
frm_hdr = tk.Frame(root, bg=ACCENT, pady=6)
frm_hdr.pack(fill=tk.X)
tk.Label(frm_hdr, text="GMR UIN R1A", font=("Courier New", 16, "bold"),
         bg=ACCENT, fg="#ffffff").pack(side=tk.LEFT, padx=14)
tk.Label(frm_hdr, text="MQTT PUBLISHER", font=("Courier New", 9),
         bg=ACCENT, fg="#ffffff").pack(side=tk.LEFT)

# MAIN
frm_main = tk.Frame(root, bg=BG)
frm_main.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

# Kolom kiri: plot
frm_left = tk.Frame(frm_main, bg=BG)
frm_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

fig, ax = plt.subplots(facecolor="#ffffff")
ax.set_facecolor("#f8fafc")
ax.set_title("Medan Magnet vs Waktu", color=TEXT, fontsize=10, pad=6)
ax.set_xlabel("Waktu, t (s)", color=SUBTEXT, fontsize=9)
ax.set_ylabel("Medan Magnet, B (mT)", color=SUBTEXT, fontsize=9)
ax.tick_params(colors=SUBTEXT)
for sp in ax.spines.values(): sp.set_color(DIVIDER)
ax.grid(True, color="#e2e8f0", linewidth=0.7)
line, = ax.plot([], [], lw=2, color=ACCENT)
canvas = FigureCanvasTkAgg(fig, master=frm_left)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Kolom kanan: scrollable
frm_ro = tk.Frame(frm_main, bg=BG, width=270)
frm_ro.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
frm_ro.pack_propagate(False)

cv = tk.Canvas(frm_ro, bg=BG, highlightthickness=0)
sb = tk.Scrollbar(frm_ro, orient=tk.VERTICAL, command=cv.yview)
cv.configure(yscrollcommand=sb.set)
sb.pack(side=tk.RIGHT, fill=tk.Y)
cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

frm_right = tk.Frame(cv, bg=BG)
wid = cv.create_window((0, 0), window=frm_right, anchor="nw")

frm_right.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
cv.bind("<Configure>",        lambda e: cv.itemconfig(wid, width=e.width))
cv.bind("<MouseWheel>",       lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))
cv.bind("<Button-4>",         lambda e: cv.yview_scroll(-1, "units"))
cv.bind("<Button-5>",         lambda e: cv.yview_scroll(1, "units"))

# ============================================================
# HELPER WIDGETS
# ============================================================
def section(title):
    f = tk.Frame(frm_right, bg=PANEL)
    f.pack(fill=tk.X, pady=(0, 5))
    tk.Label(f, text=f"  {title}", font=("Courier New", 7, "bold"),
             bg=PANEL, fg=SUBTEXT).pack(anchor=tk.W, pady=(4, 1))
    tk.Frame(f, bg=DIVIDER, height=1).pack(fill=tk.X, padx=6, pady=(0, 4))
    return f

def lbl(p, t):
    tk.Label(p, text=t, bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=8)

def ent(p, var, col=None):
    c = col or ACCENT
    e = tk.Entry(p, textvariable=var, bg="#f1f5f9", fg=c,
                 font=("Courier New", 9), relief=tk.FLAT, bd=3, insertbackground=c)
    e.pack(fill=tk.X, padx=8, pady=2)
    return e

def mkbtn(p, text, cmd, bg, fg=TEXT, **kw):
    return tk.Button(p, text=text, command=cmd, bg=bg, fg=fg,
                     font=("Courier New", 8, "bold"), relief=tk.FLAT,
                     cursor="hand2", pady=6, **kw)

# ============================================================
# PANEL: SERIAL
# ============================================================
pnl_s = section("SERIAL PORT")
lbl(pnl_s, "Port")
port_var = tk.StringVar(value=DEFAULT_PORT)
ent(pnl_s, port_var)

if sys.platform.startswith("linux"):
    frm_sc2 = tk.Frame(pnl_s, bg=PANEL)
    frm_sc2.pack(fill=tk.X, padx=8, pady=(0, 2))
    tk.Label(frm_sc2, text="Shortcut:", bg=PANEL, fg=SUBTEXT,
             font=("Courier New", 7)).pack(side=tk.LEFT)
    for p in ["/dev/ttyUSB0", "/dev/ttyACM0"]:
        tk.Button(frm_sc2, text=p.split("/")[-1],
                  command=lambda x=p: port_var.set(x),
                  bg=DIVIDER, fg=TEXT, font=("Courier New", 7),
                  relief=tk.FLAT, padx=4, cursor="hand2").pack(side=tk.LEFT, padx=2)

lbl(pnl_s, "Baud Rate")
baud_var = tk.StringVar(value=str(BAUD_RATE))
ttk.Combobox(pnl_s, textvariable=baud_var,
             values=["9600","19200","38400","57600","115200"],
             font=("Courier New", 8)).pack(fill=tk.X, padx=8, pady=2)

frm_sc = tk.Frame(pnl_s, bg=PANEL)
frm_sc.pack(fill=tk.X, padx=8, pady=(4, 6))
tk.Button(frm_sc, text="Hubungkan", command=connect_serial,
          bg=ACCENT, fg="#ffffff", font=("Courier New", 8, "bold"),
          relief=tk.FLAT, cursor="hand2", padx=6).pack(side=tk.LEFT)
lbl_serial_status = tk.Label(frm_sc, text="Belum", bg=PANEL, fg=RED, font=("Courier New", 7))
lbl_serial_status.pack(side=tk.LEFT, padx=6)

# ============================================================
# PANEL: MQTT
# ============================================================
pnl_m = section("MQTT BROKER")
lbl(pnl_m, "Broker IP / Hostname")
broker_var = tk.StringVar(value=MQTT_BROKER)
ent(pnl_m, broker_var)
lbl(pnl_m, "Port")
mqttport_var = tk.StringVar(value=str(MQTT_PORT))
ent(pnl_m, mqttport_var)

frm_mc = tk.Frame(pnl_m, bg=PANEL)
frm_mc.pack(fill=tk.X, padx=8, pady=(4, 2))
tk.Button(frm_mc, text="Hubungkan", command=connect_mqtt,
          bg=YELLOW, fg="#1a1a2e", font=("Courier New", 8, "bold"),
          relief=tk.FLAT, cursor="hand2", padx=6).pack(side=tk.LEFT)
lbl_mqtt_status = tk.Label(frm_mc, text="Belum", bg=PANEL, fg=RED, font=("Courier New", 7))
lbl_mqtt_status.pack(side=tk.LEFT, padx=6)
tk.Label(pnl_m, text=f"Topic: {MQTT_TOPIC_DATA}", bg=PANEL, fg=SUBTEXT,
         font=("Courier New", 7)).pack(anchor=tk.W, padx=8, pady=(0, 5))

# ============================================================
# PANEL: LIVE DATA
# ============================================================
pnl_l = section("LIVE DATA")
lbl_last_b = tk.Label(pnl_l, text="B = - mT", bg=PANEL, fg=ACCENT,
                       font=("Courier New", 13, "bold"))
lbl_last_b.pack(pady=(2, 0))
lbl_last_v = tk.Label(pnl_l, text="V = - V", bg=PANEL, fg=TEXT,
                       font=("Courier New", 9))
lbl_last_v.pack()
lbl_count = tk.Label(pnl_l, text="0 sampel", bg=PANEL, fg=SUBTEXT,
                      font=("Courier New", 8))
lbl_count.pack(pady=(1, 6))

# ============================================================
# PANEL: KONTROL
# ============================================================
pnl_c = section("KONTROL")

fb1 = tk.Frame(pnl_c, bg=PANEL)
fb1.pack(fill=tk.X, padx=8, pady=(0, 3))
mkbtn(fb1, "START",  mulai,    GREEN,  "#ffffff").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
mkbtn(fb1, "STOP",   berhenti, YELLOW, "#1a1a2e").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

fb2 = tk.Frame(pnl_c, bg=PANEL)
fb2.pack(fill=tk.X, padx=8, pady=(0, 3))
mkbtn(fb2, "RESET", reset_data,    "#e2e8f0").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
mkbtn(fb2, "EXCEL", simpan_excel,  "#e2e8f0").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
mkbtn(fb2, "IMAGE", simpan_gambar, "#e2e8f0").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

fb3 = tk.Frame(pnl_c, bg=PANEL)
fb3.pack(fill=tk.X, padx=8, pady=(0, 8))
mkbtn(fb3, "KELUAR", keluar, RED, "#ffffff").pack(fill=tk.X)

# ============================================================
# PANEL: LOG
# ============================================================
pnl_lg = section("LOG OUTPUT")
txt_log = tk.Text(pnl_lg, height=7, bg="#f1f5f9", fg=ACCENT,
                  font=("Courier New", 7), state=tk.DISABLED,
                  relief=tk.FLAT, bd=3, wrap=tk.WORD)
txt_log.pack(fill=tk.X, padx=6, pady=(0, 6))

# ============================================================
# RUN
# ============================================================
ani = animation.FuncAnimation(fig, update, interval=100, cache_frame_data=False)
root.protocol("WM_DELETE_WINDOW", keluar)
log(f"Platform: {sys.platform} | Port default: {DEFAULT_PORT}")
log("Hubungkan Serial & MQTT, lalu tekan START.")
root.mainloop()
# signed by: Gilang Pratama Putra Siswanto (2026-05-08)
