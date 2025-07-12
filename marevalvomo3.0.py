




try:
    from mfrc522 import SimpleMFRC522
    reader = SimpleMFRC522()
except ImportError:
    reader = None  # Kehitysympäristö ilman NFC-lukijaa

import tkinter as tk
from tkinter import simpledialog, messagebox
import csv
import time
import os
from typing import Optional
import sqlite3


# ======================= Asetukset ja perusdata ==============================

ADMIN_PASSWORD = "1234"

DB_FILE = "mare.db"

# [8, 5, 5, 10, 6, 6, 5, 6]
TOTAL_SLOTS =   [10, 10, 10, 10, 10, 10, 10, 10]
occupied_slots = [0, 0,  0, 0, 0, 0, 0, 0]

conn = sqlite3.connect(DB_FILE)
c = conn.cursor()

# --- Tietokanta ja sen alustukset ---

def init_db():
    # Luo rastit-taulu jos ei ole
    c.execute('''
        CREATE TABLE IF NOT EXISTS rastit (
            id INTEGER PRIMARY KEY,
            nimi_fi TEXT,
            nimi_en TEXT,
            total_slots INTEGER DEFAULT 0,
            occupied_slots INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS loki (
            id INTEGER PRIMARY KEY,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            tag_idx INTEGER,
            rasti_id INTEGER,
            action TEXT,
            FOREIGN KEY (tag_idx) REFERENCES vartiot(tag_idx),
            FOREIGN KEY (rasti_id) REFERENCES rastit(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS vartiot (
            tag_idx INTEGER PRIMARY KEY,
            nimi TEXT,
            koko INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS active_tags (
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            tag_idx INTEGER,
            rasti_id INTEGER,
            FOREIGN KEY (tag_idx) REFERENCES vartiot(tag_idx),
            FOREIGN KEY (rasti_id) REFERENCES rastit(id)
        )
    ''')

    # Lisää rastit tietokantaan jos taulu on tyhjä
    c.execute("SELECT COUNT(*) FROM rastit")
    if c.fetchone()[0] == 0:
        print("override")
        for i in range(len(room_names)):
            c.execute("INSERT INTO rastit (id, nimi_fi, nimi_en, total_slots, occupied_slots) VALUES (?, ?, ?, ?, ?)",
                      (i, room_names[i], room_names_en[i], TOTAL_SLOTS[i], occupied_slots[i]))

    conn.commit()

def init_slots():
    global TOTAL_SLOTS, occupied_slots
    c.execute("SELECT total_slots, occupied_slots FROM rastit ORDER BY id")
    rows = c.fetchall()
    print(rows)
    TOTAL_SLOTS = [i[0] for i in rows]
    occupied_slots = [i[1] for i in rows]
    conn.commit()

def get_vartio_from_db(current_tag_idx: int):
    c.execute("SELECT * FROM vartiot WHERE tag_idx = (?)",
                (current_tag_idx,))
    return c.fetchone()

def set_vartio(tag_uid, vartio_nimi, vartio_koko):
    c.execute("INSERT INTO vartiot (tag_idx, nimi, koko) VALUES (?, ?, ?)",
    (tag_uid, vartio_nimi.get(), vartio_koko.get()))
    conn.commit()

def get_checkpoint_from_db(current_idx: int):
    c.execute("SELECT * FROM rastit WHERE id = (?)",
                (current_idx,))
    conn.commit()
    return c.fetchone()

def get_checkpoints_from_db():
    global TOTAL_SLOTS, occupied_slots
    c.execute("SELECT * FROM rastit ORDER BY id")
    rows = c.fetchall()
    for r in rows:
        idx, total, occupied = r
        if idx < len(TOTAL_SLOTS):
            TOTAL_SLOTS[idx] = total
            occupied_slots[idx] = occupied
    conn.commit()

def save_slots_to_db(current_idx: int):
    c.execute("UPDATE rastit SET occupied_slots = (?) WHERE id = (?)",
                (occupied_slots[current_idx], current_idx))
    conn.commit()

def save_log(uid, idx, action):
    c.execute("INSERT INTO loki (tag_idx, rasti_id, action) VALUES (?, ?, ?)",
                (uid, idx, action))
    conn.commit()

def get_active_tag(current_tag_idx: int):
    c.execute("SELECT * FROM active_tags WHERE tag_idx = (?)",
                (current_tag_idx,))
    conn.commit()
    return c.fetchone()

def get_active_tags():
    c.execute("SELECT * FROM active_tags")
    conn.commit()
    return c.fetchall()

