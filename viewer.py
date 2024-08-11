import tkinter as tk
from tkinter import ttk
from typing import List

from loader import Animate, save_property, read_property


class EditableTreeview(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Create a frame for the treeview and the button
        self.tree_frame = tk.Frame(self, padx=10, pady=10)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)

        self.id_name_columns = {0: 'search_name', 1: 'fuzzy_name', 2: 'real_name', 3: 'current_chapter'}
        self.name_id_columns = {'search_name': 0, 'fuzzy_name': 1, 'real_name': 2, 'current_chapter': 3}
        self.can_edit_columns = [self.id_name_columns[0], self.id_name_columns[1], self.id_name_columns[3]]
        self.tree = ttk.Treeview(self.tree_frame, columns=list(self.id_name_columns.values()))
        self.tree.heading('#0', text='ID')
        self.tree.heading('#1', text=self.id_name_columns[0])
        self.tree.heading('#2', text=self.id_name_columns[1])
        self.tree.heading('#3', text=self.id_name_columns[2])
        self.tree.heading('#4', text=self.id_name_columns[3])
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

        # Start button
        self.start_button = tk.Button(self.button_frame, text="Start", bg="green", fg="white",
                                      command=self.process_all_items)
        self.start_button.pack(side=tk.RIGHT, padx=10, pady=10)

        # Save button
        self.save_button = tk.Button(self.button_frame, text="Save", bg="yellow", fg="black", command=self.save_data)
        self.save_button.pack(side=tk.RIGHT)

    def _setup_data(self):
        l: List[Animate] = read_property()
        i = 0
        for e in l:
            self.tree.insert('', 'end', iid=i, values=(f"{e.search_name}", f"{e.fuzzy_name}", f"{e.real_name}", f"{e.current_chapter}"))
            i += 1

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
            self.tree.item(selected_item, values=old_values)
            popup.destroy()

        button_frame = tk.Frame(popup, padx=10, pady=10)
        button_frame.pack(fill=tk.X)
        tk.Button(button_frame, text="Save", command=save_data).pack(side=tk.LEFT, expand=True)
        tk.Button(button_frame, text="Cancel", command=popup.destroy).pack(side=tk.RIGHT, expand=True)

    def center_window(self, window, width, height):
        # Get screen width and height
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        # Calculate position x, y
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        window.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def process_all_items(self):
        # Collect all items data from the treeview
        all_items = [(iid, self.tree.item(iid)['values']) for iid in self.tree.get_children()]
        function_a(self, all_items)  # Call function A with all items

    def save_data(self):
        # Placeholder for save function
        animate_list = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            animate_list.append(Animate(
                search_name=values[self.name_id_columns['search_name']],
                fuzzy_name=values[self.name_id_columns['fuzzy_name']].split(","),
                real_name=values[self.name_id_columns['real_name']],
                current_chapter=values[self.name_id_columns['current_chapter']],
                jump_url=None,
                magnet=None,
                file_name=None
            ))
        save_property(animate_list)
        # print(animate_list)
        print("Data saved!")


def function_a(treeview, data):
    # This function will process and modify the entire list of data
    print("Processing and updating data:")
    for item_id, values in data:
        new_values = [value.upper() for value in values]  # Example modification
        treeview.tree.item(item_id, values=new_values)  # Update the treeview with new values


# Main window
root = tk.Tk()
root.title("Editable Treeview Example")
app = EditableTreeview(root)
app.pack(fill='both', expand=True)
root.mainloop()
