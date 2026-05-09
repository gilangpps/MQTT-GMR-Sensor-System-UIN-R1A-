# GMR UIN R1A - MQTT Publisher
# Data Acquisition + MQTT Publisher
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

# ============================================================
# KONFIGURASI
# ============================================================
SERIAL_PORT       = 'COM3'
BAUD_RATE         = 9600

MQTT_BROKER       = 'localhost'
MQTT_PORT         = 1883
MQTT_TOPIC_DATA   = 'gmr/data'
MQTT_TOPIC_STATUS = 'gmr/status'
MQTT_CLIENT_ID    = 'GMR-Publisher'

# ============================================================
# KALIBRASI
# ============================================================
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
        update_mqtt_status(f"Gagal (rc={rc})", RED)

def on_mqtt_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    update_mqtt_status("Terputus", RED)

def connect_mqtt():
    global mqtt_client
    try:
        mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
        mqtt_client.on_connect    = on_mqtt_connect
        mqtt_client.on_disconnect = on_mqtt_disconnect
        mqtt_client.will_set(MQTT_TOPIC_STATUS, json.dumps({"status": "publisher_offline"}), retain=True)
        mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
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
    port = port_var.get()
    baud = int(baud_var.get())
    try:
        ser = serial.Serial(port, baud, timeout=1)
        ser.flush()
        update_serial_status("Terhubung", GREEN)
        log(f"Serial terhubung: {port} @ {baud} baud")
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
# FUNGSI KONTROL
# ============================================================
def mulai():
    global collecting, start_time
    if ser is None or not ser.is_open:
        messagebox.showwarning("Peringatan", "Hubungkan serial port terlebih dahulu.")
        return
    collecting = True
    if start_time is None:
        start_time = datetime.now()
    log("▶ Akuisisi data dimulai")
    if mqtt_connected:
        mqtt_client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "collecting"}))

def berhenti():
    global collecting
    collecting = False
    log("⏸ Akuisisi data dihentikan")
    if mqtt_connected and mqtt_client:
        mqtt_client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "stopped"}))

def reset_data():
    global data_waktu, data_b, start_time, collecting
    collecting = False
    data_waktu.clear()
    data_b.clear()
    start_time = None
    line.set_data([], [])
    ax.relim()
    ax.autoscale_view()
    canvas.draw()
    log("🔄 Data direset")
    lbl_count.config(text="0 sampel")

def simpan_excel():
    if not data_waktu:
        messagebox.showwarning("Peringatan", "Belum ada data untuk disimpan.")
        return
    fp = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Files", "*.xlsx")],
        title="Simpan Data Excel"
    )
    if fp:
        df = pd.DataFrame({'t (s)': data_waktu, 'B (mT)': data_b})
        try:
            df.to_excel(fp, index=False)
            messagebox.showinfo("Sukses", f"Data disimpan:\n{fp}")
            log(f"💾 Excel disimpan: {fp}")
        except Exception as e:
            messagebox.showerror("Gagal", str(e))

def simpan_gambar():
    fp = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG Image", "*.png")],
        title="Simpan Gambar Plot"
    )
    if fp:
        fig.savefig(fp, dpi=150)
        messagebox.showinfo("Sukses", f"Gambar disimpan:\n{fp}")
        log(f"🖼 Gambar disimpan: {fp}")

def keluar():
    if messagebox.askokcancel("Keluar", "Yakin ingin keluar?"):
        berhenti()
        if mqtt_client:
            mqtt_client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "publisher_offline"}), retain=True)
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        try:
            if ser and ser.is_open:
                ser.close()
        except: pass
        root.destroy()

# ============================================================
# ANIMASI PLOT
# ============================================================
def update(frame):
    global start_time
    if collecting and ser and ser.is_open:
        try:
            if ser.in_waiting:
                baris    = ser.readline().decode('utf-8').strip()
                tegangan = float(baris)
                b_mT     = tegangan_ke_b(tegangan)
                if start_time is None:
                    start_time = datetime.now()
                waktu = (datetime.now() - start_time).total_seconds()
                data_waktu.append(waktu)
                data_b.append(b_mT)
                publish_data(waktu, tegangan, b_mT)
                log(f"t={waktu:.2f}s | V={tegangan:.4f}V | B={b_mT:.4f}mT → MQTT ✓")
                lbl_count.config(text=f"{len(data_waktu)} sampel")
                lbl_last_b.config(text=f"B = {b_mT:.4f} mT")
                lbl_last_v.config(text=f"V = {tegangan:.4f} V")
                line.set_data(data_waktu, data_b)
                ax.relim()
                ax.autoscale_view()
                canvas.draw()
        except Exception as e:
            log(f"Error: {e}")
    return line,

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
# ROOT WINDOW
# ============================================================
root = tk.Tk()
root.title("GMR UIN R1A — MQTT Publisher")
root.configure(bg=BG)
root.resizable(True, True)