def set_active_tag(current_tag_idx: int, current_rasti_id: int):
    c.execute("INSERT INTO active_tags (tag_idx, rasti_id) VALUES (?, ?)",
                (current_tag_idx, current_rasti_id))
    conn.commit()

def update_timestamp(tag_uid: int):
    c.execute("UPDATE active_tags SET timestamp = CURRENT_TIMESTAMP WHERE tag_idx = (?)",
                (tag_uid,))
    conn.commit()

def delete_active_tag(current_tag_idx: int):
    c.execute("DELETE FROM active_tags WHERE tag_idx = (?)",
                (current_tag_idx,))
    conn.commit()

room_names = [
    "1 PYSY PINNALLA", "2 ÄLÄ ANNA PALAA", "3 LIIKETTÄ PALLOON",
    "4 RISUARNOLDS", "5 Kuumat paikat", "6 Santa odysseia",
    "7 Sokkona vesillä", "8 Lauta ralli",
]

room_names_en = [
    "1 Stay afloat", "2 Don't let it burn", "3 Keep the ball moving",
    "4 Dunkin sticks", "5 Hot Spots", "6 Sand odyssei",
    "7 Lost at sea", "8 Plank ralley",
]

texts_fi = {
    "title": "Mare valvomo 3000",
    "admin": "Admin asetukset",
    "instructions": "Käyttöohjeet",
    "free_slots": "Vapaita: {}",
    "admin_view": "Admin näkymä",
    "log_review": "Tarkastele lokia",
    "timeout": "Aseta aikakatkaisu (s)",
    "nfc_sim": "Simuloi NFC",
    "active_tags": "Näytä aktiiviset tagit",
    "remove": "Poista",
}

texts_en = {
    "title": "Mare Control 3000",
    "admin": "Admin Settings",
    "instructions": "Instructions",
    "free_slots": "Free: {}",
    "admin_view": "Admin view",
    "log_review": "View log",
    "timeout": "Set timeout (s)",
    "nfc_sim": "Simulate NFC",
    "active_tags": "Show active tags",
    "remove": "Remove",
}

kieli = "FI"

log_file = "leimaukset.csv"
timeout_seconds = 7200

# ======================= Tk-pääikkuna ==============================

root = tk.Tk()
root.title(texts_fi["title"])
root.geometry("1280x720")
root.attributes("-fullscreen", True)

frame_container = tk.Frame(root)
frame_container.pack(fill="both", expand=True)

frame_container.grid_columnconfigure(0, weight=0)
frame_container.grid_columnconfigure(1, weight=1)

# Vasemman laidan kehys (käyttöohje)
left_frame = tk.Frame(frame_container, width=300)
left_frame.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)

ohje_label = tk.Label(left_frame, text=texts_fi["instructions"], font=("Helvetica", 12, "bold"))
ohje_label.pack(pady=(0,10))

ohje_text = tk.Text(left_frame, height=20, width=35,font=("Helvetica", 16), wrap="word")
ohje_text.pack()

suomi_ohje = """\




!!! OHJAA KURSORIA LIIKUTTAMALLA SORMEA NÄYTÖLLÄ JA VALITSE NAPAUTTAMALLA NÄYTTÖÄ !!!

1. Vie NFC-tagi lähelle lukijaa.
2. Valitse haluamasi rasti painamalla.
3. Jos tagi on jo rastilla, voit valita uuden, jatkaa samalla tai poistua rastilta.

CHANGE LANGUAGE BY DRAGGING YOUR FINGER ON SCREEN AND TAP WHEN CURSOR IS OVER ENGLISH
"""

englanti_ohje = """\



!!! MOVE CURSOR BY DRAGGING YOUR FINGER ON SCREEN AND TAP TO SELECT !!!

1. Move your playingcard near the reader.
2. Choose your checkpoint by placing cursor on wanted checkpoint.
3. If tag is already in checkpoint, you can choose new, continue or exit checkpoint.

VAIHDA KIELTÄ OHJAAMALLA KURSORI SUOMEKSI PAINIKKEEN PÄÄLLE JA NAPAUTA NÄYTTÖÄ
"""

ohje_text.insert("1.0", suomi_ohje)
ohje_text.config(state="disabled")

def switch_language():
    global kieli
    kieli = "EN" if kieli == "FI" else "FI"
    päivitä_kieli()

kieli_btn = tk.Button(left_frame, text="English",font=("Helvetica", 14, "bold"), width=10, height=2, command=switch_language)
kieli_btn.pack(pady=10)

