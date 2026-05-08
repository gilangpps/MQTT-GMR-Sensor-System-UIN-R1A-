# GMR UIN R1A - MQTT Publisher
# Data Acquisition + MQTT Publisher
# Update patch: 2026-05-08

import serial
import json
import time
import threading
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
SERIAL_PORT  = 'COM7'
BAUD_RATE    = 9600

MQTT_BROKER  = '100.116.20.77'      # ganti jika broker di host lain
MQTT_PORT    = 1883
MQTT_TOPIC_DATA  = 'gmr/data'
MQTT_TOPIC_STATUS = 'gmr/status'
MQTT_CLIENT_ID   = 'GMR-Publisher'

# ============================================================
# KALIBRASI
# ============================================================
def tegangan_ke_b(v):
    return 5.3381 * v - 4.2983

# ============================================================
# STATE GLOBAL
# ============================================================
data_waktu  = []
data_b      = []
collecting  = False
start_time  = None
ser         = None
mqtt_client = None
mqtt_connected = False

# ============================================================
# MQTT
# ============================================================
def on_mqtt_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        update_mqtt_status("Terhubung", "#00e676")
        client.publish(MQTT_TOPIC_STATUS, json.dumps({"status": "publisher_online"}), retain=True)
    else:
        mqtt_connected = False
        update_mqtt_status(f"Gagal (rc={rc})", "#ff5252")

def on_mqtt_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    update_mqtt_status("Terputus", "#ff5252")

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
        update_mqtt_status(f"Error: {e}", "#ff5252")

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
        update_serial_status("Terhubung", "#00e676")
        log(f"Serial terhubung: {port} @ {baud} baud")
    except Exception as e:
        ser = None
        update_serial_status("Gagal", "#ff5252")
        log(f"Error serial: {e}")

# ============================================================
# GUI HELPERS
# ============================================================
def update_mqtt_status(text, color):
    try:
        lbl_mqtt_status.config(text=text, fg=color)
    except:
        pass

def update_serial_status(text, color):
    try:
        lbl_serial_status.config(text=text, fg=color)
    except:
        pass

def log(msg):
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        txt_log.config(state=tk.NORMAL)
        txt_log.insert(tk.END, f"[{ts}] {msg}\n")
        txt_log.see(tk.END)
        txt_log.config(state=tk.DISABLED)
    except:
        pass

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
        except:
            pass
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

                # Publish via MQTT
                publish_data(waktu, tegangan, b_mT)

                # Log
                log(f"t={waktu:.2f}s | V={tegangan:.4f}V | B={b_mT:.4f}mT  → MQTT ✓")

                # Update stats
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
# GUI UTAMA
# ============================================================
BG      = "#0d1117"
PANEL   = "#161b22"
ACCENT  = "#00b4d8"
GREEN   = "#00e676"
RED     = "#ff5252"
YELLOW  = "#ffd166"
TEXT    = "#e6edf3"
SUBTEXT = "#8b949e"

root = tk.Tk()
root.title("GMR UIN R1A — MQTT Publisher")
root.configure(bg=BG)
root.geometry("1100x750")
root.resizable(True, True)

# ---- HEADER ----
frm_header = tk.Frame(root, bg=ACCENT, pady=8)
frm_header.pack(fill=tk.X)
tk.Label(frm_header, text="GMR UIN R1A", font=("Courier New", 18, "bold"),
         bg=ACCENT, fg="#0d1117").pack(side=tk.LEFT, padx=16)
tk.Label(frm_header, text="MQTT PUBLISHER", font=("Courier New", 10),
         bg=ACCENT, fg="#0d1117").pack(side=tk.LEFT)

# ---- MAIN AREA ----
frm_main = tk.Frame(root, bg=BG)
frm_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

# -- Kolom kiri: plot + log --
frm_left = tk.Frame(frm_main, bg=BG)
frm_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Plot
fig, ax = plt.subplots(facecolor="#161b22")
ax.set_facecolor("#0d1117")
ax.set_title("Medan Magnet vs Waktu", color=TEXT, fontsize=10, pad=8)
ax.set_xlabel("Waktu, t (s)", color=SUBTEXT, fontsize=9)
ax.set_ylabel("Medan Magnet, B (mT)", color=SUBTEXT, fontsize=9)
ax.tick_params(colors=SUBTEXT)
for sp in ax.spines.values():
    sp.set_color("#30363d")
ax.grid(True, color="#21262d", linewidth=0.7)
line, = ax.plot([], [], lw=2, color=ACCENT)

canvas = FigureCanvasTkAgg(fig, master=frm_left)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(0,6))

# Log
frm_log = tk.Frame(frm_left, bg=PANEL, bd=0)
frm_log.pack(fill=tk.X, pady=(0,4))
tk.Label(frm_log, text=" LOG OUTPUT", font=("Courier New", 8, "bold"),
         bg=PANEL, fg=SUBTEXT).pack(anchor=tk.W, padx=6, pady=(4,0))
txt_log = tk.Text(frm_log, height=6, bg="#0d1117", fg=GREEN,
                  font=("Courier New", 8), state=tk.DISABLED,
                  insertbackground=GREEN, relief=tk.FLAT, bd=4)
txt_log.pack(fill=tk.X, padx=4, pady=(0,4))

# -- Kolom kanan: panel kontrol --
frm_right = tk.Frame(frm_main, bg=BG, width=240)
frm_right.pack(side=tk.RIGHT, fill=tk.Y, padx=(8,0))
frm_right.pack_propagate(False)