# Cross-platform maximize
try:
    root.state("zoomed")                          # Windows
except tk.TclError:
    try:
        root.attributes("-zoomed", True)          # Linux GNOME / XFCE
    except tk.TclError:
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.geometry(f"{w}x{h}+0+0")            # fallback universal

# ---- HEADER ----
frm_header = tk.Frame(root, bg=ACCENT, pady=8)
frm_header.pack(fill=tk.X)
tk.Label(frm_header, text="GMR UIN R1A", font=("Courier New", 18, "bold"),
         bg=ACCENT, fg="#ffffff").pack(side=tk.LEFT, padx=16)
tk.Label(frm_header, text="MQTT PUBLISHER", font=("Courier New", 10),
         bg=ACCENT, fg="#ffffff").pack(side=tk.LEFT)

# ---- MAIN AREA ----
frm_main = tk.Frame(root, bg=BG)
frm_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

# -- Kolom kiri: plot --
frm_left = tk.Frame(frm_main, bg=BG)
frm_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

fig, ax = plt.subplots(facecolor="#ffffff")
ax.set_facecolor("#f8fafc")
ax.set_title("Medan Magnet vs Waktu", color=TEXT, fontsize=10, pad=8)
ax.set_xlabel("Waktu, t (s)", color=SUBTEXT, fontsize=9)
ax.set_ylabel("Medan Magnet, B (mT)", color=SUBTEXT, fontsize=9)
ax.tick_params(colors=SUBTEXT)
for sp in ax.spines.values():
    sp.set_color(DIVIDER)
ax.grid(True, color="#e2e8f0", linewidth=0.7)
line, = ax.plot([], [], lw=2, color=ACCENT)

canvas = FigureCanvasTkAgg(fig, master=frm_left)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# -- Kolom kanan: semua panel kontrol + log --
frm_right = tk.Frame(frm_main, bg=BG, width=270)
frm_right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
frm_right.pack_propagate(False)

def panel_section(parent, title):
    f = tk.Frame(parent, bg=PANEL)
    f.pack(fill=tk.X, pady=(0, 8))
    tk.Label(f, text=f" {title}", font=("Courier New", 8, "bold"),
             bg=PANEL, fg=SUBTEXT).pack(anchor=tk.W, padx=6, pady=(6, 2))
    tk.Frame(f, bg=DIVIDER, height=1).pack(fill=tk.X, padx=6, pady=(0, 6))
    return f