admin_btn = tk.Button(left_frame, text=texts_fi["admin"], command=lambda: admin_panel())
admin_btn.pack(pady=120)

# Oikean laidan kehys (rasti-ruudukko)
grid_frame = tk.Frame(frame_container)
grid_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

slot_labels: list[tk.Label] = []
title_labels: list[tk.Label] = []

def get_bg_color(idx: int) -> str:
    if occupied_slots[idx] >= TOTAL_SLOTS[idx]:
        return "#FF6347"  # punainen täynnä
    else:
        return "#90EE90"  # vihreä vapaa

ROWS = 3
COLUMNS = 3
BOX_WIDTH = 17
BOX_HEIGHT = 7

for i in range(len(room_names)):
    r, ö = divmod(i, 3)
    r1 = r + 1

    title = tk.Label(grid_frame, text=room_names[i], font=("Helvetica", 11, "bold"))
    title.grid(row=r1*2, column=ö, padx=10, pady=(0,20))
    title_labels.append(title)

    slot_label = tk.Label(grid_frame, text=f"Vapaita: {TOTAL_SLOTS[i] - occupied_slots[i]}",
                          bg=get_bg_color(i), font=("Helvetica", 12), width=BOX_WIDTH, height=BOX_HEIGHT)
    slot_label.grid(row=r1*2+1, column=ö, padx=8, pady=(0,24))
    slot_labels.append(slot_label)

def päivitä_kieli():
    global current_names
    if kieli == "FI":
        t = texts_fi
        current_names = room_names
        ohje_text.config(state="normal")
        ohje_text.delete("1.0", tk.END)
        ohje_text.insert("1.0", suomi_ohje)
        kieli_btn.config(text="English")
    else:
        t = texts_en
        current_names = room_names_en
        ohje_text.config(state="normal")
        ohje_text.delete("1.0", tk.END)
        ohje_text.insert("1.0", englanti_ohje)
        kieli_btn.config(text="Suomeksi")

    ohje_text.config(state="disabled")

    root.title(t["title"])
    admin_btn.config(text=t["admin"])
    ohje_label.config(text=t["instructions"])

    for i in range(len(current_names)):
        title_labels[i].config(text=current_names[i])
        free = TOTAL_SLOTS[i] - occupied_slots[i]
        slot_labels[i].config(
            text=f"{'Vapaita' if kieli == 'FI' else 'Free'}: {free}",
            bg=get_bg_color(i)
        )

# ======================= Admin-paneeli ==============================

def admin_panel():
    if simpledialog.askstring("Admin", "Syötä salasana:") != ADMIN_PASSWORD:
        return

    win = tk.Toplevel(root)
    t = texts_fi if kieli == "FI" else texts_en
    win.title(t["admin_view"])

    def tarkastele_lokia():
        if not os.path.exists(log_file):
            messagebox.showinfo("Ei lokia", "Lokitiedostoa ei löytynyt.")
            return

        log_win = tk.Toplevel(win)
        log_win.title(t["log_review"])

        with open(log_file, newline="") as f:
            reader_csv = csv.reader(f, delimiter=";")
            for row in reader_csv:
                tk.Label(log_win, text="; ".join(row)).pack(anchor="w", padx=5)

    def muuta_vanhentumisaika():
        global timeout_seconds
        uusi = simpledialog.askinteger(t["timeout"], t["timeout"])
        if uusi:
            global timeout_seconds
            timeout_seconds = uusi

    def simuloi_nfc():
        tag_uid = simpledialog.askinteger("Simulointi", "Syötä tagin UID")
        if tag_uid is not None:
            idx_tuple = get_active_tag(tag_uid)
            print(idx_tuple)
            current_idx = idx_tuple[2] if idx_tuple else None
            vartio = get_vartio_from_db(tag_uid)
            print(vartio)
            if not vartio:
                createvartiovalues_window(tag_uid)
            else:
                choose_rasti_window(tag_uid, current_idx)
    def nayta_aktiiviset():
        show_active_tags()

    tk.Button(win, text=t["log_review"], width=30, command=tarkastele_lokia).pack(padx=10, pady=5)
    tk.Button(win, text=t["timeout"], width=30, command=muuta_vanhentumisaika).pack(padx=10, pady=5)
    tk.Button(win, text=t["nfc_sim"], width=30, command=simuloi_nfc).pack(padx=10, pady=5)
    tk.Button(win, text=t["active_tags"], width=30, command=nayta_aktiiviset).pack(padx=10, pady=5)

# ======================= Aikaleimojen tarkistus ==============================

