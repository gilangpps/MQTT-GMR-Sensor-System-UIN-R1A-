# GMR UIN R1A - MQTT Subscriber
# Data Viewer / Real-time Monitor
# Update patch: 2026-05-08

import json
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
# KONFIGURASI DEFAULT
# ============================================================
MQTT_BROKER      = 'localhost'
MQTT_PORT        = 1883
MQTT_TOPIC_DATA  = 'gmr/data'
MQTT_TOPIC_STATUS = 'gmr/status'
MQTT_CLIENT_ID   = 'GMR-Subscriber'

# ============================================================
# STATE GLOBAL
# ============================================================
data_waktu    = []
data_b        = []
data_v        = []
mqtt_client   = None
mqtt_connected = False
publisher_status = "unknown"
data_lock     = threading.Lock()

# ============================================================
# MQTT CALLBACKS
# ============================================================
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        client.subscribe(MQTT_TOPIC_DATA,   qos=1)
        client.subscribe(MQTT_TOPIC_STATUS, qos=0)
        update_mqtt_status("Terhubung", "#00e676")
        log(f"Terhubung ke broker. Subscribe: {MQTT_TOPIC_DATA}")
    else:
        mqtt_connected = False
        update_mqtt_status(f"Gagal (rc={rc})", "#ff5252")
        log(f"Koneksi MQTT gagal, rc={rc}")

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    update_mqtt_status("Terputus", "#ff5252")
    log("Koneksi MQTT terputus.")

def on_message(client, userdata, msg):
    global publisher_status
    try:
        payload = json.loads(msg.payload.decode('utf-8'))

        if msg.topic == MQTT_TOPIC_STATUS:
            publisher_status = payload.get("status", "unknown")
            update_publisher_status(publisher_status)
            log(f"Status publisher: {publisher_status}")

        elif msg.topic == MQTT_TOPIC_DATA:
            t   = payload.get("t_s",  0.0)
            v   = payload.get("v_V",  0.0)
            b   = payload.get("b_mT", 0.0)
            ts  = payload.get("timestamp", "")

            with data_lock:
                data_waktu.append(t)
                data_b.append(b)
                data_v.append(v)

            log(f"⬇ t={t:.2f}s | V={v:.4f}V | B={b:.4f}mT")
    except Exception as e:
        log(f"Error parse pesan: {e}")

# ============================================================
# MQTT CONNECT
# ============================================================
def connect_mqtt():
    global mqtt_client
    broker = broker_var.get()
    port   = int(port_var.get())
    try:
        if mqtt_client:
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            except:
                pass

        mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)
        mqtt_client.on_connect    = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_message    = on_message
        mqtt_client.connect_async(broker, port, keepalive=60)
        mqtt_client.loop_start()
        log(f"Menghubungkan ke {broker}:{port}…")
    except Exception as e:
        update_mqtt_status(f"Error", "#ff5252")
        log(f"Error koneksi: {e}")

def disconnect_mqtt():
    global mqtt_client, mqtt_connected
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    mqtt_connected = False
    update_mqtt_status("Terputus", "#ff5252")
    log("Koneksi MQTT diputus manual.")

# ============================================================
# GUI HELPERS
# ============================================================
def update_mqtt_status(text, color):
    try:
        lbl_mqtt_status.config(text=text, fg=color)
    except:
        pass

def update_publisher_status(status_str):
    mapping = {
        "publisher_online":  ("Online",     "#00e676"),
        "collecting":        ("Collecting…","#ffd166"),
        "stopped":           ("Stopped",    "#ff9800"),
        "publisher_offline": ("Offline",    "#ff5252"),
    }
    txt, col = mapping.get(status_str, (status_str, "#8b949e"))
    try:
        lbl_pub_status.config(text=txt, fg=col)
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
# KONTROL DATA
# ============================================================
def reset_data():
    with data_lock:
        data_waktu.clear()
        data_b.clear()
        data_v.clear()
    line.set_data([], [])
    ax.relim()
    ax.autoscale_view()
    canvas.draw()
    lbl_count.config(text="0 sampel")
    lbl_last_b.config(text="B = — mT")
    lbl_last_v.config(text="V = — V")
    log("🔄 Data direset")