# -- Panel: Serial --
pnl_serial = panel_section(frm_right, "SERIAL PORT")
tk.Label(pnl_serial, text="Port", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
port_var = tk.StringVar(value=SERIAL_PORT)
tk.Entry(pnl_serial, textvariable=port_var, bg="#f1f5f9", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)
tk.Label(pnl_serial, text="Baud Rate", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
baud_var = tk.StringVar(value=str(BAUD_RATE))
ttk.Combobox(pnl_serial, textvariable=baud_var,
             values=["9600", "19200", "38400", "57600", "115200"],
             font=("Courier New", 8), width=16).pack(fill=tk.X, padx=10, pady=2)
frm_srow = tk.Frame(pnl_serial, bg=PANEL)
frm_srow.pack(fill=tk.X, padx=10, pady=4)
tk.Button(frm_srow, text="Hubungkan", command=connect_serial, bg=ACCENT,
          fg="#ffffff", font=("Courier New", 8, "bold"), relief=tk.FLAT,
          cursor="hand2", padx=6).pack(side=tk.LEFT)
lbl_serial_status = tk.Label(frm_srow, text="Belum terhubung", bg=PANEL,
                              fg=RED, font=("Courier New", 7))
lbl_serial_status.pack(side=tk.LEFT, padx=6)

# -- Panel: MQTT --
pnl_mqtt = panel_section(frm_right, "MQTT BROKER")
tk.Label(pnl_mqtt, text="Broker", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
broker_var = tk.StringVar(value=MQTT_BROKER)
tk.Entry(pnl_mqtt, textvariable=broker_var, bg="#f1f5f9", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)
tk.Label(pnl_mqtt, text="Port", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
mqttport_var = tk.StringVar(value=str(MQTT_PORT))
tk.Entry(pnl_mqtt, textvariable=mqttport_var, bg="#f1f5f9", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)

def connect_mqtt_gui():
    global MQTT_BROKER, MQTT_PORT
    MQTT_BROKER = broker_var.get()
    MQTT_PORT   = int(mqttport_var.get())
    connect_mqtt()
    log(f"Menghubungkan MQTT ke {MQTT_BROKER}:{MQTT_PORT}…")

frm_mrow = tk.Frame(pnl_mqtt, bg=PANEL)
frm_mrow.pack(fill=tk.X, padx=10, pady=4)
tk.Button(frm_mrow, text="Hubungkan", command=connect_mqtt_gui, bg=YELLOW,
          fg="#1a1a2e", font=("Courier New", 8, "bold"), relief=tk.FLAT,
          cursor="hand2", padx=6).pack(side=tk.LEFT)
lbl_mqtt_status = tk.Label(frm_mrow, text="Belum terhubung", bg=PANEL,
                            fg=RED, font=("Courier New", 7))
lbl_mqtt_status.pack(side=tk.LEFT, padx=6)
tk.Label(pnl_mqtt, text=f"Topic: {MQTT_TOPIC_DATA}", bg=PANEL, fg=SUBTEXT,
         font=("Courier New", 7)).pack(anchor=tk.W, padx=10, pady=(0, 6))

# -- Panel: Live Data --
pnl_live = panel_section(frm_right, "LIVE DATA")
lbl_last_b = tk.Label(pnl_live, text="B = — mT", bg=PANEL, fg=ACCENT,
                       font=("Courier New", 14, "bold"))
lbl_last_b.pack(pady=(4, 0))
lbl_last_v = tk.Label(pnl_live, text="V = — V", bg=PANEL, fg=TEXT,
                       font=("Courier New", 10))
lbl_last_v.pack()
lbl_count = tk.Label(pnl_live, text="0 sampel", bg=PANEL, fg=SUBTEXT,
                      font=("Courier New", 8))
lbl_count.pack(pady=(2, 8))

# -- Panel: Kontrol --
pnl_ctrl = panel_section(frm_right, "KONTROL")

def mkbtn(parent, text, cmd, bg, fg=TEXT):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                     font=("Courier New", 8, "bold"), relief=tk.FLAT,
                     cursor="hand2", padx=2, pady=7)

# Baris 1: START | STOP
frm_b1 = tk.Frame(pnl_ctrl, bg=PANEL)
frm_b1.pack(fill=tk.X, padx=8, pady=(2, 2))
mkbtn(frm_b1, "▶ START", mulai,    GREEN,  "#ffffff").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
mkbtn(frm_b1, "⏸ STOP",  berhenti, YELLOW, "#1a1a2e").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

# Baris 2: RESET | EXCEL | IMAGE
frm_b2 = tk.Frame(pnl_ctrl, bg=PANEL)
frm_b2.pack(fill=tk.X, padx=8, pady=(2, 2))
mkbtn(frm_b2, "🔄 RESET", reset_data,    "#e2e8f0").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
mkbtn(frm_b2, "💾 EXCEL", simpan_excel,  "#e2e8f0").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
mkbtn(frm_b2, "🖼 IMAGE", simpan_gambar, "#e2e8f0").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

# Baris 3: KELUAR (full width)
frm_b3 = tk.Frame(pnl_ctrl, bg=PANEL)
frm_b3.pack(fill=tk.X, padx=8, pady=(2, 8))
mkbtn(frm_b3, "❌  KELUAR", keluar, RED, "#ffffff").pack(fill=tk.X)

# -- Panel: Log Output --
pnl_log = panel_section(frm_right, "LOG OUTPUT")
txt_log = tk.Text(pnl_log, height=8, bg="#f1f5f9", fg=ACCENT,
                  font=("Courier New", 7), state=tk.DISABLED,
                  insertbackground=ACCENT, relief=tk.FLAT, bd=4, wrap=tk.WORD)
txt_log.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

# ---- ANIMASI ----
ani = animation.FuncAnimation(fig, update, interval=100, cache_frame_data=False)

root.protocol("WM_DELETE_WINDOW", keluar)
log("GMR UIN R1A Publisher siap. Hubungkan Serial & MQTT terlebih dahulu.")
root.mainloop()

# signed by: Gilang Pratama Putra Siswanto (extended MQTT build — 2026-05-08)