def tarkista_vanhentuneet_tagit():
    nykyhetki = time.time()
    active_tags = get_active_tags()
    vanhentuneet = [tag for tag in active_tags if nykyhetki - tag[2] > timeout_seconds]
    for tag in vanhentuneet:
        delete_active_tag(tag[1])
        vartio = get_vartio_from_db(tag[1])
        if occupied_slots[tag[1]] > 0:
            occupied_slots[tag[1]] -= vartio[2]
        update_slot(tag[1])
        log_event(tag[1], tag[2], "TIMEOUT")

# ======================= Lokin kirjaus ==============================

def log_event(uid: int, idx: int, action: str):
    save_log(uid, idx, action)

# ======================= Päivitä rastin tila ==============================

    
def update_slot(idx: int):
    vapaita = TOTAL_SLOTS[idx] - occupied_slots[idx]
    save_slots_to_db(idx)
    slot_labels[idx].config(
        text=f"{'Vapaita' if kieli == 'FI' else 'Free'}: {vapaita}",
        bg=get_bg_color(idx)
    )

# ======================= Apufunktiot ==============================

def get_room_name(idx: Optional[int]) -> str:
    if idx is None or idx < 0 or idx >= len(room_names):
        return "-"
    checkpoint = get_checkpoint_from_db(idx)
    return checkpoint[1] if kieli == "FI" else checkpoint[2]

def show_active_tags():
    win = tk.Toplevel(root)
    win.title("Aktiiviset tagit" if kieli == "FI" else "Active tags")
    active_tags = get_active_tags()
    if not active_tags:
        tk.Label(win, text="Ei aktiivisia tageja" if kieli == "FI" else "No active tags").pack(padx=10, pady=10)
        return
    for (uid, idx, ts) in active_tags:
        aika = time.strftime("%H:%M:%S", time.localtime(ts))
        rasti = get_room_name(idx)
        tk.Label(win, text=f"Tag {uid} - Rasti: {rasti} - Aika: {aika}").pack(anchor="w", padx=10)