def simpan_excel():
    with data_lock:
        if not data_waktu:
            messagebox.showwarning("Peringatan", "Belum ada data untuk disimpan.")
            return
        df = pd.DataFrame({'t (s)': list(data_waktu),
                           'V (V)': list(data_v),
                           'B (mT)': list(data_b)})
    fp = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Files", "*.xlsx")],
        title="Simpan Data"
    )
    if fp:
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
        try:
            if mqtt_client:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
        except:
            pass
        root.destroy()

# ============================================================
# ANIMASI PLOT
# ============================================================
def update_plot(frame):
    with data_lock:
        if not data_waktu:
            return line,
        x = list(data_waktu)
        y = list(data_b)
        v = data_v[-1] if data_v else 0.0

    line.set_data(x, y)
    ax.relim()
    ax.autoscale_view()
    canvas.draw()

    n = len(x)
    lbl_count.config(text=f"{n} sampel")
    lbl_last_b.config(text=f"B = {y[-1]:.4f} mT")
    lbl_last_v.config(text=f"V = {v:.4f} V")

    # Statistik
    if n > 1:
        lbl_bmax.config(text=f"Max: {max(y):.4f} mT")
        lbl_bmin.config(text=f"Min: {min(y):.4f} mT")
        lbl_bavg.config(text=f"Avg: {sum(y)/n:.4f} mT")

    return line,

# ============================================================
# GUI UTAMA
# ============================================================
BG      = "#0d1117"
PANEL   = "#161b22"
ACCENT  = "#f77f00"      # oranye — beda dari publisher
GREEN   = "#00e676"
RED     = "#ff5252"
YELLOW  = "#ffd166"
CYAN    = "#00b4d8"
TEXT    = "#e6edf3"
SUBTEXT = "#8b949e"

root = tk.Tk()
root.title("GMR UIN R1A — MQTT Subscriber")
root.configure(bg=BG)
root.geometry("1100x750")
root.resizable(True, True)

# ---- HEADER ----
frm_header = tk.Frame(root, bg=ACCENT, pady=8)
frm_header.pack(fill=tk.X)
tk.Label(frm_header, text="GMR UIN R1A", font=("Courier New", 18, "bold"),
         bg=ACCENT, fg="#0d1117").pack(side=tk.LEFT, padx=16)
tk.Label(frm_header, text="MQTT SUBSCRIBER", font=("Courier New", 10),
         bg=ACCENT, fg="#0d1117").pack(side=tk.LEFT)
# Badge subscriber
tk.Label(frm_header, text="⬇ RECEIVE MODE", font=("Courier New", 8, "bold"),
         bg="#0d1117", fg=ACCENT, padx=8, pady=2).pack(side=tk.RIGHT, padx=12)

# ---- MAIN AREA ----
frm_main = tk.Frame(root, bg=BG)
frm_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

# -- Kolom kiri: plot + log --
frm_left = tk.Frame(frm_main, bg=BG)
frm_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Plot
fig, ax = plt.subplots(facecolor="#161b22")
ax.set_facecolor("#0d1117")
ax.set_title("Medan Magnet vs Waktu  [Subscriber]", color=TEXT, fontsize=10, pad=8)
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
txt_log = tk.Text(frm_log, height=6, bg="#0d1117", fg=ACCENT,
                  font=("Courier New", 8), state=tk.DISABLED,
                  insertbackground=ACCENT, relief=tk.FLAT, bd=4)
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

