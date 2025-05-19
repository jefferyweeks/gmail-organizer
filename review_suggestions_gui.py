import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

RULES_FILE = "rules.json"
SUGGESTED_FILE = "suggested_rules.json"
DENIED_FILE = "denied_rules.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def rule_key(rule):
    return f"{rule['type']}|{rule['contains']}|{rule['label']}"

def accept_rule(rule):
    rules = load_json(RULES_FILE)
    key_set = {rule_key(r) for r in rules}
    if rule_key(rule) not in key_set:
        rules.append(rule)
        save_json(RULES_FILE, rules)
    remove_suggestion(rule)

def deny_rule(rule):
    denied = load_json(DENIED_FILE)
    key_set = {rule_key(r) for r in denied}
    if rule_key(rule) not in key_set:
        denied.append(rule)
        save_json(DENIED_FILE, denied)
    remove_suggestion(rule)

def remove_suggestion(rule):
    suggestions = load_json(SUGGESTED_FILE)
    filtered = [r for r in suggestions if rule_key(r) != rule_key(rule)]
    save_json(SUGGESTED_FILE, filtered)
    refresh_all()

def refresh_all():
    load_suggested_tab()
    load_denied_tab()
    clear_edit_fields()

def load_suggested_tab():
    for row in suggested_tree.get_children():
        suggested_tree.delete(row)

    suggestions = load_json(SUGGESTED_FILE)
    denied = load_json(DENIED_FILE)
    denied_keys = {rule_key(r) for r in denied}

    for rule in suggestions:
        if rule_key(rule) not in denied_keys:
            suggested_tree.insert("", "end", values=(rule["type"], rule["contains"], rule["label"]))

def load_denied_tab():
    for row in denied_tree.get_children():
        denied_tree.delete(row)

    denied = load_json(DENIED_FILE)
    for rule in denied:
        denied_tree.insert("", "end", values=(rule["type"], rule["contains"], rule["label"]))

def get_selected_rules(tree):
    selected = tree.selection()
    rules = []
    for row in selected:
        values = tree.item(row)["values"]
        rules.append({"type": values[0], "contains": values[1], "label": values[2]})
    return rules

def on_accept():
    selected_rules = get_selected_rules(suggested_tree)
    if not selected_rules:
        messagebox.showinfo("Select Rule", "Please select one or more rules to accept.")
        return
    for rule in selected_rules:
        accept_rule(rule)

def on_deny():
    selected_rules = get_selected_rules(suggested_tree)
    if not selected_rules:
        messagebox.showinfo("Select Rule", "Please select one or more rules to deny.")
        return
    for rule in selected_rules:
        deny_rule(rule)

def on_edit():
    selected_rules = get_selected_rules(suggested_tree)
    if not selected_rules:
        messagebox.showinfo("Select Rule", "Please select a rule to edit.")
        return
    if len(selected_rules) > 1:
        messagebox.showinfo("Multiple Rules", "Please select only one rule to edit at a time.")
        return
    rule = selected_rules[0]
    type_var.set(rule["type"])
    contains_var.set(rule["contains"])
    label_var.set(rule["label"])
    editing_rule.clear()
    editing_rule.update(rule)

def on_save_edit():
    if not editing_rule:
        messagebox.showinfo("Edit Rule", "No rule is currently being edited.")
        return

    edited_rule = {
        "type": type_var.get(),
        "contains": contains_var.get().strip(),
        "label": label_var.get().strip()
    }

    if not edited_rule["contains"] or not edited_rule["label"]:
        messagebox.showerror("Missing Info", "Please fill out all fields.")
        return

    suggestions = load_json(SUGGESTED_FILE)
    updated = False
    for i, r in enumerate(suggestions):
        if rule_key(r) == rule_key(editing_rule):
            suggestions[i] = edited_rule
            updated = True
            break

    if updated:
        save_json(SUGGESTED_FILE, suggestions)
        refresh_all()
    else:
        messagebox.showerror("Error", "Could not find the rule to update.")

def clear_edit_fields():
    type_var.set("from")
    contains_var.set("")
    label_var.set("")
    editing_rule.clear()

# GUI Setup
root = tk.Tk()
root.title("Review Suggested Rules")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Suggested Tab
suggested_frame = ttk.Frame(notebook)
notebook.add(suggested_frame, text="Suggested Rules")

suggested_tree = ttk.Treeview(
    suggested_frame,
    columns=("Type", "Contains", "Label"),
    show="headings",
    selectmode="extended"  # multi-select enabled
)
for col in ("Type", "Contains", "Label"):
    suggested_tree.heading(col, text=col)
suggested_tree.pack(fill="both", expand=True, pady=5)

# Edit Fields
edit_frame = ttk.LabelFrame(suggested_frame, text="Edit Selected Rule")
edit_frame.pack(pady=5, fill="x")

type_var = tk.StringVar(value="from")
contains_var = tk.StringVar()
label_var = tk.StringVar()
editing_rule = {}

ttk.Label(edit_frame, text="Type:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
ttk.Combobox(edit_frame, textvariable=type_var, values=["from", "subject"], state="readonly", width=10).grid(row=0, column=1)

ttk.Label(edit_frame, text="Contains:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
ttk.Entry(edit_frame, textvariable=contains_var, width=30).grid(row=0, column=3)

ttk.Label(edit_frame, text="Label:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
ttk.Entry(edit_frame, textvariable=label_var, width=20).grid(row=0, column=5)

ttk.Button(edit_frame, text="✏️ Edit Selected", command=on_edit).grid(row=1, column=1, pady=5)
ttk.Button(edit_frame, text="💾 Save Changes", command=on_save_edit).grid(row=1, column=3, pady=5)

# Action Buttons
btn_frame = ttk.Frame(suggested_frame)
btn_frame.pack(pady=5)

ttk.Button(btn_frame, text="✅ Accept Selected", command=on_accept).grid(row=0, column=0, padx=5)
ttk.Button(btn_frame, text="❌ Deny Selected", command=on_deny).grid(row=0, column=1, padx=5)

# Denied Tab
denied_frame = ttk.Frame(notebook)
notebook.add(denied_frame, text="Denied Rules")

denied_tree = ttk.Treeview(
    denied_frame,
    columns=("Type", "Contains", "Label"),
    show="headings",
    selectmode="browse"
)
for col in ("Type", "Contains", "Label"):
    denied_tree.heading(col, text=col)
denied_tree.pack(fill="both", expand=True, pady=5)

refresh_all()
root.mainloop()