def center_window(win, width=300, height=200):
    # Hakee pääikkunan sijainnin ja koon
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_width = root.winfo_width()
    root_height = root.winfo_height()

    # Lasketaan keskikohta pääikkunassa
    x = root_x + (root_width // 2) - (width // 2)
    y = root_y + (root_height // 2) - (height // 2)

    win.geometry(f"{width}x{height}+{x}+{y}")

# Käyttö esimerkissämme (esim. choose_rasti_window-funktiossa):
def choose_rasti_window(tag_uid: int, current_idx: Optional[int]):
    win = tk.Toplevel(root)
    win.title("Valitse rasti" if kieli == "FI" else "Choose checkpoint")
    (tag, vartio_nimi, vartio_koko) = get_vartio_from_db(tag_uid)
    active_tag = get_active_tag(tag_uid)

    # Ei fullscreen, jotta keskitys toimii
    # win.attributes("-fullscreen", True)  # Poistettu keskityksen vuoksi
    center_window(win, 700, 400)

    tag_str = f"Tagi {tag_uid}" if kieli == "FI" else f"Tag {tag_uid}"
    if current_idx is not None:
        msg = (f"{tag_str} on nyt rastilla {get_room_name(current_idx)} \n" if kieli == "FI" else f"{tag_str} is now at {get_room_name(current_idx)} \n"+
               "Valitse uusi rasti, jatka samalla rastilla tai poistu rastilta:" if kieli == "FI" else "Choose new checkpoint, stay on current or check out from checkpoint")
    else:
        msg = f"{tag_str} luettu. Valitse rasti:" if kieli == "FI" else f"{tag_str} read. Choose checkpoint:"

    tk.Label(win, text=msg, font=("Helvetica", 13)).pack(pady=10)

    grid = tk.Frame(win)
    grid.pack(pady=5)

    status_label = tk.Label(win, text="", font=("Helvetica", 11), fg="red")
    status_label.pack(pady=10)

# Käyttö esimerkissämme (esim. choose_rasti_window-funktiossa):
    def assign(idx: int):

        # Jatka samalla rastilla
        if idx == current_idx:
            if active_tag:
                update_slot(idx)
                log_event(tag_uid, idx, "CONTINUE")
            win.destroy()
            return

        # Poistu edelliseltä rastilta
        if current_idx is not None:
            if occupied_slots[current_idx] > 0:
                occupied_slots[current_idx] -= vartio_koko
            update_slot(current_idx)
            log_event(tag_uid, current_idx, "EXIT")
            delete_active_tag(tag_uid)

        # Tarkista onko uusi rasti täynnä
        if occupied_slots[idx] < TOTAL_SLOTS[idx]:
            occupied_slots[idx] += vartio_koko
            set_active_tag(tag_uid, idx)
            update_slot(idx)
            log_event(tag_uid, idx, "ENTRY")
            win.destroy()
        else:   
            status_label.config(text=f"{get_room_name(idx)} on täynnä!" if kieli == "FI" else "is full!")


    def exit_slot():
        # Poistaa tagin rastilta
        if current_idx is not None and active_tag:
            if occupied_slots[current_idx] > 0:
                occupied_slots[current_idx] -= vartio_koko
            update_slot(current_idx)
            log_event(tag_uid, current_idx, "EXIT")
            delete_active_tag(tag_uid)
        win.destroy()

    # Luodaan rastipainikkeet
    for i, nimi in enumerate(room_names if kieli == "FI" else room_names_en):
        b = tk.Button(grid, text=nimi, width=15, command=lambda i=i: assign(i))
        b.grid(row=i // 3, column=i % 3, padx=5, pady=5)

    # Jatka rastia -painike (näkyy vain jos tag on jo rastilla)
    if current_idx is not None:
        cont_btn_text = "Jatka rastia" if kieli == "FI" else "Continue current"
        cont_btn = tk.Button(win, text=cont_btn_text, width=20, command=lambda: assign(current_idx))
        cont_btn.pack(pady=(10,5))

        # Poistu rastilta -painike
        exit_btn_text = "Poistu rastilta" if kieli == "FI" else "Exit slot"
        exit_btn = tk.Button(win, text=exit_btn_text, width=20, command=exit_slot)
        exit_btn.pack(pady=(0,10))

# ======================= Luo vartion arvot ==============================

def createvartiovalues_window(tag_uid: int):
    def handle_save():
        set_vartio(tag_uid, vartio_nimi, vartio_koko)
        win.destroy()
        choose_rasti_window(tag_uid, None)

    win = tk.Toplevel(root)
    win.title("Luo vartio" if kieli == "FI" else "Choose checkpoint")
    center_window(win, 700, 400)

    msg = "Anna vartiolle uusi nimi ja koko"
    tk.Label(win, text=msg, font=("Helvetica", 13)).pack(pady=10)

    vartio_nimi = tk.StringVar()
    vartio_koko = tk.IntVar()

    frame = tk.Frame(win)
    frame.pack(pady=10)

    # Nimi
    tk.Label(frame, text="Nimi:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
    name_entry = tk.Entry(frame, textvariable=vartio_nimi)
    name_entry.grid(row=0, column=1, padx=5, pady=5)

    # Koko
    tk.Label(frame, text="Koko:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    size_entry = tk.Entry(frame, textvariable=vartio_koko)
    size_entry.grid(row=1, column=1, padx=5, pady=5)

    # Tallenna + Poistu -painike
    exit_btn_text = "Tallenna" if kieli == "FI" else "Save"
    tk.Button(win, text=exit_btn_text, width=20,
              command=handle_save).pack(pady=(10, 10))


# ======================= Tagin käsittely ==============================

def process_tag(tag_uid: int):
    """Käsitellään luettu tagi, avataan valintaikkuna"""
    print("Prosessoidaan")
    idx_tuple = get_active_tag(tag_uid)
    current_idx = idx_tuple[2] if idx_tuple else None
    vartio = get_vartio_from_db(tag_uid)
    if not vartio:
        createvartiovalues_window(tag_uid)
    else:
        choose_rasti_window(tag_uid, current_idx)


# ======================= Muisti viimeiselle tagille ==============================

last_read_uid = None
last_read_time = 0
READ_COOLDOWN = 3  # sekuntia ennen kuin sama tagi voidaan käsitellä uudestaan

# ======================= Pääohjelman ajo ==============================

def main_loop():
    global last_read_uid, last_read_time

    # Tarkistetaan vanhentuneet tagit säännöllisesti
    # tarkista_vanhentuneet_tagit()

    # Jos NFC-lukija löytyy, luetaan tagi
    if reader:
        try:
            result = reader.read_no_block()
            if result:
                id, _ = result
                if id is not None:
                    now = time.time()
                    if id != last_read_uid or (now - last_read_time > READ_COOLDOWN):
                        last_read_uid = id
                        last_read_time = now
                        process_tag(id)
                        time.sleep(1)  # estää tuplalukemista
        except Exception as e:
            print("Lukija virhe:", e)

    root.after(1000, main_loop)

init_db()
init_slots()
päivitä_kieli()
main_loop()
root.mainloop()
