import csv
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# --- Константы ---
ICON_PATH = "logrun_thumbnail.ico"          # иконка лежит рядом с exe
LAST_USER_FILE = "logrun_lastuser.txt"      # файл с именем последнего пользователя
DATA_PREFIX = "logrun_"                     # префикс для файлов данных
DATA_SUFFIX = ".csv"

def get_data_filename(username):
    """Возвращает имя файла для заданного пользователя"""
    if not username:
        return None
    # Очищаем имя от недопустимых символов (простейшая санитизация)
    safe_name = "".join(c for c in username if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe_name:
        safe_name = "unknown"
    return f"{DATA_PREFIX}{safe_name}{DATA_SUFFIX}"

# --- Функции работы с данными ---
def parse_duration(duration_str):
    parts = duration_str.strip().split(':')
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes + seconds / 60.0
    else:
        try:
            return float(duration_str)
        except ValueError:
            raise ValueError("Используйте ММ:СС или минуты (число)")

def format_duration(minutes_float):
    total_sec = int(minutes_float * 60)
    m = total_sec // 60
    s = total_sec % 60
    return f"{m:02d}:{s:02d}"

def format_pace(pace_min_per_km):
    total_sec = int(pace_min_per_km * 60)
    m = total_sec // 60
    s = total_sec % 60
    return f"{m:02d}:{s:02d}"

def load_data_for_user(username):
    """Загружает записи пользователя из CSV"""
    filename = get_data_filename(username)
    data = []
    if not filename or not os.path.exists(filename):
        return data
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['Длительность (мин)'] = float(row['Длительность (мин)'])
                row['Расстояние (км)'] = float(row['Расстояние (км)'])
                row['Средняя скорость (км/ч)'] = float(row['Средняя скорость (км/ч)'])
                row['Средний темп (мин/км)'] = float(row['Средний темп (мин/км)'])
                data.append(row)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить данные: {e}")
    return data

def save_data_for_user(username, data):
    """Сохраняет записи пользователя в CSV"""
    filename = get_data_filename(username)
    if not filename:
        return
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['Дата', 'Длительность (мин)', 'Расстояние (км)', 'Место',
                      'Средняя скорость (км/ч)', 'Средний темп (мин/км)']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def get_last_user():
    """Возвращает имя последнего пользователя из файла"""
    if os.path.exists(LAST_USER_FILE):
        try:
            with open(LAST_USER_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            pass
    return None

def set_last_user(username):
    """Сохраняет имя последнего пользователя"""
    with open(LAST_USER_FILE, 'w', encoding='utf-8') as f:
        f.write(username)

def list_users():
    """Возвращает список имён пользователей на основе файлов logrun_*.csv"""
    users = []
    for f in os.listdir('.'):
        if f.startswith(DATA_PREFIX) and f.endswith(DATA_SUFFIX):
            # Извлекаем имя пользователя из названия
            name = f[len(DATA_PREFIX):-len(DATA_SUFFIX)]
            users.append(name)
    return users

# --- Основное приложение ---
class RunningApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Логран - Журнал пробежек")
        self.root.geometry("500x650")  # немного увеличил высоту для кнопки пользователя
        self.root.resizable(False, False)
        
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except:
                pass
        
        self.current_user = None
        self.data = []
        
        # Создаём интерфейс (кнопки, поля)
        self.create_widgets()
        
        # Загружаем последнего пользователя или запускаем выбор
        self.load_initial_user()
    
    def create_widgets(self):
        # Заголовок
        title_label = tk.Label(self.root, text="Логран", font=("Arial", 24, "bold"), fg="#2c3e50")
        title_label.pack(pady=(10, 5))
        
        # Рамка для информации о пользователе
        user_frame = ttk.Frame(self.root)
        user_frame.pack(fill="x", padx=10, pady=5)
        
        self.user_label = ttk.Label(user_frame, text="Пользователь: не выбран", font=("Arial", 10))
        self.user_label.pack(side="left")
        
        self.switch_user_btn = ttk.Button(user_frame, text="Сменить / Создать пользователя", command=self.switch_user)
        self.switch_user_btn.pack(side="right")
        
        # Рамка формы ввода
        frame_input = ttk.LabelFrame(self.root, text="Новая пробежка", padding=10)
        frame_input.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(frame_input, text="Дата (ГГГГ-ММ-ДД):").grid(row=0, column=0, sticky="w", pady=5)
        self.date_entry = ttk.Entry(frame_input, width=30)
        self.date_entry.grid(row=0, column=1, pady=5)
        self.date_entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
        
        ttk.Label(frame_input, text="Длительность (ММ:СС или мин):").grid(row=1, column=0, sticky="w", pady=5)
        self.duration_entry = ttk.Entry(frame_input, width=30)
        self.duration_entry.grid(row=1, column=1, pady=5)
        
        ttk.Label(frame_input, text="Расстояние (км):").grid(row=2, column=0, sticky="w", pady=5)
        self.distance_entry = ttk.Entry(frame_input, width=30)
        self.distance_entry.grid(row=2, column=1, pady=5)
        
        ttk.Label(frame_input, text="Место бега:").grid(row=3, column=0, sticky="w", pady=5)
        self.location_entry = ttk.Entry(frame_input, width=30)
        self.location_entry.grid(row=3, column=1, pady=5)
        
        self.add_btn = ttk.Button(frame_input, text="➕ Добавить запись", command=self.add_record)
        self.add_btn.grid(row=4, column=0, columnspan=2, pady=15)
        
        # Кнопки истории и графиков
        self.history_btn = ttk.Button(self.root, text="📋 Показать историю", command=self.show_history)
        self.history_btn.pack(pady=5)
        
        self.graph_btn = ttk.Button(self.root, text="📈 Показать графики", command=self.show_graphs)
        self.graph_btn.pack(pady=5)
        
        # Статусная строка и email
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(side="bottom", fill="x")
        
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе.")
        status_label = ttk.Label(bottom_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_label.pack(side="left", fill="x", expand=True)
        
        email_label = tk.Label(bottom_frame, text="victsav@gmail.com", font=("Arial", 8), fg="gray")
        email_label.pack(side="right", padx=5, pady=2)
    
    def load_initial_user(self):
        last_user = get_last_user()
        if last_user and os.path.exists(get_data_filename(last_user)):
            self.set_user(last_user)
        else:
            # Нет пользователя или файл пропал – предлагаем выбрать/создать
            self.switch_user()
    
    def set_user(self, username):
        """Устанавливает текущего пользователя, загружает его данные"""
        self.current_user = username
        self.data = load_data_for_user(username)
        self.user_label.config(text=f"Пользователь: {username}")
        self.status_var.set(f"Загружен пользователь: {username} (записей: {len(self.data)})")
        set_last_user(username)
    
    def switch_user(self):
        """Диалог выбора существующего или создания нового пользователя"""
        users = list_users()
        choice = simpledialog.askstring("Выбор пользователя",
                                         f"Доступные пользователи: {', '.join(users) if users else 'нет'}\n\n"
                                         "Введите имя существующего или нового пользователя:",
                                         parent=self.root)
        if not choice or not choice.strip():
            return
        new_name = choice.strip()
        # Проверяем, не хочет ли он переключиться на того же
        if self.current_user == new_name:
            return
        # Загружаем или создаём нового
        self.set_user(new_name)
    
    def add_record(self):
        if not self.current_user:
            messagebox.showwarning("Предупреждение", "Сначала выберите пользователя (кнопка 'Сменить / Создать').")
            return
        
        date_str = self.date_entry.get().strip()
        duration_str = self.duration_entry.get().strip()
        distance_str = self.distance_entry.get().strip()
        location = self.location_entry.get().strip()
        
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Ошибка", "Дата должна быть в формате ГГГГ-ММ-ДД")
            return
        
        try:
            duration_min = parse_duration(duration_str)
            if duration_min <= 0:
                raise ValueError
        except:
            messagebox.showerror("Ошибка", "Неверный формат длительности. Используйте ММ:СС или число > 0")
            return
        
        try:
            distance = float(distance_str)
            if distance <= 0:
                raise ValueError
        except:
            messagebox.showerror("Ошибка", "Расстояние должно быть положительным числом")
            return
        
        if not location:
            location = "Не указано"
        
        hours = duration_min / 60.0
        avg_speed = distance / hours
        avg_pace = duration_min / distance
        
        new_entry = {
            'Дата': date_str,
            'Длительность (мин)': round(duration_min, 2),
            'Расстояние (км)': round(distance, 2),
            'Место': location,
            'Средняя скорость (км/ч)': round(avg_speed, 2),
            'Средний темп (мин/км)': round(avg_pace, 2)
        }
        
        self.data.append(new_entry)
        self.data.sort(key=lambda x: x['Дата'])
        save_data_for_user(self.current_user, self.data)
        
        # Очистка полей
        self.duration_entry.delete(0, tk.END)
        self.distance_entry.delete(0, tk.END)
        self.location_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, datetime.today().strftime("%Y-%m-%d"))
        
        self.status_var.set(f"Запись добавлена! Скорость: {avg_speed:.2f} км/ч, темп: {format_pace(avg_pace)}")
    
    def show_history(self):
        if not self.current_user:
            messagebox.showinfo("Информация", "Пользователь не выбран.")
            return
        if not self.data:
            messagebox.showinfo("Информация", "Нет записей для этого пользователя.")
            return
        
        hist_win = Toplevel(self.root)
        hist_win.title(f"История пробежек — {self.current_user} (Логран)")
        hist_win.geometry("950x550")
        if os.path.exists(ICON_PATH):
            try:
                hist_win.iconbitmap(ICON_PATH)
            except:
                pass
        
        main_frame = ttk.Frame(hist_win)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        columns = ("№", "Дата", "Длительность", "Расстояние (км)", "Место", "Скорость (км/ч)", "Темп (мин/км)")
        tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        col_widths = [40, 100, 80, 90, 250, 100, 100]
        for col, width in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="center" if col != "Место" else "w")
        
        def populate():
            tree.delete(*tree.get_children())
            for i, entry in enumerate(self.data, start=1):
                dur_fmt = format_duration(entry['Длительность (мин)'])
                pace_fmt = format_pace(entry['Средний темп (мин/км)'])
                tree.insert("", tk.END, values=(
                    i,
                    entry['Дата'],
                    dur_fmt,
                    f"{entry['Расстояние (км)']:.2f}",
                    entry['Место'],
                    f"{entry['Средняя скорость (км/ч)']:.2f}",
                    pace_fmt
                ))
        populate()
        
        scroll_y = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
        scroll_x = ttk.Scrollbar(main_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        btn_frame = ttk.Frame(hist_win)
        btn_frame.pack(pady=10)
        
        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Предупреждение", "Выберите запись для удаления.")
                return
            item = selected[0]
            row_index = int(tree.item(item, "values")[0]) - 1
            confirm = messagebox.askyesno("Подтверждение", f"Удалить запись от {self.data[row_index]['Дата']}?")
            if confirm:
                del self.data[row_index]
                save_data_for_user(self.current_user, self.data)
                populate()
                self.status_var.set("Запись удалена.")
                if not self.data:
                    hist_win.destroy()
        
        ttk.Button(btn_frame, text="🗑 Удалить выбранную запись", command=delete_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=hist_win.destroy).pack(side="left", padx=5)
    
    def show_graphs(self):
        if not self.current_user:
            messagebox.showinfo("Информация", "Пользователь не выбран.")
            return
        if len(self.data) < 2:
            messagebox.showinfo("Информация", "Нужно хотя бы 2 записи для построения графиков.")
            return
        
        sorted_data = sorted(self.data, key=lambda x: x['Дата'])
        dates = [datetime.strptime(entry['Дата'], "%Y-%m-%d") for entry in sorted_data]
        speeds = [entry['Средняя скорость (км/ч)'] for entry in sorted_data]
        durations = [entry['Длительность (мин)'] for entry in sorted_data]
        paces = [entry['Средний темп (мин/км)'] for entry in sorted_data]
        
        graph_win = Toplevel(self.root)
        graph_win.title(f"Графики прогресса — {self.current_user} (Логран)")
        graph_win.geometry("900x700")
        if os.path.exists(ICON_PATH):
            try:
                graph_win.iconbitmap(ICON_PATH)
            except:
                pass
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
        fig.subplots_adjust(hspace=0.3)
        
        ax1.plot(dates, speeds, 'o-', color='green', linewidth=2, markersize=6)
        ax1.set_ylabel('Скорость (км/ч)')
        ax1.set_title('Изменение средней скорости')
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        ax2.plot(dates, durations, 'o-', color='blue', linewidth=2, markersize=6)
        ax2.set_ylabel('Длительность (мин)')
        ax2.set_title('Изменение длительности пробежки')
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        ax3.plot(dates, paces, 'o-', color='red', linewidth=2, markersize=6)
        ax3.set_ylabel('Темп (мин/км)')
        ax3.set_title('Изменение темпа (меньше — быстрее)')
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.set_xlabel('Дата')
        
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        canvas = FigureCanvasTkAgg(fig, master=graph_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(graph_win, text="Закрыть", command=graph_win.destroy).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = RunningApp(root)
    root.mainloop()