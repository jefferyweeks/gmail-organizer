import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

RULES_FILE = 'rules.json'

def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_rules(rules):
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2)

def update_rule_list():
    rule_tree.delete(*rule_tree.get_children())
    for i, rule in enumerate(rules):
        rule_tree.insert("", "end", iid=str(i), values=(rule["type"], rule["contains"], rule["label"]))

def add_rule():
    rule_type = type_var.get()
    contains = contains_entry.get().strip()
    label = label_entry.get().strip()

    if not contains or not label:
        messagebox.showerror("Missing Info", "Please fill out all fields.")
        return

    new_rule = {"type": rule_type, "contains": contains, "label": label}
    
    if editing_index.get() is not None:
        # Edit existing rule
        index = editing_index.get()
        rules[index] = new_rule
        editing_index.set(None)
    else:
        # Add new rule
        rules.append(new_rule)

    save_rules(rules)
    update_rule_list()
    contains_entry.delete(0, tk.END)
    label_entry.delete(0, tk.END)

def delete_rule():
    selected_items = rule_tree.selection()
    if not selected_items:
        messagebox.showinfo("Select Rule", "Please select one or more rules to delete.")
        return

    confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected_items)} rule(s)?")
    if not confirm:
        return

    # Convert to int and sort in reverse so deleting doesn't mess up indexes
    indexes = sorted([int(i) for i in selected_items], reverse=True)
    for index in indexes:
        del rules[index]

    save_rules(rules)
    update_rule_list()
    contains_entry.delete(0, tk.END)
    label_entry.delete(0, tk.END)
    editing_index.set(None)

def edit_rule():
    selected = rule_tree.selection()
    if not selected:
        messagebox.showinfo("Select Rule", "Please select a rule to edit.")
        return
    index = int(selected[0])
    rule = rules[index]
    type_var.set(rule["type"])
    contains_entry.delete(0, tk.END)
    contains_entry.insert(0, rule["contains"])
    label_entry.delete(0, tk.END)
    label_entry.insert(0, rule["label"])
    editing_index.set(index)

# Load rules
rules = load_rules()

# GUI Setup
root = tk.Tk()
root.title("Gmail Organizer Rule Manager")

editing_index = tk.IntVar(value=None)

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="Rule Type:").grid(row=0, column=0, padx=5, pady=5)
type_var = tk.StringVar(value="from")
type_menu = ttk.Combobox(frame, textvariable=type_var, values=["from", "subject"], state="readonly")
type_menu.grid(row=0, column=1, padx=5, pady=5)

tk.Label(frame, text="Contains:").grid(row=1, column=0, padx=5, pady=5)
contains_entry = tk.Entry(frame, width=30)
contains_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(frame, text="Label:").grid(row=2, column=0, padx=5, pady=5)
label_entry = tk.Entry(frame, width=30)
label_entry.grid(row=2, column=1, padx=5, pady=5)

button_frame = tk.Frame(frame)
button_frame.grid(row=3, column=0, columnspan=2, pady=10)

tk.Button(button_frame, text="Add / Save Rule", command=add_rule).grid(row=0, column=0, padx=5)
tk.Button(button_frame, text="Edit Selected", command=edit_rule).grid(row=0, column=1, padx=5)
tk.Button(button_frame, text="Delete Selected", command=delete_rule).grid(row=0, column=2, padx=5)

rule_tree = ttk.Treeview(root, columns=("Type", "Contains", "Label"), show="headings", selectmode="extended")
rule_tree.heading("Type", text="Type")
rule_tree.heading("Contains", text="Contains")
rule_tree.heading("Label", text="Label")
rule_tree.pack(padx=10, pady=10, fill="both", expand=True)

update_rule_list()
root.mainloop()
