import tkinter as tk
from tkinter import simpledialog, messagebox
import csv
import time
import os

try:
    from mfrc522 import SimpleMFRC522
    reader = SimpleMFRC522()
except ImportError:
    reader = None  # PC-kehitysympäristö

ADMIN_PASSWORD = "1234"

room_names = [
    "Rasti1", "Rasti2", "Rasti3",
    "Rasti4", "Rasti5", "Rasti6",
    "Rasti7", "Rasti8", "Rasti9",
]

TOTAL_SLOTS   = [10,  8, 12,  9, 15,  6,  7,  5, 11]
occupied_slots = [3,  5,  4,  1, 10,  3,  2,  5,  9]

log_file = "leimaukset.csv"

active_tags = {}

root = tk.Tk()
root.title("Mare valvomo 3000")
root.state("zoomed")

frame = tk.Frame(root)
frame.pack(pady=20)

slot_labels = []
title_labels = []

def get_bg_color(idx):
    if occupied_slots[idx] >= TOTAL_SLOTS[idx]:
        return "#FF6347"  # punainen täynnä
    else:
        return "#90EE90"  # vihreä vapaa

def update_slot(idx, new_occupied=None):
    if new_occupied is not None:
        occupied_slots[idx] = max(0, new_occupied)
    free = TOTAL_SLOTS[idx] - occupied_slots[idx]
    slot_labels[idx].config(text=f"Vapaita: {free}", bg=get_bg_color(idx))

def update_name(idx, new_name):
    room_names[idx] = new_name
    title_labels[idx].config(text=new_name)

for i in range(9):
    r, c = divmod(i, 3)
    title = tk.Label(frame, text=room_names[i], font=("Helvetica", 14, "bold"))
    title.grid(row=r*2, column=c, padx=20, pady=5)
    title_labels.append(title)
    free = TOTAL_SLOTS[i] - occupied_slots[i]
    slot = tk.Label(frame, text=f"Vapaita: {free}", font=("Helvetica", 13),
                    bg=get_bg_color(i), width=15, height=2, relief="ridge")
    slot.grid(row=r*2+1, column=c, padx=20, pady=5)
    slot_labels.append(slot)

def log_event(tag_uid, rasti_idx, action):
    first = not os.path.exists(log_file)
    with open(log_file, "a", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if first:
            w.writerow(["timestamp", "rasti", "tag_uid", "action"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), room_names[rasti_idx], tag_uid, action])

def choose_rasti_window(tag_uid, current_idx):
    win = tk.Toplevel(root)
    win.title("Valitse rasti")

    if current_idx is None:
        msg = f"Tagi {tag_uid} luettu. Valitse rasti:"
    else:
        msg = (f"Tagi {tag_uid} on nyt rastilla {room_names[current_idx]}\n"
               "Valitse uusi rasti:")
    tk.Label(win, text=msg, font=("Helvetica", 13)).pack(pady=10)

    grid = tk.Frame(win)
    grid.pack(pady=5)

    def assign(idx):
        nonlocal win
        if current_idx is not None and idx != current_idx:
            if occupied_slots[current_idx] > 0:
                occupied_slots[current_idx] -= 1
            update_slot(current_idx)
            log_event(tag_uid, current_idx, "EXIT")
            active_tags.pop(tag_uid, None)
        if occupied_slots[idx] < TOTAL_SLOTS[idx]:
            occupied_slots[idx] += 1
            active_tags[tag_uid] = idx
            update_slot(idx)
            log_event(tag_uid, idx, "ENTRY")
            win.destroy()
        else:
            messagebox.showwarning("Täynnä", f"{room_names[idx]} on täynnä!")

    for i, name in enumerate(room_names):
        r, c = divmod(i, 3)
        b = tk.Button(grid, text=name, width=15, height=2,
                      command=lambda i=i: assign(i))
        b.grid(row=r, column=c, padx=5, pady=5)

# --- Näytön sammutus/herätys logiikka