# -- Panel: MQTT --
pnl_mqtt = panel_section(frm_right, "MQTT BROKER")
tk.Label(pnl_mqtt, text="Broker", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
broker_var = tk.StringVar(value=MQTT_BROKER)
tk.Entry(pnl_mqtt, textvariable=broker_var, bg="#0d1117", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)
tk.Label(pnl_mqtt, text="Port", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
port_var = tk.StringVar(value=str(MQTT_PORT))
tk.Entry(pnl_mqtt, textvariable=port_var, bg="#0d1117", fg=ACCENT,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=ACCENT).pack(fill=tk.X, padx=10, pady=2)
tk.Label(pnl_mqtt, text="Subscribe Topic", bg=PANEL, fg=TEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
topic_var = tk.StringVar(value=MQTT_TOPIC_DATA)
tk.Entry(pnl_mqtt, textvariable=topic_var, bg="#0d1117", fg=CYAN,
         font=("Courier New", 9), relief=tk.FLAT, bd=4,
         insertbackground=CYAN).pack(fill=tk.X, padx=10, pady=2)

frm_mrow = tk.Frame(pnl_mqtt, bg=PANEL)
frm_mrow.pack(fill=tk.X, padx=10, pady=4)
tk.Button(frm_mrow, text="Subscribe", command=connect_mqtt, bg=ACCENT,
          fg="#0d1117", font=("Courier New", 8, "bold"), relief=tk.FLAT,
          cursor="hand2", padx=6).pack(side=tk.LEFT)
tk.Button(frm_mrow, text="Putus", command=disconnect_mqtt, bg="#30363d",
          fg=TEXT, font=("Courier New", 8), relief=tk.FLAT,
          cursor="hand2", padx=6).pack(side=tk.LEFT, padx=(4,0))
lbl_mqtt_status = tk.Label(pnl_mqtt, text="Belum terhubung", bg=PANEL,
                             fg=RED, font=("Courier New", 7))
lbl_mqtt_status.pack(anchor=tk.W, padx=10, pady=(0,4))

# -- Panel: Publisher Status --
pnl_pub = panel_section(frm_right, "STATUS PUBLISHER")
tk.Label(pnl_pub, text="Publisher:", bg=PANEL, fg=SUBTEXT, font=("Courier New", 8)).pack(anchor=tk.W, padx=10)
lbl_pub_status = tk.Label(pnl_pub, text="Unknown", bg=PANEL, fg=SUBTEXT,
                            font=("Courier New", 11, "bold"))
lbl_pub_status.pack(anchor=tk.W, padx=10, pady=(0,6))

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
lbl_count.pack(pady=(2,4))

# -- Panel: Statistik --
pnl_stat = panel_section(frm_right, "STATISTIK B (mT)")
lbl_bmax = tk.Label(pnl_stat, text="Max: —", bg=PANEL, fg=GREEN, font=("Courier New", 8))
lbl_bmax.pack(anchor=tk.W, padx=10)
lbl_bmin = tk.Label(pnl_stat, text="Min: —", bg=PANEL, fg=RED, font=("Courier New", 8))
lbl_bmin.pack(anchor=tk.W, padx=10)
lbl_bavg = tk.Label(pnl_stat, text="Avg: —", bg=PANEL, fg=CYAN, font=("Courier New", 8))
lbl_bavg.pack(anchor=tk.W, padx=10, pady=(0,6))

# -- Panel: Kontrol --
pnl_ctrl = panel_section(frm_right, "KONTROL")

def btn(parent, text, cmd, bg, fg="#0d1117"):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                     font=("Courier New", 9, "bold"), relief=tk.FLAT,
                     cursor="hand2", padx=4, pady=6)

btn(pnl_ctrl, "🔄  RESET DATA",  reset_data,   "#30363d", TEXT).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "💾  SAVE EXCEL",  simpan_excel, "#30363d", TEXT).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "🖼  SAVE IMAGE",  simpan_gambar,"#30363d", TEXT).pack(fill=tk.X, padx=10, pady=3)
btn(pnl_ctrl, "❌  KELUAR",      keluar,       RED).pack(fill=tk.X, padx=10, pady=(8,10))

# ---- ANIMASI ----
ani = animation.FuncAnimation(fig, update_plot, interval=200, cache_frame_data=False)

# ---- START ----
root.protocol("WM_DELETE_WINDOW", keluar)
log("GMR UIN R1A Subscriber siap. Klik 'Subscribe' untuk mulai menerima data.")
root.mainloop()

# signed by: Gilang Pratama Putra Siswanto (MQTT Subscriber — 2026-05-08)