def panel_section(parent, title):
    f = tk.Frame(parent, bg=PANEL, bd=0, relief=tk.FLAT)
    f.pack(fill=tk.X, pady=(0,8))
    tk.Label(f, text=f" {title}", font=("Courier New", 8, "bold"),
             bg=PANEL, fg=SUBTEXT).pack(anchor=tk.W, padx=6, pady=(6,2))
    tk.Frame(f, bg="#30363d", height=1).pack(fill=tk.X, padx=6, pady=(0,6))
    return f

# -- Panel: Serial --
pnl_serial = panel_section(frm_right, "SERIAL PORT")
tk.Label(pnl_serial, text="Port", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
port_var = tk.StringVar(value=SERIAL_PORT)
tk.Entry(pnl_serial, textvariable=port_var, bg="#0d1117", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)
tk.Label(pnl_serial, text="Baud Rate", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
baud_var = tk.StringVar(value=str(BAUD_RATE))
ttk.Combobox(pnl_serial, textvariable=baud_var, values=["9600","19200","38400","57600","115200"],
             font=("Courier New", 8), width=16).pack(fill=tk.X, padx=10, pady=2)
frm_srow = tk.Frame(pnl_serial, bg=PANEL)
frm_srow.pack(fill=tk.X, padx=10, pady=4)
tk.Button(frm_srow, text="Hubungkan", command=connect_serial, bg=ACCENT,
          fg="#0d1117", font=("Courier New", 8, "bold"), relief=tk.FLAT,
          cursor="hand2", padx=6).pack(side=tk.LEFT)
lbl_serial_status = tk.Label(frm_srow, text="Belum terhubung", bg=PANEL,
                              fg=RED, font=("Courier New", 7))
lbl_serial_status.pack(side=tk.LEFT, padx=6)

# -- Panel: MQTT --
pnl_mqtt = panel_section(frm_right, "MQTT BROKER")
tk.Label(pnl_mqtt, text="Broker", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
broker_var = tk.StringVar(value=MQTT_BROKER)
tk.Entry(pnl_mqtt, textvariable=broker_var, bg="#0d1117", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)
tk.Label(pnl_mqtt, text="Port", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
mqttport_var = tk.StringVar(value=str(MQTT_PORT))
tk.Entry(pnl_mqtt, textvariable=mqttport_var, bg="#0d1117", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)

def connect_mqtt_gui():
    global mqtt_client, MQTT_BROKER, MQTT_PORT
    MQTT_BROKER = broker_var.get()
    MQTT_PORT   = int(mqttport_var.get())
    connect_mqtt()
    log(f"Menghubungkan MQTT ke {MQTT_BROKER}:{MQTT_PORT}…")

frm_mrow = tk.Frame(pnl_mqtt, bg=PANEL)
frm_mrow.pack(fill=tk.X, padx=10, pady=4)
tk.Button(frm_mrow, text="Hubungkan", command=connect_mqtt_gui, bg=YELLOW,
          fg="#0d1117", font=("Courier New", 8, "bold"), relief=tk.FLAT,
          cursor="hand2", padx=6).pack(side=tk.LEFT)
lbl_mqtt_status = tk.Label(frm_mrow, text="Belum terhubung", bg=PANEL,
                             fg=RED, font=("Courier New", 7))
lbl_mqtt_status.pack(side=tk.LEFT, padx=6)
tk.Label(pnl_mqtt, text=f"Topic: {MQTT_TOPIC_DATA}", bg=PANEL, fg=SUBTEXT,
         font=("Courier New", 7)).pack(anchor=tk.W, padx=10, pady=(0,6))

# -- Panel: Live Data --
pnl_live = panel_section(frm_right, "LIVE DATA")
lbl_last_b = tk.Label(pnl_live, text="B = — mT", bg=PANEL, fg=ACCENT,
                       font=("Courier New", 14, "bold"))
lbl_last_b.pack(pady=(4,0))
lbl_last_v = tk.Label(pnl_live, text="V = — V", bg=PANEL, fg=TEXT,
                       font=("Courier New", 10))
lbl_last_v.pack()
lbl_count  = tk.Label(pnl_live, text="0 sampel", bg=PANEL, fg=SUBTEXT,
                       font=("Courier New", 8))
lbl_count.pack(pady=(2,8))

# -- Panel: Kontrol --
pnl_ctrl = panel_section(frm_right, "KONTROL")

def btn(parent, text, cmd, bg, fg="#0d1117"):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                     font=("Courier New", 9, "bold"), relief=tk.FLAT,
                     cursor="hand2", padx=4, pady=6)

btn(pnl_ctrl, "▶  START",      mulai,        GREEN).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "⏸  STOP",       berhenti,     YELLOW).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "🔄  RESET",      reset_data,   "#30363d", TEXT).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "💾  SAVE EXCEL", simpan_excel, "#30363d", TEXT).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "🖼  SAVE IMAGE", simpan_gambar,"#30363d", TEXT).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "❌  KELUAR",     keluar,       RED).pack(fill=tk.X, padx=10, pady=(8,10))

# ---- ANIMASI ----
ani = animation.FuncAnimation(fig, update, interval=100, cache_frame_data=False)

# ---- START ----
root.protocol("WM_DELETE_WINDOW", keluar)
log("GMR UIN R1A Publisher siap. Hubungkan Serial & MQTT terlebih dahulu.")
root.mainloop()

# signed by: Gilang Pratama Putra Siswanto (extended MQTT build — 2026-05-08)