SCREEN_TIMEOUT_MS = 30_000  # 30 sekuntia
screen_off_job = None

def screen_off():
    # Piilottaa ikkunan (näyttö voi sammua tai olla musta)
    root.withdraw()
    # Jos haluat oikeasti sammuttaa fyysisen näytön, voit käyttää komentoa:
    # os.system("vcgencmd display_power 0")
    print("Näyttö sammutettu")

def screen_on():
    root.deiconify()
    # os.system("vcgencmd display_power 1")
    print("Näyttö herätetty")

def reset_screen_timer():
    global screen_off_job
    if screen_off_job is not None:
        root.after_cancel(screen_off_job)
    screen_on()
    screen_off_job = root.after(SCREEN_TIMEOUT_MS, screen_off)

def scan_tag():
    if reader is None:
        messagebox.showerror("RFID virhe", "RFID lukijaa ei löydy. Käynnistä Raspberry Pi:llä.")
        return

    try:
        messagebox.showinfo("Skannaus", "Vie NFC tagi lukijalle")
        tag_uid, _ = reader.read()
    except Exception as err:
        messagebox.showerror("Lukuvirhe", str(err))
        return

    reset_screen_timer()  # Herätetään näyttö ja käynnistetään 30s laskuri

    if tag_uid in active_tags:
        idx = active_tags[tag_uid]
        resposta = messagebox.askyesno(
            "Tagi luettu",
            f"Tagi on jo rastilla {room_names[idx]}.\nHaluatko valita uuden rastin?",
        )
        if resposta:
            choose_rasti_window(tag_uid, idx)
        else:
            messagebox.showinfo("Jatketaan", f"Tagi jatkaa rastilla {room_names[idx]}")
            log_event(tag_uid, idx, "CONTINUE")
    else:
        choose_rasti_window(tag_uid, None)

def open_admin_with_password():
    pw = simpledialog.askstring("Admin salasana", "Syötä salasana:", show="*")
    if pw == ADMIN_PASSWORD:
        open_admin_window()
    else:
        messagebox.showerror("Virheellinen salasana", "Pääsy evätty.")

def open_admin_window():
    adm = tk.Toplevel(root)
    adm.title("ADMIN")
    adm.geometry("600x600")

    tk.Label(adm, text="Muokkaa tilatietoja", font=("Helvetica", 16, "bold")).pack(pady=10)

    frm = tk.Frame(adm)
    frm.pack()

    vars_ = []
    for i in range(9):
        tk.Label(frm, text=f"Tila {i+1}").grid(row=i, column=0, sticky="e", padx=5, pady=5)
        nv = tk.StringVar(value=room_names[i])
        tv = tk.IntVar(value=TOTAL_SLOTS[i])
        ov = tk.IntVar(value=occupied_slots[i])
        tk.Entry(frm, textvariable=nv, width=15).grid(row=i, column=1)
        tk.Entry(frm, textvariable=tv, width=5).grid(row=i, column=2)
        tk.Entry(frm, textvariable=ov, width=5).grid(row=i, column=3)
        vars_.append((nv, tv, ov))

    def save():
        for i, (nv, tv, ov) in enumerate(vars_):
            update_name(i, nv.get())
            TOTAL_SLOTS[i] = tv.get()
            occupied_slots[i] = ov.get()
            update_slot(i)
        adm.destroy()

    tk.Button(adm, text="Tallenna", command=save, font=("Helvetica", 12),
              bg="#4CAF50", fg="white").pack(pady=20)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=15)

scan_btn = tk.Button(btn_frame, text="Skannaa NFC", font=("Helvetica", 13, "bold"),
                     bg="#FF9800", fg="white", command=scan_tag)
scan_btn.pack(side="left", padx=15)

admin_btn = tk.Button(btn_frame, text="Admin asetukset", font=("Helvetica", 12),
                      bg="#2196F3", fg="white", command=open_admin_with_password)
admin_btn.pack(side="left", padx=15)

reset_screen_timer()  # Käynnistä näytön aikakatkaisu heti

root.mainloop()
