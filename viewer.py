import os
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import List

from loader import Animate, save_property, read_property, get_link, download_magnet, DownloadStatus, get_all_files, storage_path, increment_string_number, move_file


class EditableTreeview(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Create a frame for the treeview and the button
        self.tree_frame = tk.Frame(self, padx=10, pady=10)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        self.animate_list: List[Animate] = []
        self.async_task = None

        self.id_name_columns = {0: 'search_name', 1: 'fuzzy_name', 2: 'real_name', 3: 'current_chapter', 4: 'magnet', 5: 'status'}
        self.name_id_columns = {'search_name': 0, 'fuzzy_name': 1, 'real_name': 2, 'current_chapter': 3, 'magnet': 4, 'status': 5}
        self.can_edit_columns = [self.id_name_columns[0], self.id_name_columns[1], self.id_name_columns[3]]
        self.tree = ttk.Treeview(self.tree_frame, columns=list(self.id_name_columns.values()))
        self.tree.heading('#0', text='ID')
        self.tree.heading('#1', text=self.id_name_columns[0])
        self.tree.heading('#2', text=self.id_name_columns[1])
        self.tree.heading('#3', text=self.id_name_columns[2])
        self.tree.heading('#4', text=self.id_name_columns[3])
        self.tree.heading('#5', text=self.id_name_columns[4])
        self.tree.heading('#6', text='status')
        self.tree['show'] = 'headings'

        # Increase row height by modifying the row height style
        style = ttk.Style()
        style.configure('Treeview', rowheight=25)

        self.tree.pack(fill=tk.BOTH, expand=True)

        self._setup_data()

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Bind the double-click event to edit the row
        self.tree.bind('<Double-1>', self.edit_row)

        # Button frame below the treeview
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(fill=tk.X)

        self.save_button = tk.Button(self.button_frame, text="Save", bg="yellow", fg="black", command=self.save_data)
        self.save_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.start_button = tk.Button(self.button_frame, text="Move", bg="blue", fg="white",
                                      command=self.move_file)
        self.start_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.start_button = tk.Button(self.button_frame, text="Start", bg="green", fg="white",
                                      command=self.process_all_items)
        self.start_button.pack(side=tk.RIGHT, padx=10,  pady=10)

        self.tree.tag_configure('lightgreen', background='lightgreen')
        self.tree.tag_configure('green', background='green')
        self.tree.tag_configure('lightblue', background='lightblue')
        self.tree.tag_configure('lightyellow', background='lightyellow')

    def _setup_data(self):
        self.animate_list = read_property()
        i = 0
        for e in self.animate_list:
            self.tree.insert('', 'end', iid=i, values=(f"{e.search_name}", f"{e.fuzzy_name}", f"{e.real_name}", f"{e.current_chapter}"))
            e.item_id = i
            i += 1

    def center_window(self, window, width, height):
        # Get screen width and height
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        # Calculate position x, y
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        window.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def edit_row(self, event):
        # Get the selected item to edit
        selected_item = self.tree.selection()[0]
        values = self.tree.item(selected_item, 'values')

        # Create popup to edit data
        popup = tk.Toplevel(self)
        popup.title("Edit Data")
        popup.geometry("300x200")
        self.center_window(popup, 300, 200)
        entries = []

        for index, value in enumerate(values):
            if self.id_name_columns[index] not in self.can_edit_columns:
                continue
            frame = tk.Frame(popup, padx=10, pady=5)
            frame.pack(fill=tk.X)
            tk.Label(frame, text=f"{self.id_name_columns[index]}", width=15, anchor='w').pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.insert(0, value)
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            entries.append(entry)

        def save_data():
            new_values = [entry.get() for entry in entries]
            old_values = list(self.tree.item(selected_item, 'values'))
            for i, can_edit_column in enumerate(self.can_edit_columns):
                old_values[self.name_id_columns[can_edit_column]] = new_values[i]
                animate = self.animate_list[int(selected_item)]
                animate[can_edit_column] = new_values[i]
            self.tree.item(selected_item, values=old_values)
            popup.destroy()

        button_frame = tk.Frame(popup, padx=10, pady=10)
        button_frame.pack(fill=tk.X)
        tk.Button(button_frame, text="Save", command=save_data).pack(side=tk.LEFT, expand=True)
        tk.Button(button_frame, text="Cancel", command=popup.destroy).pack(side=tk.RIGHT, expand=True)

    def process_all_items(self):
        # Collect all items data from the treeview
        all_items = [(iid, self.tree.item(iid)['values']) for iid in self.tree.get_children()]
        self.async_task = threading.Thread(target=self.start_download_task, args=(all_items, self.animate_list))
        self.async_task.start()
        print('over')

    def save_data(self):
        save_property(self.animate_list)
        print("Data saved!")

    def move_file(self):
        print("start to move animate")
        for animate in self.animate_list:
            if animate.file_name is None:
                continue
            file_name = os.path.basename(animate.file_name)[:-4]
            for file in get_all_files(storage_path):
                if file_name in file and '.bc' not in file:
                    move_file(storage_path, os.path.join(storage_path, animate.real_name), file_name)
            animate.status = DownloadStatus.MOVED
            self.update_view(animate, animate.item_id, 'lightblue')

    def start_download_task(self, data, animate_list):
        # This function will process and modify the entire list of data
        print("Processing and updating data:")
        for item_id, values in data:
            animate = animate_list[int(item_id)]
            time.sleep(1)
            get_link(animate)
            if animate.magnet is None:
                animate.magnet = 'Not found'
                self.update_view(animate, item_id, 'green')
                continue
            self.update_view(animate, item_id, 'green')
            download_magnet(animate)
            self.update_view(animate, item_id, 'lightgreen')

        self.check_all_task_success()

    def check_all_task_success(self):
        print('start to check task')
        # 校验所有下载任务是否完成，时长一个小时
        for cnt in range(0, 600):
            time.sleep(6)
            cnt += 1
            if cnt % 10 == 0:
                print(f'{cnt * 6} sec passed')
            all_completed = True
            for animate in self.animate_list:
                if animate.file_name is None:
                    continue
                file_name = os.path.basename(animate.file_name)[:-4]
                for file in get_all_files(storage_path):
                    if file_name in file:
                        if file.endswith('.bc!'):
                            if cnt % 10 == 0:
                                print(f'wait for {file}')
                            all_completed = False
                        else:
                            if animate.status != DownloadStatus.DOWNLOAD_DONE:
                                animate.status = DownloadStatus.DOWNLOAD_DONE
                                animate.current_chapter = increment_string_number(animate.current_chapter)
                                self.update_view(animate, animate.item_id, 'lightyellow')
            if all_completed:
                return True
        return False

    def update_view(self, animate, item_id, color):
        new_values = [animate.search_name, animate.fuzzy_name, animate.real_name, animate.current_chapter, animate.magnet,
                      animate.status]
        self.tree.item(item_id, values=new_values, tags=(color,))  # Update the treeview with new values

if __name__ == '__main__':
    # Main window
    root = tk.Tk()
    root.title("Animate downloader")
    app = EditableTreeview(root)
    app.pack(fill='both', expand=True)
    root.mainloop()
    print('view main over')
    if app.async_task is not None:
        app.async_task.join()
