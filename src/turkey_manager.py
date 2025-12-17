from readline import backend

import flet as ft
import pandas as pd
from backend import Backend  # your backend logic

class TurkeyManager:
    def __init__(self, backend: Backend, refresh_cb):
        self.backend = backend
        self.refresh = refresh_cb

        # Selected items
        self.selected_turkey = None
        self.selected_order = None

        # Sorting
        self.turkey_sort_modes = [
            "tid_asc", "tid_desc", "weight_asc", "weight_desc",
            "unassigned_weight_asc", "unassigned_weight_desc"
        ]
        self.order_sort_modes = [
            "oid_asc", "oid_desc", "target_weight_asc", "target_weight_desc",
            "unassigned_weight_asc", "unassigned_weight_desc"
        ]
        self.turkey_sort_index = 0
        self.order_sort_index = 0

        # --- Create input fields ---
        self.tid_input = ft.TextField(label="Turkey ID", width=100)
        self.weight_input = ft.TextField(label="Weight", width=100)

        self.oid_input = ft.TextField(label="Order ID", width=100)
        self.order_name_input = ft.TextField(label="Name", width=150)
        self.target_weight_input = ft.TextField(label="Target Weight", width=100)
        self.notes_input = ft.TextField(label="Notes", width=200)
        self.ham_radio_group = ft.RadioGroup(
            content=ft.Row([
                ft.Text("Ham:", size=16),
                ft.Radio(value="None", label="None"),
                ft.Radio(value="Whole", label="Whole"),
                ft.Radio(value="1/2", label="1/2"),
                ft.Radio(value="1/4", label="1/4"),
            ]),
            value="None"
        )

        # --- Create buttons ---
        self.add_turkey_btn = ft.ElevatedButton(
            "Add Turkey",
            on_click=lambda e: self.add_turkey_from_inputs()
        )
        self.delete_turkey_btn = ft.ElevatedButton(
            "Delete Selected Turkey",
            on_click=lambda e: self.delete_selected_turkey()
        )
        self.auto_match_btn = ft.ElevatedButton(
            "Auto Match",
            on_click=lambda e: self.auto_match()
        )

        self.add_order_btn = ft.ElevatedButton(
            "Add Order",
            on_click=lambda e: self.add_order_from_inputs()
        )
        self.delete_order_btn = ft.ElevatedButton(
            "Delete Selected Order",
            on_click=lambda e: self.delete_selected_order()
        )
        self.match_btn = ft.ElevatedButton(
            "Match Selected Order & Turkey",
            on_click=lambda e: self.match_selected()
        )
        self.unmatch_turkey_btn = ft.ElevatedButton(
            "Unmatch Selected Turkey",
            on_click=lambda e: self.unmatch_selected_turkey()
        )
        self.unmatch_order_btn = ft.ElevatedButton(
            "Unmatch Selected Order",
            on_click=lambda e: self.unmatch_selected_order()
        )
        # Button to generate all PDFs
        self.make_pdfs_btn = ft.ElevatedButton(
            text="Generate PDFs",
            on_click=lambda e: self.make_pdf()
        )
        # Turkey inputs: Enter moves focus from TID -> Weight, then adds turkey
        self.tid_input.on_submit = lambda e: self.weight_input.focus()
        self.weight_input.on_submit = lambda e: self.add_turkey_from_inputs()

        # Order inputs: cycle through fields, last one triggers add_order
        self.oid_input.on_submit = lambda e: self.order_name_input.focus()
        self.order_name_input.on_submit = lambda e: self.target_weight_input.focus()
        self.target_weight_input.on_submit = lambda e: self.notes_input.focus()
        self.notes_input.on_submit = lambda e: self.add_order_from_inputs()

    # --- Logic functions ---
    def select_turkey(self, tid):
        self.selected_turkey = tid
        self.refresh()

    def select_order(self, oid):
        self.selected_order = oid
        self.refresh()

    def add_turkey_from_inputs(self):
        try:
            tid = int(self.tid_input.value)
            weight = float(self.weight_input.value)
        except ValueError:
            print("Invalid turkey input!")
            return
        self.backend.add_turkey(tid, weight)
        self.tid_input.value = str(tid + 1)
        self.weight_input.value = ""
        self.tid_input.update()
        self.weight_input.update()
        self.weight_input.focus()
        self.refresh()

    def add_order_from_inputs(self):
        try:
            oid = int(self.oid_input.value)
            target_weight = float(self.target_weight_input.value) if self.target_weight_input.value.strip() else 0
            name = self.order_name_input.value
            notes = self.notes_input.value
            ham = self.ham_radio_group.value
        except ValueError:
            print("Invalid order input!")
            return
        self.backend.add_order(oid, target_weight, name, ham, notes)
        self.oid_input.value = str(oid + 1)
        self.target_weight_input.value = ""
        self.order_name_input.value = ""
        self.notes_input.value = ""
        self.ham_radio_group.value = "None"
        self.oid_input.update()
        self.target_weight_input.update()
        self.order_name_input.update()
        self.notes_input.update()
        self.ham_radio_group.update()
        self.refresh()

    def delete_selected_turkey(self):
        if self.selected_turkey is not None:
            self.backend.remove_turkey(self.selected_turkey)
            self.selected_turkey = None
            self.refresh()

    def delete_selected_order(self):
        if self.selected_order is not None:
            self.backend.remove_order(self.selected_order)
            self.selected_order = None
            self.refresh()

    def match_selected(self):
        if self.selected_order and self.selected_turkey:
            try:
                self.backend.match(self.selected_order, self.selected_turkey)
            except ValueError as ve:
                print(ve)
            self.refresh()

    def unmatch_selected_turkey(self):
        if self.selected_turkey:
            self.backend.remove_match_by_tid(self.selected_turkey)
            self.refresh()

    def unmatch_selected_order(self):
        if self.selected_order:
            self.backend.remove_match_by_oid(self.selected_order)
            self.refresh()

    def auto_match(self):
        try:
            self.backend.auto_match()
        except ValueError as ve:
            print(ve)
        self.refresh()

    def make_pdf(self):
        self.backend.export_turkey_orders_pdf()
        self.backend.export_ham_orders_without_turkey()
        self.backend.export_free_turkeys_pdf()
    # --- Sorting ---
    def cycle_turkey_sort(self):
        self.turkey_sort_index = (self.turkey_sort_index + 1) % len(self.turkey_sort_modes)
        self.refresh()

    def cycle_order_sort(self):
        self.order_sort_index = (self.order_sort_index + 1) % len(self.order_sort_modes)
        self.refresh()

    # --- Get sorted data ---
    def get_sorted_turkeys(self):
        df = self.backend.turkeys.copy()
        mode = self.turkey_sort_modes[self.turkey_sort_index]
        if mode == "tid_asc": df = df.sort_values("tid")
        elif mode == "tid_desc": df = df.sort_values("tid", ascending=False)
        elif mode == "weight_asc": df = df.sort_values("weight")
        elif mode == "weight_desc": df = df.sort_values("weight", ascending=False)
        elif mode == "unassigned_weight_asc": df = df[df["assigned"] == False].sort_values("weight")
        elif mode == "unassigned_weight_desc": df = df[df["assigned"] == False].sort_values("weight", ascending=False)
        return df

    def get_sorted_orders(self):
        df = self.backend.orders.copy()
        mode = self.order_sort_modes[self.order_sort_index]
        if mode == "oid_asc": df = df.sort_values("oid")
        elif mode == "oid_desc": df = df.sort_values("oid", ascending=False)
        elif mode == "target_weight_asc": df = df.sort_values("target_weight")
        elif mode == "target_weight_desc": df = df.sort_values("target_weight", ascending=False)
        elif mode == "unassigned_weight_asc": df = df[df["assigned_tid"].isna()].sort_values("target_weight")
        elif mode == "unassigned_weight_desc": df = df[df["assigned_tid"].isna()].sort_values("target_weight", ascending=False)
        return df
